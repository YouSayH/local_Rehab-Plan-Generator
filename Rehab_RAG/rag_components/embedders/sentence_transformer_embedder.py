from sentence_transformers import SentenceTransformer
import torch


class SentenceTransformerEmbedder:
    """
    [手法解説: Embedding]
    テキストを「意味を捉えた数値のベクトル」に変換するコンポーネント。
    ここでは、Hugging Faceで公開されている`sentence-transformers`ライブラリを使用します。
    モデルを変えることで、Embeddingの性能や特性を変えることができます。

    目的:
    - テキスト間の意味的な類似度を計算可能にする。
    - キーワード検索では見つけられない、意図が近い文書を発見する。
    """

    def __init__(self, model_name: str, device: str = "auto"):
        """
        コンストラクタ。指定されたモデルをロードします。

        Args:
            model_name (str): Hugging Face上のモデル名 (例: "intfloat/multilingual-e5-large")
            device (str): "cuda", "cpu", "auto"のいずれか。autoの場合、GPUが利用可能ならGPUを使用します。
        """
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        print(f"Embeddingモデル ({model_name}) を {self.device} にロード中...")
        self.model = SentenceTransformer(model_name, device=self.device)
        print("Embeddingモデルのロード完了。")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        複数のドキュメント（チャンク）を一度にベクトル化するメソッド。
        データベース構築時に使用します。
        """
        embeddings = self.model.encode(
            texts, convert_to_tensor=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """
        単一のクエリテキストをベクトル化するメソッド。
        ユーザーからの質問を検索する際に使用します。
        """
        embedding = self.model.encode(text, convert_to_tensor=True)
        return embedding.tolist()
