import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_neo4j import Neo4jGraph
import re

class GraphRetriever:
    """
    GraphRetriever: 質問からキーワードを抽出し、グラフから近傍情報を検索するアプローチ。
    LangChainの複雑なチェーンに頼らず、より安定的で直接的な方法を実装する。
    """
    def __init__(self, llm, **kwargs):
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        load_dotenv(dotenv_path=env_path)

        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not all([uri, user, password]):
            raise ValueError("環境変数 NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD が設定されていません。")

        self.graph = Neo4jGraph(url=uri, username=user, password=password)
        # query_rag.pyで初期化された単一のLLMインスタンスを使用する
        self.llm = llm
        
        print("Graph Retriever (キーワード検索版・改) が初期化され、Neo4j に接続しました。")

    def _extract_keywords(self, query_text: str) -> list[str]:
        """LLMを使って、検索クエリからグラフ検索に使う主要なキーワードを抽出する。"""
        prompt = f"""以下の質問文から、ナレッジグラフで検索するべき最も重要なエンティティ（疾患名、治療法、症状など）を5つまで抽出してください。
        回答はPythonのリスト形式（例: ['脳梗塞', 'リハビリテーション', '半側空間無視']）で、キーワードのみを返してください。

        質問文: "{query_text}"
        
        キーワード:"""
        
        # self.llm.generateメソッドを使うように統一
        response = self.llm.generate(prompt)
        
        match = re.search(r'\[(.*?)\]', response)
        if match:
            try:
                keywords = eval(f"[{match.group(1)}]")
                print(f"  - 抽出されたキーワード: {keywords}")
                return [str(k) for k in keywords]
            except:
                return []
        return []

    def retrieve(self, query_text: str, n_results: int = 10) -> dict:
        """
        キーワードを抽出し、それらのキーワードに一致するノードから2ホップ先の情報をグラフから取得する。
        """
        keywords = self._extract_keywords(query_text)
        if not keywords:
            return {"documents": [[]], "metadatas": [[]]}

        all_context_texts = []
        
        # Cypherクエリを、r.contextを返すように変更
        cypher_query = """
        UNWIND $keywords AS keyword
        MATCH (n)
        WHERE toLower(n.id) CONTAINS toLower(keyword)
        MATCH (n)-[r]-(m)
        RETURN r.context AS context
        LIMIT 20
        """
        
        try:
            results = self.graph.query(cypher_query, params={'keywords': keywords})
            
            for record in results:
                # contextプロパティが存在すればリストに追加
                if record['context']:
                    all_context_texts.append(record['context'])
        except Exception as e:
            print(f"エラー: Neo4jクエリの実行中に問題が発生しました: {e}")
            return {"documents": [[]], "metadatas": [[]]}

        if not all_context_texts:
            return {"documents": [[]], "metadatas": [[]]}

        # 重複を排除し、最終的なコンテキストを作成
        unique_context = list(dict.fromkeys(all_context_texts))
        
        return {
            "documents": [unique_context[:n_results]],
            "metadatas": [[{"source": "Knowledge Graph"}] * len(unique_context[:n_results])],
        }

    def add_documents(self, chunks: list[dict]):
        """このRetrieverは検索専用のため、このメソッドは何もしません。"""
        pass