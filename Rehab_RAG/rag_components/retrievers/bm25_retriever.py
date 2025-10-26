import os
import pickle
from rank_bm25 import BM25Okapi
from tqdm import tqdm
import MeCab


class BM25Retriever:
    """
    [手法解説: キーワード検索 (BM25)]
    ベクトル検索が苦手とする固有名詞や専門用語の検索を補完するためのキーワード検索エンジン。
    TF-IDFを改良したアルゴリズムで、単語の出現頻度と希少性に基づいて文書の関連性をスコアリングします。

    役割:
    - (データベース構築時) 全てのチャンクを形態素解析し、転置インデックスを作成して保存する。
    - (クエリ実行時) 質問文を形態素解析し、BM25スコアが最も高いチャンクを検索する。
    """

    def __init__(self, path: str, collection_name: str):
        """
        コンストラクタ。インデックスファイルのパスを設定します。

        Args:
            path (str): BM25インデックスを保存するディレクトリのパス。
            collection_name (str): インデックスファイル名のプレフィックス。
        """
        self.index_path = os.path.join(path, f"{collection_name}_bm25.pkl")
        self.mecab = MeCab.Tagger("-Owakati")
        self.bm25 = None
        self.chunks = []

    def _tokenize(self, text: str) -> list[str]:
        """テキストを分かち書きする内部メソッド"""
        return self.mecab.parse(text).strip().split()

    def add_documents(self, chunks: list[dict]):
        """
        チャンクのリストからBM25インデックスを構築し、ファイルに保存します。

        Args:
            chunks (list[dict]): チャンク情報の辞書のリスト。
        """
        print("BM25インデックスの構築を開始します...")
        self.chunks = chunks

        tokenized_corpus = [
            self._tokenize(chunk["text"])
            for chunk in tqdm(chunks, desc="Tokenizing for BM25")
        ]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # インデックスとチャンクデータを保存
        with open(self.index_path, "wb") as f:
            pickle.dump((self.bm25, self.chunks), f)
        print(f"BM25インデックスを '{self.index_path}' に保存しました。")

    def load_index(self):
        """保存されたBM25インデックスを読み込む"""
        if os.path.exists(self.index_path):
            with open(self.index_path, "rb") as f:
                self.bm25, self.chunks = pickle.load(f)
            # print("BM25インデックスを読み込みました。")
        else:
            raise FileNotFoundError(
                f"BM25インデックスファイルが見つかりません: {self.index_path}"
            )

    def retrieve(self, query_text: str, n_results: int = 10) -> dict:
        """
        与えられたクエリテキストにキーワードが最も一致するドキュメントを検索します。

        Args:
            query_text (str): ユーザーからの質問文。
            n_results (int): 取得する検索結果の数。

        Returns:
            dict: BM25からの検索結果。ChromaDBの出力形式と互換性があります。
        """
        if self.bm25 is None:
            self.load_index()

        tokenized_query = self._tokenize(query_text)

        # BM25スコアを計算し、上位n_results件のインデックスを取得
        doc_scores = self.bm25.get_scores(tokenized_query)
        top_n_indices = sorted(
            range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True
        )[:n_results]

        # ChromaDBと同様の形式で結果を返す
        top_chunks = [self.chunks[i] for i in top_n_indices]
        results = {
            "ids": [[chunk["id"] for chunk in top_chunks]],
            "documents": [[chunk["text"] for chunk in top_chunks]],
            "metadatas": [[chunk["metadata"] for chunk in top_chunks]],
            "distances": [
                [doc_scores[i] for i in top_n_indices]
            ],  # BM25スコアを距離の代わりに格納
        }
        return results
