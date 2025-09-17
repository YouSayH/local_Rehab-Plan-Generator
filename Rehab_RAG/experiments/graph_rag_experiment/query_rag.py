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
`python .\\experiments\\<実験名>\\query_rag.py`
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

        prompt = f"""あなたは理学療法の専門家アシスタントです。
以下の参考情報を主な根拠として、ユーザーの質問に日本語で回答してください。

### 指示
- 回答は参考情報の内容を要約・抽出し、あなたの個人的な知識や意見は含めないでください。
- もし参考情報の中に、質問に答えるための情報が全く見つからない場合にのみ、「参考情報の中に関連する情報が見つかりませんでした。」と回答してください。
- 回答の各文末には、根拠として利用した参考情報の番号を [番号] の形式で必ず付記してください。複数の情報を参考にした場合は [番号1, 番号2] のように記述してください。

### ユーザーの質問
{query}

### 参考情報
{context_str}

### あなたの回答
"""
        return prompt

    def query(self, query: str):
        print(f"\n[ユーザーの質問]: {query}")

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

        # if not filtered_docs:
        #     print("\n[最終回答]\n参考情報の中に関連する情報が見つかりませんでした。")
        #     return

        if not filtered_docs:
            not_found_message = "参考情報の中に関連する情報が見つかりませんでした。"
            print(f"\n[最終回答]\n{not_found_message}")
            return {"answer": not_found_message, "contexts": []}

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

    # === 初期テストクエリ ===
    # パイプラインが正しく動作するかを確認するためのサンプル質問リスト。
    # それぞれ異なるガイドライン文書から情報を引くように設計されています。
    test_queries = [
        "大腿骨近位部骨折の術後、理学療法の頻度を増やすとどうなりますか？",
        "変形性股関節症の発症を予防するには、運動療法だけで十分ですか？",
        "脳卒中患者に対する有酸素運動は推奨されますか？",
        "肩関節周囲炎の炎症期に、痛みを我慢して積極的に運動したほうがいいですか？",
    ]
    for q in test_queries:
        pipeline.query(q)
        time.sleep(1)  # APIのレート制限を避けるため

    # === 対話モード ===
    # ユーザーが自由に入力して、RAGパイプラインの挙動をインタラクティブに
    # 確認できるようにするためのモードです。
    print("\n\n対話モードを開始します。終了するには 'q' または 'exit' と入力してください。")
    while True:
        user_input = input("\n質問を入力してください: ")
        if user_input.lower() in ["q", "exit"]:
            print("終了します。")
            break
        if user_input:
            pipeline.query(user_input)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"パイプラインの実行中に致命的なエラーが発生しました: {e}")
