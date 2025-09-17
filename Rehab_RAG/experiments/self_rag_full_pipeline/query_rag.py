"""
RAGクエリ実行スクリプト (The Query Engine / 最終汎用版)

[このスクリプトの役割]
このスクリプトは、RAGパイプラインの「実行」フェーズを担当する心臓部です。
`config.yaml` ファイルで定義された設定に基づき、ユーザーからの質問に対して
一連のRAGプロセスを実行し、最終的な回答を生成します。

[サポートするワークフロー]
1. Self-RAG: 検索が必要かAIが自己判断し、不要な検索をスキップします。
2. Multi-Query: １つの質問から複数の検索クエリを自動生成し、網羅性を高めます。
3. 柔軟なコンポーネント選択: config.yamlの設定に応じて、Retriever, Reranker, Filterなどを
   自由に付け替えてパイプラインを構築します。

[実行方法]
プロジェクトのルートディレクトリから、以下のコマンドで実行します。
`python .\\experiments\\<実験名>\\query_rag.py`
"""
import yaml
import importlib
import time
import os
import sys

# プロジェクトのルートディレクトリをPythonのパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..')))

def load_config(config_path='config.yaml'):
    """YAML設定ファイルを読み込む"""
    full_path = os.path.join(SCRIPT_DIR, config_path)
    with open(full_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_instance(module_name, class_name, params={}):
    """モジュールとクラス名からインスタンスを動的に生成する"""
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    return class_(**params)

class RAGPipeline:
    def __init__(self, config):
        print("--- RAGパイプラインの初期化を開始 ---")
        q_cfg = config['query_components']
        
        # LLMは全てのコンポーネントで共有される可能性があるため、最初に初期化
        llm_cfg = q_cfg['llm']
        self.llm = get_instance(
            module_name=llm_cfg['module'],
            class_name=llm_cfg['class'],
            params=llm_cfg.get('params', {})
        )

        # Embedderも同様に最初に初期化
        embedder_cfg = q_cfg['embedder']
        self.embedder = get_instance(
            module_name=embedder_cfg['module'],
            class_name=embedder_cfg['class'],
            params=embedder_cfg.get('params', {})
        )

        # Self-RAGの判断役(Judge)を初期化
        if 'judge' in q_cfg and q_cfg['judge']:
            judge_cfg = q_cfg['judge']
            judge_params = judge_cfg.get('params', {})
            judge_params['llm'] = self.llm 
            self.judge = get_instance(
                module_name=judge_cfg['module'],
                class_name=judge_cfg['class'],
                params=judge_params
            )
        else:
            self.judge = None

        # クエリ拡張(Enhancer)を初期化
        if 'query_enhancer' in q_cfg and q_cfg['query_enhancer']:
            enhancer_cfg = q_cfg['query_enhancer']
            enhancer_params = enhancer_cfg.get('params', {})
            enhancer_params['llm'] = self.llm
            self.query_enhancer = get_instance(
                module_name=enhancer_cfg['module'],
                class_name=enhancer_cfg['class'],
                params=enhancer_params
            )
        else:
            self.query_enhancer = None

        # リランカー(Reranker)を初期化
        if 'reranker' in q_cfg and q_cfg['reranker']:
            reranker_cfg = q_cfg['reranker']
            self.reranker = get_instance(
                module_name=reranker_cfg['module'],
                class_name=reranker_cfg['class'],
                params=reranker_cfg.get('params', {})
            )
        else:
            self.reranker = None

        # フィルタ(Filter)を初期化
        if 'filter' in q_cfg and q_cfg['filter']:
            filter_cfg = q_cfg['filter']
            filter_params = filter_cfg.get('params', {})
            filter_params['llm'] = self.llm # SelfReflectiveFilterなどがLLMを使えるように
            self.filter = get_instance(
                module_name=filter_cfg['module'],
                class_name=filter_cfg['class'],
                params=filter_params
            )
        else:
            self.filter = None
            
        # リトリーバー(Retriever)を初期化 (動的読み込み)
        retriever_cfg = q_cfg.get('retriever')
        full_db_path = os.path.join(SCRIPT_DIR, config['database']['path'])
        
        if retriever_cfg:
            retriever_params = {
                "path": full_db_path,
                "collection_name": config['database']['collection_name'],
                "embedder": self.embedder,
                **retriever_cfg.get('params', {})
            }
            self.retriever = get_instance(
                retriever_cfg['module'],
                retriever_cfg['class'],
                retriever_params
            )
        else: # 後方互換性のため、retriever指定がない場合はChromaDBをデフォルトとする
            retriever_params = {
                "path": full_db_path,
                "collection_name": config['database']['collection_name'],
                "embedder": self.embedder
            }
            self.retriever = get_instance(
                'rag_components.retrievers.chromadb_retriever', 
                'ChromaDBRetriever', 
                retriever_params
            )

        print("--- 初期化完了 ---")

    def construct_prompt(self, query: str, context_docs: list, context_metadatas: list) -> str:
        context_str = ""
        for i, (doc, meta) in enumerate(zip(context_docs, context_metadatas)):
            source_info = f"出典: {meta.get('source', 'N/A')}, 疾患: {meta.get('disease', 'N/A')}, セクション: {meta.get('section', 'N/A')}, level: {meta.get('level', 'N/A')}"
            context_str += f"[参考情報 {i+1}] ({source_info})\n"
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

        # [ステップ0/7] (Self-RAG) 検索が必要か判断する
        if self.judge:
            print("\n[ステップ0/7] 検索が必要か判断中...")
            decision = self.judge.judge(query)
            if decision == "NO_RETRIEVAL":
                print("\n[ステップ6/7] LLMで直接回答を生成中...")
                direct_prompt = f"あなたは親切なAIアシスタントです。以下の質問に簡潔に答えてください。\n質問: {query}\n回答:"
                final_answer = self.llm.generate(direct_prompt)
                print("\n" + "="*50)
                print("[最終回答 (検索なし)]")
                print(final_answer)
                print("="*50 + "\n")
                return { "answer": final_answer, "contexts": [] }
        
        # [ステップ1/7] クエリを拡張する (Multi-Query / HyDE)
        if self.query_enhancer:
            print("\n[ステップ1/7] クエリを拡張中...")
            search_queries = self.query_enhancer.enhance(query)
            if not isinstance(search_queries, list):
                search_queries = [search_queries]
        else:
            print("\n[ステップ1/7] クエリ拡張はスキップされました。")
            search_queries = [query]

        # [ステップ2/7] 関連文書を検索する
        print("\n[ステップ2/7] 関連文書を検索中...")
        all_docs = {}
        for q in search_queries:
            if len(search_queries) > 1:
                print(f"  - クエリ '{q}' で検索...")
            results = self.retriever.retrieve(q, n_results=10)
            if results and results.get('documents') and results['documents'][0]:
                for i, doc_text in enumerate(results['documents'][0]):
                    if doc_text not in all_docs:
                        all_docs[doc_text] = results['metadatas'][0][i]
        docs = list(all_docs.keys())
        metadatas = list(all_docs.values())
        print(f"  - 合計で {len(docs)}件のユニークな文書を取得しました。")

        # [ステップ3/7] 検索結果をリランキングする
        if self.reranker:
            print("\n[ステップ3/7] CrossEncoderで検索結果をリランキング中...")
            reranked_docs, reranked_metadatas = self.reranker.rerank(query, docs, metadatas)
            docs, metadatas = reranked_docs, reranked_metadatas
            print(f"  - リランキングが完了しました。")
        else:
            print("\n[ステップ3/7] リランキングはスキップされました。")
        
        # [ステップ4/7] 検索結果をフィルタリングする
        if self.filter:
            print("\n[ステップ4/7] 検索結果をフィルタリング中...")
            filtered_docs, filtered_metadatas = self.filter.filter(query, docs, metadatas)
            print(f"  - フィルタリング後、{len(filtered_docs)}件の文書が残りました。 ({len(docs) - len(filtered_docs)}件を除外)")
            docs, metadatas = filtered_docs, filtered_metadatas
        else:
            print("\n[ステップ4/7] フィルタリングはスキップされました。")
            
        # if not docs:
        #     print("\n[最終回答]\n参考情報の中に関連する情報が見つかりませんでした。")
        #     return
            


        if not docs:
            not_found_message = "参考情報の中に関連する情報が見つかりませんでした。"
            print(f"\n[最終回答]\n{not_found_message}")
            return {
                "answer": not_found_message,
                "contexts": []
            }

        # [ステップ5/7] LLM用のプロンプトを構築する
        print("\n[ステップ5/7] LLM用のプロンプトを構築中...")
        top_k = 5
        final_docs = docs[:top_k]
        final_metadatas = metadatas[:top_k]
        print(f"  - 最も関連性の高い上位{len(final_docs)}件を使用します。")
        final_prompt = self.construct_prompt(query, final_docs, final_metadatas)

        # [ステップ6/7] LLMで最終回答を生成する
        print("\n[ステップ6/7] LLMで最終回答を生成中...")
        final_answer = self.llm.generate(final_prompt)
        
        print("\n" + "="*50)
        print("[最終回答]")
        print(final_answer)
        print("="*50 + "\n")
        return { "answer": final_answer, "contexts": final_docs }

def main():
    config = load_config()
    pipeline = RAGPipeline(config)
    
    # === 初期テストクエリ ===
    test_queries = [
        "こんにちは、調子はどうですか？",
        "大腿骨近位部骨折の術後、理学療法の頻度を増やすとどうなりますか？",
        "変形性股関節症の発症を予防するには、運動療法だけで十分ですか？",
        "脳卒中患者に対する有酸素運動は推奨されますか？",
        "肩関節周囲炎の炎症期に、痛みを我慢して積極的に運動したほうがいいですか？"
    ]
    for q in test_queries:
        pipeline.query(q)
        time.sleep(1) 

    # === 対話モード ===
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