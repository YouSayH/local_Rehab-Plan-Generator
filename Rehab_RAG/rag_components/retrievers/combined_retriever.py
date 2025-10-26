from .graph_retriever import GraphRetriever
from .hybrid_retriever import HybridRetriever

class CombinedRetriever:
    """
    [手法解説: 複合検索 (Combined Retrieval)]
    グラフ検索とハイブリッド検索を同時に実行し、それぞれの結果を統合するリトリーバー。
    これにより、関係性の問いに強いグラフの利点と、網羅性に優れたハイブリッド検索の
    利点を両立させることを目指します。
    """
    def __init__(self, llm, path: str, collection_name: str, embedder, **kwargs):
        """
        コンストラクタ。GraphRetrieverとHybridRetrieverを初期化します。
        """
        print("Combined Retrieverを初期化中...")
        self.graph_retriever = GraphRetriever(llm=llm)
        self.hybrid_retriever = HybridRetriever(path, collection_name, embedder)
        print("Combined Retrieverの初期化完了。")

    def retrieve(self, query_text: str, n_results: int = 10) -> dict:
        """
        両方のリトリーバーで検索を実行し、結果をマージして返す。
        """
        print("  - GraphRetrieverで検索中...")
        graph_results = self.graph_retriever.retrieve(query_text, n_results=n_results)
        
        print("  - HybridRetrieverで検索中...")
        hybrid_results = self.hybrid_retriever.retrieve(query_text, n_results=n_results)

        # 結果を統合し、重複を排除する
        all_docs = {}
        
        # グラフ検索の結果を追加
        if graph_results['documents'] and graph_results['documents'][0]:
            for i, doc_text in enumerate(graph_results['documents'][0]):
                if doc_text not in all_docs:
                    all_docs[doc_text] = graph_results['metadatas'][0][i]

        # ハイブリッド検索の結果を追加
        if hybrid_results['documents'] and hybrid_results['documents'][0]:
            for i, doc_text in enumerate(hybrid_results['documents'][0]):
                if doc_text not in all_docs:
                    all_docs[doc_text] = hybrid_results['metadatas'][0][i]
        
        final_documents = list(all_docs.keys())
        final_metadatas = list(all_docs.values())
        
        print(f"  - 統合後、{len(final_documents)}件のユニークな文書を取得しました。")

        return {
            'documents': [final_documents],
            'metadatas': [final_metadatas]
        }

    def add_documents(self, chunks: list[dict]):
        """
        このRetrieverは検索専用のため、このメソッドは何もしません。
        DB構築は個別のBuilderで行います。
        """
        pass