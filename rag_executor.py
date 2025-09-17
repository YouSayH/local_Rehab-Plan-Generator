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
    def __init__(self, config_path='rag_config.yaml'):
        # 1. & 2. パイプライン設定の読み込み
        with open(config_path, 'r', encoding='utf-8') as f:
            app_config = yaml.safe_load(f)
        pipeline_name = app_config.get('active_pipeline')
        if not pipeline_name:
            raise ValueError("rag_config.yamlに 'active_pipeline' が指定されていません。")
        
        pipeline_config_path = os.path.join('Rehab_RAG', 'experiments', pipeline_name, 'config.yaml')
        if not os.path.exists(pipeline_config_path):
            raise FileNotFoundError(f"設定ファイルが見つかりません: {pipeline_config_path}")
        with open(pipeline_config_path, 'r', encoding='utf-8') as f:
            self.pipeline_config = yaml.safe_load(f)

        # --- ▼▼▼ ここから最後の修正 ▼▼▼ ---
        # 実行中のパイプラインのディレクトリを基準パスとして保持
        self.experiment_dir = os.path.dirname(pipeline_config_path)
        # --- ▲▲▲ 修正ここまで ▲▲▲ ---

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
        
        if 'embedder' not in specific_config and 'build_components' in self.pipeline_config:
            embedder_cfg = self.pipeline_config.get('build_components', {}).get('embedder')
            if embedder_cfg:
                print("INFO: 'query_components'にembedderがないため、'build_components'から読み込みます。")
                class_name = embedder_cfg.get('class_name') or embedder_cfg.get('class')
                self.components['embedder'] = get_instance(embedder_cfg['module'], class_name, embedder_cfg.get('params', {}))

        for name, config in specific_config.items():
            if config:
                params = config.get('params', {}).copy() # .copy()で元のconfigを汚染しないようにする
                class_name = config.get('class_name') or config.get('class')
                
                # --- ▼▼▼ ここから最後の修正 ▼▼▼ ---
                # パスの自動解決ロジック
                # 'path' または 'db_path' というキーを持つパラメータを絶対パスに変換
                for path_key in ['path', 'db_path', 'bm25_path']:
                    if path_key in params and isinstance(params[path_key], str) and not os.path.isabs(params[path_key]):
                        # 相対パスをexperimentディレクトリからの絶対パスに変換
                        absolute_path = os.path.join(self.experiment_dir, params[path_key])
                        params[path_key] = os.path.normpath(absolute_path)
                        print(f"INFO: パラメータ '{path_key}' を絶対パスに変換しました: {params[path_key]}")
                # --- ▲▲▲ 修正ここまで ▲▲▲ ---

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
        self.filter = self.components.get('filter')

    def _construct_prompt(self, query: str, docs: list) -> str:
        context = "\\n\\n".join(docs)
        return f"""以下の参考情報のみに基づいて、質問に日本語で回答してください。
参考情報:
{context}

質問: {query}
"""

    def execute(self, patient_facts: dict):
        if not self.llm or not self.retriever:
            error_msg = "必須コンポーネントが初期化されていません。"
            if not self.llm: error_msg += " [LLMがNoneです]"
            if not self.retriever: error_msg += " [RetrieverがNoneです]"
            return {"error": error_msg}
            
        query_for_retrieval = f"{patient_facts.get('基本情報', {}).get('算定病名', '')} {patient_facts.get('担当者からの所見', '')}"
        
        if self.judge and not self.judge.judge(query_for_retrieval):
            return self.llm.generate(query_for_retrieval)

        search_queries = [query_for_retrieval]
        if self.query_enhancer:
            search_queries = self.query_enhancer.enhance(query_for_retrieval)
            if not isinstance(search_queries, list): search_queries = [search_queries]
        
        all_docs = {}
        if self.retriever:
            for q in search_queries:
                results = self.retriever.retrieve(q, n_results=10)
                if results and results.get('documents') and results['documents'][0]:
                    for i, doc_text in enumerate(results['documents'][0]):
                        if doc_text not in all_docs:
                            all_docs[doc_text] = results['metadatas'][0][i]
        
        docs = list(all_docs.keys())
        metadatas = list(all_docs.values())
        
        if self.reranker and docs:
            docs, metadatas = self.reranker.rerank(query_for_retrieval, docs, metadatas)

        if self.filter and docs:
            docs, metadatas = self.filter.filter(query_for_retrieval, docs, metadatas)
            
        final_docs = docs[:5]
        if not final_docs:
            return {"error": "関連する情報が見つかりませんでした。"}

        final_prompt = self._construct_prompt(query_for_retrieval, final_docs)
        response = self.llm.generate(final_prompt, response_schema=RehabPlanSchema)
        
        if isinstance(response, dict) and "error" in response:
            return response
        else:
            return response.model_dump()