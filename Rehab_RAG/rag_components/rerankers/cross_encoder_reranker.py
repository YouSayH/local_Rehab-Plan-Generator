from sentence_transformers.cross_encoder import CrossEncoder
import torch
import numpy as np

class CrossEncoderReranker:
    """
    [手法解説: Reranking with Cross-Encoder]
    リトリーバーによって取得された文書群を、より精度の高いモデルで並べ替えるコンポーネント。
    
    仕組み:
    1. Bi-Encoder(Retriever)が、質問と文書をそれぞれ個別にベクトル化し、高速に候補を絞り込む。
    2. Cross-Encoder(Reranker)は、「質問」と「候補文書」をペアで入力として受け取る。
    3. 文脈を直接比較することで、より正確な関連性スコアを算出し、そのスコアに基づいて文書を並べ替える。

    期待される効果:
    - Bi-Encoderが見逃しがちな、より文脈的に関連性の高い文書を上位に引き上げる。
    - LLMに渡すコンテキストの質を向上させ、最終的な回答の精度を高める。
    - 計算コストが高いため、リトリーバーで絞り込んだ後の少数の候補に対して適用するのが効果的。
    """
    def __init__(self, model_name: str, device: str = "auto"):
        """
        コンストラクタ。指定されたCross-Encoderモデルをロードします。
        
        Args:
            model_name (str): Hugging Face上のモデル名 (例: "bge-reranker-base")
            device (str): "cuda", "cpu", "auto"のいずれか。
        """
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Rerankerモデル ({model_name}) を {self.device} にロード中...")
        self.model = CrossEncoder(model_name, max_length=512, device=self.device)
        print("Rerankerモデルのロード完了。")

    def rerank(self, query: str, documents: list[str], metadatas: list[dict]) -> tuple[list[str], list[dict]]:
        """
        Cross-Encoderモデルを使用して、文書をクエリとの関連性スコアで並べ替える。
        
        Args:
            query (str): ユーザーの元の質問文。
            documents (list[str]): 検索された文書チャンクのリスト。
            metadatas (list[dict]): 各文書チャンクに対応するメタデータのリスト。

        Returns:
            tuple[list[str], list[dict]]: スコアに基づいて並べ替えられた文書とメタデータのタプル。
        """
        if not documents:
            return [], []

        # (query, document) のペアを作成
        sentence_pairs = [[query, doc] for doc in documents]

        # スコアを計算
        scores = self.model.predict(sentence_pairs, show_progress_bar=False)
        
        # スコアに基づいてソート
        sorted_indices = np.argsort(scores)[::-1] # 降順にソート

        reranked_docs = [documents[i] for i in sorted_indices]
        reranked_metadatas = [metadatas[i] for i in sorted_indices]
        
        return reranked_docs, reranked_metadatas