from .chromadb_retriever import ChromaDBRetriever
from .bm25_retriever import BM25Retriever

class HybridRetriever:
    """
    [手法解説: ハイブリッド検索 (Hybrid Search)]
    意味の近さで検索する「ベクトル検索」と、キーワードの一致で検索する「BM25検索」を
    組み合わせることで、両者の長所を活かし、短所を補い合う検索手法です。

    仕組み (Reciprocal Rank Fusion - RRF):
    1. ベクトル検索とBM25検索をそれぞれ独立して実行する。
    2. 各検索結果のランキング(順位)のみに着目する。
       (例: 1位→1点, 2位→1/2点, 3位→1/3点, ...)
    3. 両方の検索結果に登場する各文書について、それぞれのランキングスコアを合計する。
    4. 合計スコアが高い順に文書を並べ替え、最終的な検索結果とする。

    期待される効果:
    - 専門用語や固有名詞での検索精度（キーワード検索の長所）と、
      曖昧な質問への対応力（ベクトル検索の長所）を両立できる。
    """
    def __init__(self, path: str, collection_name: str, embedder, k: int = 60):
        """
        コンストラクタ。ベクトルリトリーバーとキーワードリトリーバーを初期化します。
        
        Args:
            path (str): データベースのパス。
            collection_name (str): コレクション名。
            embedder: Embedderインスタンス。
            k (int): RRFのランキング計算で使用する定数。
        """
        self.vector_retriever = ChromaDBRetriever(path, collection_name, embedder)
        self.keyword_retriever = BM25Retriever(path, collection_name)
        self.k = k

    def retrieve(self, query_text: str, n_results: int = 10) -> dict:
        """
        ベクトル検索とキーワード検索を実行し、RRFで結果を統合して返す。
        """
        # 1. 各リトリーバーで検索を実行
        vector_results = self.vector_retriever.retrieve(query_text, n_results=n_results * 2)
        keyword_results = self.keyword_retriever.retrieve(query_text, n_results=n_results * 2)

        # 2. RRFスコアを計算
        rrf_scores = {}
        
        # ベクトル検索の結果を処理
        if vector_results['ids'][0]:
            for rank, doc_id in enumerate(vector_results['ids'][0]):
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = 0
                rrf_scores[doc_id] += 1 / (self.k + rank + 1)
        
        # キーワード検索の結果を処理
        if keyword_results['ids'][0]:
            for rank, doc_id in enumerate(keyword_results['ids'][0]):
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = 0
                rrf_scores[doc_id] += 1 / (self.k + rank + 1)

        # 3. スコアに基づいてソート
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda id: rrf_scores[id], reverse=True)
        
        # 上位n_results件に絞り込み
        top_doc_ids = sorted_doc_ids[:n_results]

        # 4. 最終的な結果を構築
        # (ChromaDBとBM25の結果から、必要な情報を再取得)
        all_docs = {}
        if vector_results['ids'][0]:
            for i, doc_id in enumerate(vector_results['ids'][0]):
                all_docs[doc_id] = {
                    'text': vector_results['documents'][0][i],
                    'metadata': vector_results['metadatas'][0][i]
                }
        if keyword_results['ids'][0]:
             for i, doc_id in enumerate(keyword_results['ids'][0]):
                if doc_id not in all_docs: # 重複を避ける
                    all_docs[doc_id] = {
                        'text': keyword_results['documents'][0][i],
                        'metadata': keyword_results['metadatas'][0][i]
                    }

        final_documents = [all_docs[doc_id]['text'] for doc_id in top_doc_ids if doc_id in all_docs]
        final_metadatas = [all_docs[doc_id]['metadata'] for doc_id in top_doc_ids if doc_id in all_docs]

        return {
            'documents': [final_documents],
            'metadatas': [final_metadatas]
        }

    def add_documents(self, chunks: list[dict]):
        """
        両方のリトリーバーにドキュメントを追加します。
        """
        self.vector_retriever.add_documents(chunks)
        self.keyword_retriever.add_documents(chunks)