"""
RAGクエリ実行スクリプト

[このスクリプトの目的]
このスクリプトは、`rehab_rag`プロジェクトにおけるRAG（Retrieval-Augmented Generation）
パイプラインの実行と検証を行うための中心的な役割を担います。
単なる質疑応答だけでなく、`kcr_rehab-plan-generator` Webアプリケーションの
バックエンドで実行される複雑なプロセスを忠実にシミュレートすることを目的としています。

[主な機能とアプローチ]
1.  **動的なパイプライン切り替え**:
    - `rag_config.yaml`を読むことで、実行するRAGの構成（例：シンプルなベクトル検索、
      グラフRAG、Self-RAGなど）を柔軟に切り替えられます。

2.  **Webアプリの動作再現**:
    - **検索と生成の分離**: 検索効率を最大化するために、患者情報から「診断名」などの
      要点を抽出して短い検索クエリを生成します。一方で、最終的な回答生成時には、
      患者情報の全体像をLLMに提供し、質の高い計画書を作成させます。
    - **プライバシー保護**: LLMに情報を渡す直前に、患者の名前を削除し、年齢を年代に
      丸める匿名化処理を施します。

3.  **多様な出力形式のテスト**:
    - Webアプリで使われる構造化データ（JSON）出力と、人間が読むための
      自然な文章出力の両方のモードでテスト実行が可能です。

[使い方]
1.  **パイプラインの選択**:
    - プロジェクトルートの`rag_config.yaml`を開き、`active_pipeline`に実行したい
      実験フォルダ名（例: `hybrid_search_experiment`）を指定します。

2.  **スクリプトの実行**:
    - プロジェクトのルートディレクトリから、以下のコマンドでスクリプトを実行します。
      `python query_rag.py`
    - 実行されると、まず`test_queries`に定義されたテストケースが自動で実行され、
      その後、ユーザーが自由に入力できる対話モードに移行します。
"""

import yaml
import importlib
import time
import os
import sys
import argparse
import re
from textwrap import indent

# プロジェクトのルートディレクトリをPythonのパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

# schemas.py から RehabPlanSchema をインポート
from schemas import RehabPlanSchema

