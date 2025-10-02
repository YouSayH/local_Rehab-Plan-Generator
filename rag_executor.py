import yaml
import sys
import os
import json
import importlib

# gemini_client.pyで定義されている、アプリケーション本体のデータ構造スキーマをインポート
# from gemini_client import RehabPlanSchema # 循環参照が発生してしまいます。
from schemas import RehabPlanSchema

# Rehab_RAGライブラリへのパスを追加
REHAB_RAG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Rehab_RAG'))
if REHAB_RAG_PATH not in sys.path:
    sys.path.append(REHAB_RAG_PATH)

def get_instance(module_name, class_name, params={}):
    """モジュール名とクラス名からインスタンスを動的に生成するヘルパー関数"""
    try:
        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        return class_(**params)
    except Exception as e:
        print(f"コンポーネント '{class_name}' のインスタンス化に失敗: {e}")
        return None

class RAGExecutor:
    """
    rag_config.yamlに基づいてRAGパイプラインを動的に構築し、実行するクラス。
    """

    def __init__(self, pipeline_name: str):
        """
        コンストラクタ。実行するパイプライン名を直接引数で受け取るように変更。
        
        Args:
            pipeline_name (str): 実行対象の実験フォルダ名 (例: "raptor_experiment")
        """
        # 1. & 2. パイプライン設定の読み込み
        if not pipeline_name:
            raise ValueError("RAGExecutorの初期化には 'pipeline_name' が必要です。")

        pipeline_config_path = os.path.join('Rehab_RAG', 'experiments', pipeline_name, 'config.yaml')
        if not os.path.exists(pipeline_config_path):
            raise FileNotFoundError(f"設定ファイルが見つかりません: {pipeline_config_path}")
        with open(pipeline_config_path, 'r', encoding='utf-8') as f:
            self.pipeline_config = yaml.safe_load(f)

        # 実行中のパイプラインのディレクトリを基準パスとして保持
        self.experiment_dir = os.path.dirname(pipeline_config_path)

        # 3. RAGパイプラインのコンポーネントを初期化
        self.components = {}
        if 'common_components' in self.pipeline_config:
            common_config = self.pipeline_config.get('common_components', {})
            specific_config = self.pipeline_config.get('pipeline_specific_components', {})
        else:
            print("INFO: 'common_components'が見つからないため、フラットなconfigとして読み込みます。")
            query_cfg = self.pipeline_config.get('query_components', {})
            common_config = {'llm': query_cfg.get('llm')} if 'llm' in query_cfg else {}
            specific_config = {k: v for k, v in query_cfg.items() if k != 'llm'}

        if 'llm' in common_config:
            cfg = common_config['llm']
            class_name = cfg.get('class_name') or cfg.get('class')
            self.components['llm'] = get_instance(cfg['module'], class_name, cfg.get('params', {}))

        # embedderを先に初期化するロジック
        embedder_cfg = specific_config.pop('embedder', None) # specific_configからembedderを一旦取り出す
        if not embedder_cfg and 'build_components' in self.pipeline_config:
             embedder_cfg = self.pipeline_config.get('build_components', {}).get('embedder')
             if embedder_cfg:
                 print("INFO: 'query_components'にembedderがないため、'build_components'から読み込みます。")
        
        if embedder_cfg:
            class_name = embedder_cfg.get('class_name') or embedder_cfg.get('class')
            self.components['embedder'] = get_instance(embedder_cfg['module'], class_name, embedder_cfg.get('params', {}))

        for name, config in specific_config.items():
            if config:

                # filterがリスト形式の場合、特別にループ処理を行う(フィルターを複数実行できるようにしているため)
                if name == 'filter' and isinstance(config, list):
                    self.components['filters'] = [] # 'filters' (複数形) というキーでリストを準備
                    for filter_cfg in config:
                        params = filter_cfg.get('params', {}).copy()
                        # SelfReflectiveFilterなどがLLMを使えるように依存性を注入
                        params['llm'] = self.components.get('llm') 
                        self.components['filters'].append(
                            get_instance(filter_cfg['module'], filter_cfg.get('class') or filter_cfg.get('class_name'), params)
                        )
                    continue # filterの処理が終わったら次のループへ

                params = config.get('params', {}).copy() # .copy()で元のconfigを汚染しないようにする
                class_name = config.get('class_name') or config.get('class')
                
                # パスの自動解決ロジック
                # 'path' または 'db_path' というキーを持つパラメータを絶対パスに変換
                for path_key in ['path', 'db_path', 'bm25_path']:
                    if path_key in params and isinstance(params[path_key], str) and not os.path.isabs(params[path_key]):
                        # 相対パスをexperimentディレクトリからの絶対パスに変換
                        absolute_path = os.path.join(self.experiment_dir, params[path_key])
                        params[path_key] = os.path.normpath(absolute_path)
                        print(f"INFO: パラメータ '{path_key}' を絶対パスに変換しました: {params[path_key]}")

                if name in ['judge', 'query_enhancer', 'filter'] and 'llm' not in params:
                    params['llm'] = self.components.get('llm')
                if name == 'retriever':
                    if 'embedder' not in params: params['embedder'] = self.components.get('embedder')
                    # 古いconfig形式でretrieverにpathが指定されていない場合、databaseセクションから補完
                    if 'path' not in params and 'database' in self.pipeline_config:
                        db_path = self.pipeline_config.get('database', {}).get('path')
                        if db_path:
                            params['path'] = os.path.normpath(os.path.join(self.experiment_dir, db_path))
                            print(f"INFO: retrieverの'path'をdatabaseセクションから補完: {params['path']}")

                    if 'collection_name' not in params and 'database' in self.pipeline_config:
                         params['collection_name'] = self.pipeline_config.get('database', {}).get('collection_name')

                for key, value in params.items():
                    if isinstance(value, str) and value.startswith('@common_components.'):
                        params[key] = self.components.get(value.split('.')[-1])

                self.components[name] = get_instance(config['module'], class_name, params)
        
        self.llm = self.components.get('llm')
        self.judge = self.components.get('judge')
        self.query_enhancer = self.components.get('query_enhancer')
        self.retriever = self.components.get('retriever')
        self.reranker = self.components.get('reranker')
        # self.filter = self.components.get('filter')
        self.filters = self.components.get('filters', []) # 'filters' (複数形) を取得。なければ空リスト

    def _construct_prompt(self, query: str, docs: list) -> str:
        context = "\\n\\n".join(docs)
        return f"""以下の参考情報のみに基づいて、質問に日本語で回答してください。
参考情報:
{context}

質問: {query}
"""

    def execute(self, patient_facts: dict):
        print(f"DEBUG [rag_executor.py]: '担当者からの所見' received = {patient_facts.get('担当者からの所見')}")
        if not self.llm or not self.retriever:
            error_msg = "必須コンポーネントが初期化されていません。"
            if not self.llm: error_msg += " [LLMがNoneです]"
            if not self.retriever: error_msg += " [RetrieverがNoneです]"
            return {"error": error_msg}

        # 検索クエリの生成  
        query_for_retrieval = f"{patient_facts.get('基本情報', {}).get('算定病名', '')} {patient_facts.get('担当者からの所見', '')}"
        print(f"\n[患者情報から生成されたクエリ]:\n{query_for_retrieval}")


        # selfRAGの判断
        if self.judge and not self.judge.judge(query_for_retrieval):
            print("ジャッジ開始")
            return self.llm.generate(query_for_retrieval)
        else:
            print("ジャッジしません")

        # クエリ拡張(HyDE)
        search_queries = [query_for_retrieval]
        if self.query_enhancer:
            print("クエリ拡張開始")
            search_queries = self.query_enhancer.enhance(query_for_retrieval)
            if not isinstance(search_queries, list):
                search_queries = [search_queries]
        else:
            print("クエリ拡張は実行しません")
            search_queries = [query_for_retrieval]
        
        # 検索
        print("関連文書検索中")
        all_docs = {}
        if self.retriever:
            for q in search_queries:
                if len(search_queries) > 1:
                    print(f"  - クエリ '{q}' で検索")                
                results = self.retriever.retrieve(q, n_results=10)
                if results and results.get('documents') and results['documents'][0]:
                    for i, doc_text in enumerate(results['documents'][0]):
                        if doc_text not in all_docs:
                            all_docs[doc_text] = results['metadatas'][0][i]
        
        docs = list(all_docs.keys())
        metadatas = list(all_docs.values())
        print(f"  - 合計で {len(docs)}件のユニークな文書を取得しました。")
        
        # リランキング(関連度を判断させ並び替える)
        if self.reranker and docs:
            print("検索結果をリランキング開始")
            docs, metadatas = self.reranker.rerank(query_for_retrieval, docs, metadatas)
            print("リランキング終了")
        else:
            print("リランキングはしません。")

        # あっているのか？正しいのかっていうのをフィルタリングする
        # if self.filter and docs:
        #     print("検索結果をフィルタリング開始")
        #     docs, metadatas = self.filter.filter(query_for_retrieval, docs, metadatas)
        #     print(f"フィルタリング後、{len(docs)}件の文書が残りました。")
        # else:
        #      print("フィルタリングはしません。")

        if self.filters and docs: # self.filter を self.filters に変更
            print("検索結果をフィルタリング開始")
            original_doc_count = len(docs)
            # ループで各フィルターを順番に適用する
            for f in self.filters:
                docs, metadatas = f.filter(query_for_retrieval, docs, metadatas)
            print(f"フィルタリング後、{len(docs)}件の文書が残りました。 ({original_doc_count - len(docs)}件を除外)")
        else:
            print("フィルタリングはしません。")            
            
        # プロンプト作成
        print("LLM用のプロンプトを作成中")            
        final_docs = docs[:10]
        # final_docsに対応するメタデータも取得
        final_metadatas = metadatas[:10] 

        if not final_docs:
            print("関連情報が見つからなかったため、処理を終了します。")
            return {
                "answer": {"error": "関連する情報が見つかりませんでした。"},
                "contexts": []
            }

        print(f"最も関連性の高い上位{len(final_docs)}件を使用します。")
        # 根拠情報（ドキュメントとメタデータ）をセットにしてリスト化
        final_contexts_with_metadata = []
        for i in range(len(final_docs)):
            final_contexts_with_metadata.append({
                "content": final_docs[i],
                "metadata": final_metadatas[i] if i < len(final_metadatas) else {}
            })

        final_prompt = self._construct_prompt(query_for_retrieval, final_docs)
        print("LLMで回答生成開始")
        response = self.llm.generate(final_prompt, response_schema=RehabPlanSchema)
        
        # Pydanticモデルのインスタンス or エラー辞書 が返ってくる
        answer_dict = {}

        if isinstance(response, dict) and "error" in response:
            answer_dict = response
        else:
            # Pydanticモデルの場合は .model_dump() で辞書に変換
            answer_dict = response.model_dump()
            print("RAGモデルによる生成が完了")

        # 回答(answer)と、メタデータ付きの根拠(contexts)の両方を辞書として返す
        return {
            "answer": answer_dict,
            "contexts": final_contexts_with_metadata
        }
        