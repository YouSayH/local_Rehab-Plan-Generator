"""
RAGクエリ実行スクリプト (The Query Engine)

[このスクリプトの役割]
このスクリプトは、RAGパイプラインの「実行」フェーズを担当します。
`config.yaml` ファイルで定義された設定に基づき、ユーザーからの質問に対して
一連のRAGプロセスを実行し、最終的な回答を生成します。

1. 設定ファイル(`config.yaml`)を読み込む。
2. 指定されたLLM, Embedder, Retriever, Query Enhancer, Filterなどの
   コンポーネントを動的にロードし、RAGパイプラインを構築する。
3. ユーザーからの質問を受け付ける。
4. (設定されていれば) HyDEなどで質問を拡張する。
5. 拡張された質問を元に、データベースから関連文書を検索(Retrieve)する。
6. (設定されていれば) NLI Filterなどで検索結果をフィルタリングする。
7. 絞り込まれた文書をコンテキストとして、LLMに最終的な回答を生成(Generate)させる。

[実行方法]
プロジェクトのルートディレクトリから、以下のコマンドで実行します。
`python .\experiments\<実験名>\query_rag.py`
"""

import yaml
import importlib
import time
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..")))


def load_config(config_path="config.yaml"):
    """YAML設定ファイルを読み込む"""
    full_path = os.path.join(SCRIPT_DIR, config_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_instance(module_name, class_name, params={}):
    """モジュールとクラス名からインスタンスを動的に生成する"""
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    return class_(**params)


class RAGPipeline:
    def __init__(self, config):
        print("--- RAGパイプラインの初期化を開始 ---")
        q_cfg = config["query_components"]

        llm_cfg = q_cfg["llm"]
        self.llm = get_instance(module_name=llm_cfg["module"], class_name=llm_cfg["class"], params=llm_cfg.get("params", {}))

        embedder_cfg = q_cfg["embedder"]
        self.embedder = get_instance(
            module_name=embedder_cfg["module"], class_name=embedder_cfg["class"], params=embedder_cfg.get("params", {})
        )

        # 'query_enhancer' がnullや空でないことを確認
        if "query_enhancer" in q_cfg and q_cfg["query_enhancer"]:
            enhancer_cfg = q_cfg["query_enhancer"]
            enhancer_params = enhancer_cfg.get("params", {})
            enhancer_params["llm"] = self.llm  # LLMインスタンスを注入
            self.query_enhancer = get_instance(
                module_name=enhancer_cfg["module"], class_name=enhancer_cfg["class"], params=enhancer_params
            )
        else:
            self.query_enhancer = None

        if "reranker" in q_cfg and q_cfg["reranker"]:
            reranker_cfg = q_cfg["reranker"]
            self.reranker = get_instance(
                module_name=reranker_cfg["module"], class_name=reranker_cfg["class"], params=reranker_cfg.get("params", {})
            )
        else:
            self.reranker = None

        if "filter" in q_cfg and q_cfg["filter"]:
            filter_cfg = q_cfg["filter"]
            self.filter = get_instance(
                module_name=filter_cfg["module"], class_name=filter_cfg["class"], params=filter_cfg.get("params", {})
            )
        else:
            self.filter = None

        retriever_cfg = q_cfg.get("retriever")
        full_db_path = os.path.join(SCRIPT_DIR, config["database"]["path"])

        # config.yamlにretrieverの定義があれば、それを動的に読み込む
        if retriever_cfg:
            retriever_params = {
                "path": full_db_path,
                "collection_name": config["database"]["collection_name"],
                "embedder": self.embedder,
                **retriever_cfg.get("params", {}),
            }
            self.retriever = get_instance(retriever_cfg["module"], retriever_cfg["class"], retriever_params)
        # 従来のconfigファイル（retriever定義なし）との後方互換性のための処理
        else:
            retriever_params = {
                "path": full_db_path,
                "collection_name": config["database"]["collection_name"],
                "embedder": self.embedder,
            }
            self.retriever = get_instance(
                "rag_components.retrievers.chromadb_retriever", "ChromaDBRetriever", retriever_params
            )

        print("--- 初期化完了 ---")

    def construct_prompt(self, query: str, context_docs: list, context_metadatas: list) -> str:
        context_str = ""
        for i, (doc, meta) in enumerate(zip(context_docs, context_metadatas)):
            source_info = f"出典: {meta.get('source', 'N/A')}, 疾患: {meta.get('disease', 'N/A')}, セクション: {meta.get('section', 'N/A')}"
            context_str += f"[参考情報 {i + 1}] ({source_info})\n"
            context_str += f"{doc}\n\n"

        prompt = f"""# 役割
あなたは、臨床経験が豊富なリハビリテーション専門家（理学療法士・作業療法士）です。
提供された「患者情報」と「参考情報（最新のガイドライン等）」を基に、専門的かつ個別性の高いリハビリテーション総合実施計画書の草案を日本語で作成してください。

# 指示
- **最重要**: 「参考情報」を最も重要な根拠としてください。参考情報に記載のあるエビデンスや推奨事項を積極的に治療計画に反映させてください。
- **引用**: 参考情報を根拠とした記述には、文末に必ず `[番号]` の形式で出典番号を付記してください。複数の情報を参考にした場合は `[番号1, 番号2]` のように記述してください。
- **構造化**: 以下の「あなたの回答」セクションの項目に従って、漏れなく記述してください。
- **具体性**: 抽象的な表現は避け、誰が読んでも理解できる具体的な内容を記述してください。特に目標設定や治療内容は、具体的な数値や動作を用いてください。

# 患者情報
{query}

# 参考情報 (ガイドライン等)
{context_str}

# あなたの回答 (リハビリテーション総合実施計画書 草案)

---

### 1. リスク管理と特記事項
- **リスク**: (患者情報から考えられる転倒、血圧変動、脱臼、再発などのリスクを具体的に挙げ、訓練中の注意点を記述)
- **禁忌**: (疾患や術式、合併症に基づく医学的な禁忌事項や、避けるべき動作・運動を記述)

### 2. 心身機能・構造の問題点
- **疼痛**: (痛みの部位、性質、NRS(10段階評価)、誘発動作などを記述)
- **関節可動域(ROM)**: (具体的な関節と角度、それによるADL上の支障を記述)
- **筋力**: (MMT等を参考に、具体的な筋群の低下と、それによる動作への影響を記述)
- **高次脳機能**: (注意障害、半側空間無視など、具体的な症状とリハビリへの影響を記述)
- **その他**: (痙縮、感覚障害、アライメントなど、特筆すべき機能障害を記述)

### 3. 活動と参加の状況
- **ADL (日常生活動作)**: (移動、更衣、食事、整容、トイレなど、介助が必要な場面と自立している場面を具体的に記述)
- **社会参加**: (仕事、趣味、社会活動の現状と課題を記述)

### 4. 目標設定
- **短期目標 (1ヶ月後)**: (SMART原則を意識し、「誰が」「いつまでに」「何を」「どのように」できるかを具体的に記述。例: T字杖と装具を使用し、病棟内50mを安定して連続歩行できる)
- **長期目標 (退院時)**: (本人の希望を踏まえ、退院後の生活で達成したい具体的なゴールを記述。例: 自宅の環境で、日中の基本的なADLが見守りレベルで自立する。趣味のカメラを両手で操作できる)

### 5. 治療方針と内容
- **全体方針**: (短期・長期目標を達成するための、リハビリテーションの全体的な方向性を示す)
- **理学療法 (PT)**: (歩行練習、筋力強化、バランス訓練など、具体的なプログラム案を複数提示)
- **作業療法 (OT)**: (上肢機能訓練、ADL練習、高次脳機能アプローチなど、具体的なプログラム案を複数提示)
- **自主トレーニング・生活指導**: (自宅でできる運動、動作の工夫、環境設定のアドバイスなどを記述)

---
"""
        return prompt

    def query(self, query: str):
        print(f"\n[患者情報]:\n{query}")

        if self.query_enhancer:
            print("\n[ステップ1/6] クエリを拡張中...")
            search_queries = self.query_enhancer.enhance(query)
            # enhanceメソッドの戻り値がリストでない場合もリストに変換して扱う
            if not isinstance(search_queries, list):
                search_queries = [search_queries]
                print(f"  - 拡張されたクエリ (検索に使用):\n'{search_queries[0][:150]}...'")
        else:
            print("\n[ステップ1/6] クエリ拡張はスキップされました。")
            search_queries = [query]

        print("\n[ステップ2/6] 関連文書を検索中...")
        # 複数のクエリで検索し、結果を重複排除してマージ
        all_docs = {}
        for q in search_queries:
            # 複数クエリの場合は、それぞれのクエリを表示
            if len(search_queries) > 1:
                print(f"  - クエリ '{q}' で検索...")
            results = self.retriever.retrieve(q, n_results=10)  # 各クエリで10件取得
            if results and results.get("documents") and results["documents"][0]:
                for i, doc_text in enumerate(results["documents"][0]):
                    # ドキュメントのテキスト内容をキーとして重複を排除
                    if doc_text not in all_docs:
                        all_docs[doc_text] = results["metadatas"][0][i]

        docs = list(all_docs.keys())
        metadatas = list(all_docs.values())
        print(f"  - 合計で {len(docs)}件のユニークな文書を取得しました。")

        if self.reranker:
            print("\n[ステップ3/6] CrossEncoderで検索結果をリランキング中...")
            # リランキングは元の単一クエリで行う
            reranked_docs, reranked_metadatas = self.reranker.rerank(query, docs, metadatas)
            docs, metadatas = reranked_docs, reranked_metadatas
            print("  - リランキングが完了しました。")
        else:
            print("\n[ステップ3/6] リランキングはスキップされました。")

        print("\n[ステップ4/6] NLIモデルで矛盾情報をフィルタリング中...")
        if self.filter:
            # フィルタリングも元の単一クエリで行う
            filtered_docs, filtered_metadatas = self.filter.filter(query, docs, metadatas)
            print(
                f"  - フィルタリング後、{len(filtered_docs)}件の文書が残りました。 ({len(docs) - len(filtered_docs)}件を除外)"
            )
        else:
            print("  - フィルタリングはスキップされました。")
            filtered_docs, filtered_metadatas = docs, metadatas

        if not filtered_docs:
            print("\n[最終回答]\n参考情報の中に関連する情報が見つかりませんでした。")
            return

        print("\n[ステップ5/6] LLM用のプロンプトを構築中...")
        top_k = 5
        final_docs = filtered_docs[:top_k]
        final_metadatas = filtered_metadatas[:top_k]
        print(f"  - 最も関連性の高い上位{len(final_docs)}件を使用します。")
        final_prompt = self.construct_prompt(query, final_docs, final_metadatas)

        print("\n[ステップ6/6] LLMで最終回答を生成中...")
        time.sleep(1)  # レート制限対策
        final_answer = self.llm.generate(final_prompt)

        print("\n" + "=" * 50)
        print("[最終回答]")
        print(final_answer)
        print("=" * 50 + "\n")
        return {
            "answer": final_answer,
            "contexts": [doc for doc in final_docs],  # ドキュメントのリストを返す
        }


def main():
    config = load_config()
    pipeline = RAGPipeline(config)

    # 患者情報テンプレート (ユーザー入力支援用)
    patient_info_template = """
# 患者情報テンプレート
以下の形式で患者様の情報を入力してください。不要な項目は削除・省略して構いません。
--------------------------------------------------
- **患者**: [氏名], [年齢]歳, [性別]
- **診断名**: [例: 脳梗塞による左片麻痺]
- **発症/受傷から**: [例: 1ヶ月]
- **合併症/既往歴**: [例: 高血圧症]
- **主な問題点**:
  - [例: 左上下肢の麻痺 (ブルンストローム 上肢III, 手指II, 下肢IV)]
  - [例: 軽度の半側空間無視]
  - [例: 左手首・手指の痙縮]
- **ADLの状況**:
  - [例: T字杖と短下肢装具で見守り歩行が可能]
  - [例: ボタンのかけ外しに介助が必要]
- **本人の希望・目標**:
  - [例: 職場復帰したい]
  - [例: 趣味のカメラを再開したい]
--------------------------------------------------
"""

    # 初期テストクエリ
    test_queries = [
        """- **患者**: 鈴木 一郎 様, 55歳, 男性
- **診断名**: 脳梗塞（右中大脳動脈領域）による左片麻痺
- **発症/受傷から**: 1ヶ月
- **合併症/既往歴**: 高血圧症
- **主な問題点**:
  - 左上下肢の麻痺 (ブルンストロームステージ 上肢Ⅲ、手指Ⅱ、下肢Ⅳ)
  - 左手首や指の痙縮
  - 左半身の感覚鈍麻
  - 軽度の半側空間無視
- **ADLの状況**:
  - 室内はT字杖と短下肢装具で見守り歩行
  - ボタンのかけ外しに介助が必要
- **本人の希望・目標**:
  - 杖なし歩行
  - PC作業への復帰
  - カメラを両手で構えたい""",
        """- **患者**: 佐藤 和子 様, 68歳, 女性
- **診断名**: 変形性膝関節症（右膝、内側型, K-L Grade 3）
- **発症/受傷から**: 長年
- **合併症/既往歴**: 肥満傾向
- **主な問題点**:
  - 歩行時、階段昇降時の右膝内側の疼痛
  - 膝の伸展-10°、屈曲110°の可動域制限
  - 大腿四頭筋の筋力低下
  - 軽度のO脚
- **ADLの状況**:
  - 15分以上の歩行で疼痛増悪
  - しゃがみ込み、床からの立ち上がりが困難
- **本人の希望・目標**:
  - 孫と痛みを気にせず散歩したい
  - 趣味の庭いじりを続けたい
  - 手術は避けたい""",
    ]
    for q in test_queries:
        pipeline.query(q)
        time.sleep(1)  # APIのレート制限を避けるため

    # === 対話モード ===
    # ユーザーが自由に入力して、RAGパイプラインの挙動をインタラクティブに
    # 確認できるようにするためのモードです。
    print("\n\n対話モードを開始します。終了するには 'q' または 'exit' と入力してください。")
    print(patient_info_template)
    while True:
        print("\n患者情報を入力してください (入力が終わったら空行でEnterを押してください):")
        user_lines = []
        try:
            while True:
                line = input()
                if line.strip() == "":  # 空行で入力終了
                    break
                user_lines.append(line)
        except EOFError:  # Ctrl+D (Unix) or Ctrl+Z+Enter (Windows) for EOF
            print("\n入力を終了します。")
            break

        user_input = "\n".join(user_lines).strip()

        if user_input.lower() in ["q", "exit"]:
            print("終了します。")
            break

        # 入力が空でなく、終了コマンドでもない場合のみクエリを実行
        if user_input:
            pipeline.query(user_input)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"パイプラインの実行中に致命的なエラーが発生しました: {e}")