def load_active_pipeline_config(config_path='rag_config.yaml'):
    """
    メインの設定ファイル(`rag_config.yaml`)からアクティブなパイプライン名を読み込み、
    対応する実験フォルダ内の詳細な設定ファイル(`config.yaml`)をロードする。
    これにより、実行するRAG構成を一つのファイルで管理できる。
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        app_config = yaml.safe_load(f)
    
    pipeline_name = app_config.get('active_pipeline')
    if not pipeline_name:
        raise ValueError("rag_config.yamlに 'active_pipeline' が指定されていません。")
    
    print(f"--- アクティブなパイプライン: '{pipeline_name}' ---")
    
    pipeline_config_path = os.path.join('experiments', pipeline_name, 'config.yaml')
    if not os.path.exists(pipeline_config_path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {pipeline_config_path}")
    
    with open(pipeline_config_path, 'r', encoding='utf-8') as f:
        pipeline_config = yaml.safe_load(f)
        
    # 後でパスを解決するために、読み込んだ設定ファイル自体のパスも保持しておく
    pipeline_config['config_file_path'] = pipeline_config_path
    return pipeline_config

def get_instance(module_name, class_name, params={}):
    """
    モジュール名とクラス名を文字列として受け取り、そのクラスのインスタンスを動的に生成する。
    config.yamlに基づいた柔軟なコンポーネントの初期化を実現するためのヘルパー関数。
    """
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    return class_(**params)

def create_search_query(patient_info: str) -> str:
    """
    患者情報の全文から、RAGの文書検索に最適化された短いキーワード群を抽出する。
    Webアプリの`rag_executor.py`のロジックを模倣し、検索精度と効率を向上させる。
    """
    # 正規表現を使い、「診断名」「主な問題点」「本人の希望・目標」のセクションを抽出
    disease_match = re.search(r"\*\*診断名\*\*:\s*(.*)", patient_info)
    disease = disease_match.group(1).strip() if disease_match else ""
    
    notes_match = re.search(r"\*\*主な問題点\*\*:\s*([\s\S]*?)(?=\n\s*-\s*\*\*ADLの状況\*\*|\Z)", patient_info)
    notes = notes_match.group(1).strip() if notes_match else ""

    goals_match = re.search(r"\*\*本人の希望・目標\*\*:\s*([\s\S]*)", patient_info)
    goals = goals_match.group(1).strip() if goals_match else ""

    # 抽出した要素を半角スペースで結合して一つの検索クエリにする
    search_query = f"{disease} {notes} {goals}".strip()

    # Markdownの `- ` や余分な改行、連続する空白を削除して整形
    search_query = re.sub(r'\s+', ' ', search_query).replace('- ', '')
    
    # もし何も抽出できなかった場合は、元の情報全体を検索クエリとして使用する
    return search_query if search_query else patient_info

def anonymize_patient_info(patient_info: str) -> str:
    """
    LLMに渡す直前に、患者情報から個人を特定できる情報を匿名化する。
    名前は削除し、年齢は年代に丸めることでプライバシーを保護する。
    """
    anonymized_lines = []
    for line in patient_info.splitlines():
        # 患者名、年齢、性別が含まれる行を特別に処理
        if re.search(r"-\s*\*\*患者\*\*:", line):
            age_str = ""
            age_match = re.search(r"(\d+)\s*歳", line)
            if age_match:
                try:
                    age = int(age_match.group(1))
                    age_group = (age // 10) * 10
                    age_str = f"{age_group}代"
                except (ValueError, TypeError):
                    pass # 変換に失敗した場合は何もしない
            
            gender_str = ""
            gender_match = re.search(r"(男|女)性", line)
            if gender_match:
                gender_str = gender_match.group(0)

            # 名前を含めずに、年代と性別だけで新しい行を再構築
            new_line = f"- **患者情報**: {age_str}, {gender_str}".strip().strip(',')
            anonymized_lines.append(new_line)
            continue

        # その他の行はそのまま追加
        anonymized_lines.append(line)
        
    return "\n".join(anonymized_lines)


class RAGPipeline:
    def __init__(self, config):
        print("--- RAGパイプラインの初期化を開始 ---")
        q_cfg = config['query_components']
        
        # 主要コンポーネントを動的に初期化
        self.llm = self._initialize_component('llm', q_cfg)
        self.embedder = self._initialize_component('embedder', q_cfg)
        self.judge = self._initialize_component('judge', q_cfg, {'llm': self.llm})
        self.query_enhancer = self._initialize_component('query_enhancer', q_cfg, {'llm': self.llm})
        self.reranker = self._initialize_component('reranker', q_cfg)

        self.filters = []
        if 'filter' in q_cfg and q_cfg['filter']:
            filter_configs = q_cfg['filter']
            # configでフィルターが一つだけ指定された場合もリストとして扱えるようにする
            if not isinstance(filter_configs, list):
                filter_configs = [filter_configs]
            
            for filter_cfg in filter_configs:
                params = filter_cfg.get('params', {})
                params.update({'llm': self.llm}) # SelfReflectiveFilterなどのためにLLMを注入
                self.filters.append(get_instance(
                    module_name=filter_cfg['module'],
                    class_name=filter_cfg['class'],
                    params=params
                ))
        # self.filter = self._initialize_component('filter', q_cfg, {'llm': self.llm})
            
        # Retrieverの初期化 (DBパスの解決もここで行う)
        retriever_cfg = q_cfg.get('retriever')
        experiment_dir = os.path.dirname(config['config_file_path'])
        db_path = os.path.join(experiment_dir, config['database']['path'])
        
        # config.yamlにretrieverの指定があればそれを使用し、なければデフォルトのChromaDBRetrieverを使う
        if retriever_cfg:
            retriever_params = {
                "path": db_path,
                "collection_name": config['database']['collection_name'],
                "embedder": self.embedder,
                **retriever_cfg.get('params', {})
            }

            if retriever_cfg.get('class') in ['GraphRetriever', 'CombinedRetriever']:
                retriever_params['llm'] = self.llm

            self.retriever = get_instance(
                retriever_cfg['module'],
                retriever_cfg['class'],
                retriever_params
            )
        else:
            retriever_params = {
                "path": db_path,
                "collection_name": config['database']['collection_name'],
                "embedder": self.embedder
            }
            self.retriever = get_instance(
                'rag_components.retrievers.chromadb_retriever', 
                'ChromaDBRetriever', 
                retriever_params
            )

        print("--- 初期化完了 ---")

    def _initialize_component(self, name, config, extra_params={}):
        """コンポーネントの初期化処理を共通化"""
        if name in config and config[name]:
            cfg = config[name]
            if isinstance(cfg, list):
                 return None
            params = cfg.get('params', {})
            params.update(extra_params)
            return get_instance(
                module_name=cfg['module'],
                class_name=cfg['class'],
                params=params
            )
        return None

    def construct_prompt(self, generation_context: str, context_docs: list, context_metadatas: list) -> str:
        """LLMに渡す最終的なプロンプトを組み立てる"""
        context_str = ""
        for i, (doc, meta) in enumerate(zip(context_docs, context_metadatas)):
            source_info = f"出典: {meta.get('source', 'N/A')}, 疾患: {meta.get('disease', 'N/A')}, セクション: {meta.get('section', 'N/A')}, level: {meta.get('level', 'N/A')}"
            context_str += f"[参考情報 {i+1}] ({source_info})\n"
            context_str += f"{doc}\n\n"

        prompt = f"""# 役割
