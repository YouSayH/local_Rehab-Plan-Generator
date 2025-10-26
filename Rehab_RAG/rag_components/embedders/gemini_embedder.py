import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from tqdm import tqdm
import backoff

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
dotenv_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path=dotenv_path)

class GeminiEmbedder:
    """
    [手法解説: Gemini Embedding]
    GoogleのGemini API (`gemini-embedding-001`) を使用してテキストをベクトル化するコンポーネント。

    特徴:
    - APIベースであるため、ローカルに大規模なモデルを持つ必要がない。
    - レート制限（1分あたりのリクエスト数）があるため、バッチ処理とAPIコール間の待機が不可欠。
    - RAGのユースケースに合わせて `task_type` を指定することで、検索精度を最適化できる。
    """

    def __init__(self, model_name: str = "gemini-embedding-001", batch_size: int = 32, requests_per_minute: int = 750):
        """
        コンストラクタ。Geminiクライアントを初期化し、レート制限設定を保存します。
        
        Args:
            model_name (str): 使用するGeminiエンベディングモデル名。
            batch_size (int): 一度のAPIコールで処理するテキストの数。レート制限対策の要。
            requests_per_minute (int): 1分あたりのAPIコール回数の上限。無料枠の場合、TPMも考慮して余裕を持った値に設定する。
                                       Gemini Embeddingの無料枠RPMは100, TPMは30,000。
        """
        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("環境変数 `GEMINI_API_KEY` が設定されていません。")
        
        print(f"Embeddingモデル ({model_name}) を初期化中...")
        self.client = genai.Client()
        self.model_name = model_name
        self.batch_size = batch_size
        self.sleep_duration = 60.0 / requests_per_minute
        print(f"Embeddingモデルの初期化完了。バッチサイズ: {self.batch_size}, APIコール間の待機時間: {self.sleep_duration:.2f}秒")

    @backoff.on_exception(
        backoff.expo,
        genai.errors.ClientError,
        max_tries=5,
        max_time=120
    )

    def _embed_content_with_retry(self, batch_texts: list[str]):
        """
        APIコールをリトライロジックでラップした内部メソッド。
        ResourceExhaustedエラーが発生した場合、自動的にエクスポネンシャルバックオフで再試行する。
        """
        return self.client.models.embed_content(
            model=self.model_name,
            contents=batch_texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        複数のドキュメント（チャンク）を一度にベクトル化するメソッド。
        データベース構築時に使用します。レート制限を考慮してバッチ処理を行います。
        """
        all_embeddings = []
        
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Embedding Batches"):
            batch_texts = texts[i:i + self.batch_size]
            
            try:
                # 直接APIを呼ぶ代わりに、リトライ機能付きメソッドを呼ぶ
                result = self._embed_content_with_retry(batch_texts)
                # result = self.client.models.embed_content(
                #     model=self.model_name,
                #     contents=batch_texts,
                #     config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
                # )
                batch_embeddings = [list(e.values) for e in result.embeddings]
                all_embeddings.extend(batch_embeddings)
            except genai.errors.ClientError as e:
                print(f"genai.errors.ClientError側の捕捉した例外の型: {type(e)}")
                print(f"エラー: バッチ {i//self.batch_size + 1} は最大リトライ回数を超えても失敗しました。スキップします。: {e}")
                all_embeddings.extend([None] * len(batch_texts))
            except Exception as e:
                # その他の予期せぬエラー
                print(f"Exception側の捕捉した例外の型: {type(e)}")
                print(f"エラー: バッチ {i//self.batch_size + 1} で予期せぬエラーが発生しました。: {e}")
                all_embeddings.extend([None] * len(batch_texts))

            time.sleep(self.sleep_duration)
            
        valid_embeddings = [emb for emb in all_embeddings if emb is not None]
        
        # 最終的に有効なエンベディングが1つも無かった場合に、明確なエラーを出す
        if not valid_embeddings:
            raise RuntimeError("全てのチャンクのエンベディングに失敗しました。APIのレート制限（特にTPM）を確認してください。")

        if len(valid_embeddings) != len(texts):
            print(f"警告: {len(texts) - len(valid_embeddings)}個のチャンクのエンベディングに失敗しました。")
            
        return valid_embeddings

    def embed_query(self, text: str) -> list[float]:
        """
        単一のクエリテキストをベクトル化するメソッド。
        ユーザーからの質問を検索する際に使用します。
        """
        result = self.client.models.embed_content(
            model=self.model_name,
            contents=[text],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        return list(result.embeddings[0].values)