あなたは、臨床経験が豊富なリハビリテーション専門家（理学療法士・作業療法士）です。
提供された「患者情報」と「参考情報（最新のガイドライン等）」を基に、専門的かつ個別性の高いリハビリテーション実施計画書の草案を日本語で作成してください。

# 指示
- **最重要**: 「参考情報」を最も重要な根拠としてください。参考情報に記載のあるエビデンスや推奨事項を積極的に治療計画に反映させてください。
- **引用**: 参考情報を根拠とした記述には、文末に必ず `[番号]` の形式で出典番号を付記してください。複数の情報を参考にした場合は `[番号1, 番号2]` のように記述してください。
- **構造化**: 以下の「あなたの回答」セクションの項目に従って、漏れなく記述してください。
- **具体性**: 抽象的な表現は避け、誰が読んでも理解できる具体的な内容を記述してください。特に目標設定や治療内容は、具体的な数値や動作を用いてください。

# 患者情報
{generation_context}

# 参考情報 (ガイドライン等)
{context_str}

# あなたの回答 (リハビリテーション実施計画書 草案)
"""
        return prompt

    def query(self, patient_info: str, use_structured_output: bool = False):
        print(f"\n[受け取った患者情報]:\n{indent(patient_info, '  ')}")

        # 1. 検索用の短いクエリを生成
        search_query = create_search_query(patient_info)
        print(f"\n[生成された検索クエリ]: {search_query}")
        
        # 2. (Self-RAG) 検索が必要か判断
        if self.judge and self.judge.judge(search_query) == "NO_RETRIEVAL":
            print("\n[ステップ6/7] LLMで直接回答を生成中...")
            direct_prompt = f"あなたは親切なAIアシスタントです。以下の質問に簡潔に答えてください。\n質問: {patient_info}\n回答:"
            final_answer = self.llm.generate(direct_prompt)
            print("\n" + "="*50 + "\n[最終回答 (検索なし)]\n" + str(final_answer) + "\n" + "="*50 + "\n")
            return { "answer": final_answer, "contexts": [] }
        
        # 3. (オプション) クエリ拡張
        search_queries = [search_query]
        if self.query_enhancer:
            print("\n[ステップ1/7] クエリを拡張中...")
            search_queries = self.query_enhancer.enhance(search_query)
            if not isinstance(search_queries, list):
                search_queries = [search_queries]
        else:
            print("\n[ステップ1/7] クエリ拡張はスキップされました。")

        # 4. 検索実行
        print("\n[ステップ2/7] 関連文書を検索中...")
        all_docs = {}
        for q in search_queries:
            if len(search_queries) > 1: print(f"  - クエリ '{q}' で検索...")
            results = self.retriever.retrieve(q, n_results=10)
            if results and results.get('documents') and results['documents'][0]:
                for i, doc_text in enumerate(results['documents'][0]):
                    if doc_text not in all_docs:
                        all_docs[doc_text] = results['metadatas'][0][i]
        docs, metadatas = list(all_docs.keys()), list(all_docs.values())
        print(f"  - 合計で {len(docs)}件のユニークな文書を取得しました。")

        # 5. (オプション) リランキング
        if self.reranker:
            print("\n[ステップ3/7] CrossEncoderで検索結果をリランキング中...")
            docs, metadatas = self.reranker.rerank(search_query, docs, metadatas)
            print(f"  - リランキングが完了しました。")
        else:
            print("\n[ステップ3/7] リランキングはスキップされました。")
        
        # 6. (オプション) フィルタリング
        if self.filters:
            print("\n[ステップ4/7] 検索結果をフィルタリング中...")
            original_doc_count = len(docs)
            for f in self.filters:
                print(f"  - フィルター '{f.__class__.__name__}' を実行中...")
                docs, metadatas = f.filter(search_query, docs, metadatas)
            
            excluded_count = original_doc_count - len(docs)
            print(f"  - フィルタリング後、{len(docs)}件の文書が残りました。 ({excluded_count}件を除外)")
        else:
            print("\n[ステップ4/7] フィルタリングはスキップされました。")
            
        if not docs:
            not_found_message = "参考情報の中に関連する情報が見つかりませんでした。"
            print(f"\n[最終回答]\n{not_found_message}")
        #     return { "answer": not_found_message, "contexts": [] }
        
        # 7. プロンプト構築と最終回答の生成
        print("\n[ステップ5/7] LLM用のプロンプトを構築中...")
        top_k = 5
        final_docs, final_metadatas = docs[:top_k], metadatas[:top_k]
        print(f"  - 最も関連性の高い上位{len(final_docs)}件を使用します。")
        
        # ここで匿名化処理を実行
        anonymized_patient_info = anonymize_patient_info(patient_info)
        print(f"\n[匿名化された生成用コンテキスト]:\n{indent(anonymized_patient_info, '  ')}")

        # 生成には匿名化された完全な患者情報を使用
        final_prompt = self.construct_prompt(anonymized_patient_info, final_docs, final_metadatas)

        print("\n[ステップ6/7] LLMで最終回答を生成中...")
        schema_to_use = RehabPlanSchema if use_structured_output else None
        final_answer = self.llm.generate(final_prompt, response_schema=schema_to_use)
        
        return { "answer": final_answer, "contexts": final_docs }

def main():
    parser = argparse.ArgumentParser(description="RAGパイプライン実行スクリプト")
    parser.add_argument("--config", type=str, default="rag_config.yaml", help="使用するRAGパイプラインを定義した設定ファイル")
    args = parser.parse_args()
    
    config = load_active_pipeline_config(args.config)
    pipeline = RAGPipeline(config)
    
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
    
    for i, q in enumerate(test_queries):
        is_structured = (i == 0)
        print(f"\n{'='*20} テストクエリ {i+1} {'(構造化出力)' if is_structured else ''} を実行 {'='*20}")
        result = pipeline.query(q, use_structured_output=is_structured)
        
        print("\n" + "="*50)
        print("[最終回答]")
        print(result["answer"])
        
        if result["contexts"]:
            print("\n--- AIが回答生成に利用した参考情報 ---")
            for j, context in enumerate(result["contexts"]):
                print(f"\n[参考情報 {j+1}]")
                print(indent(context, '  '))
        print("="*50 + "\n")
        
        time.sleep(1) 

    print("\n\n対話モードを開始します。終了するには 'q' または 'exit' と入力してください。")
    print("患者情報を入力するか、簡単な質問を入力してください。")
    while True:
        user_input = input("\n質問または患者情報を入力してください: ")
        if user_input.lower() in ["q", "exit"]:
            print("終了します。")
            break
        if user_input:
            result = pipeline.query(user_input, use_structured_output=False)
            
            print("\n" + "="*50)
            print("[最終回答]")
            print(result["answer"])

            if result["contexts"]:
                print("\n--- AIが回答生成に利用した参考情報 ---")
                for j, context in enumerate(result["contexts"]):
                    print(f"\n[参考情報 {j+1}]")
                    print(indent(context, '  '))
            print("="*50 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"パイプラインの実行中に致命的なエラーが発生しました: {e}")