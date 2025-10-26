import os
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 構造的出力
from typing import Optional, Type
from pydantic import BaseModel


class GeminiLLM:
    """
    [手法解説: Generation (LLM)]
    大規模言語モデル(LLM)とのやり取りを管理するラッパーコンポーネント。
    このプロジェクトではGoogleのGeminiモデルを使用します。

    役割:
    - (HyDEで) 架空の回答を生成する。
    - (最終段階で) 検索された情報を元に、ユーザーへの最終的な回答を生成する。

    APIキーの管理、エラー時のリトライ、セーフティ設定など、LLMとの安定した通信に
    必要な機能を集約しています。
    """

    def __init__(self, model_name: str, safety_block_none: bool = True):
        """
        コンストラクタ。APIキーを読み込み、クライアントを初期化します。

        Args:
            model_name (str): 使用するGeminiモデル名 (例: "gemini-2.5-flash-lite")
            safety_block_none (bool): Trueの場合、Geminiの安全フィルタを無効化します。
                                     医療情報など、専門的な内容を扱う際に意図しないブロックを避けるため。
        """
        load_dotenv(
            dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        )
        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError(
                "環境変数 'GEMINI_API_KEY' が .env ファイルに設定されていません。"
            )

        self.client = genai.Client()
        self.model_name = model_name

        # [エラー回避/安定化のポイント]
        # 医療系の質問は、モデルのセーフティ機能によって回答がブロックされることがあります。
        # このRAGでは、信頼できる情報源のみを参考にしているため、モデル自体の安全フィルタは
        # 無効化(BLOCK_NONE)し、意図した回答が生成されるようにします。
        if safety_block_none:
            self.safety_settings = [
                types.SafetySetting(
                    category=c, threshold=types.HarmBlockThreshold.BLOCK_NONE
                )
                for c in [
                    types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                ]
            ]
        else:
            self.safety_settings = []

        print(f"LLMラッパー初期化完了 (モデル: {self.model_name})")

    def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_output_tokens: int = 4096,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> str:
        """
        与えられたプロンプトを元に、LLMからテキスト応答を生成します。
        APIの一時的なエラーに備えて、簡単なリトライロジックを実装しています。
        """
        # [エラー回避/安定化のポイント]
        # API呼び出しは、ネットワークの問題やサーバー側の負荷で一時的に失敗することがあります(500 Internal Errorなど)。
        # そのため、簡単なリトライ処理を実装することで、システムの安定性を向上させています。

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            safety_settings=self.safety_settings,
        )

        # スキーマが指定されていれば、JSON出力モードに設定
        if response_schema:
            config.response_mime_type = "application/json"
            config.response_schema = response_schema

        for attempt in range(2):  # 最大2回試行
            try:
                response = self.client.models.generate_content(
                    model=self.model_name, contents=prompt, config=config
                )

                # スキーマの有無で戻り値を分岐
                if response_schema:
                    # JSONモードの場合、パース済みのPydanticオブジェクトを返す
                    if hasattr(response, "parsed"):
                        return response.parsed
                    else:
                        # まれにパースに失敗した場合のエラーハンドリング
                        raise ValueError(
                            f"JSONスキーマのパースに失敗しました。Response: {response.text}"
                        )

                elif response.text:
                    return response.text
                else:
                    # レスポンスが空の場合、ブロックされたかトークン上限に達した可能性がある
                    finish_reason_name = response.candidates[0].finish_reason.name
                    if finish_reason_name == "MAX_TOKENS":
                        return f"回答を生成できませんでした。理由: {finish_reason_name} (出力トークン上限超過)"

            except Exception as e:
                print(f"回答生成中にエラー発生 (試行 {attempt + 1} 回目): {e}")
                if attempt == 0:
                    time.sleep(3)
                else:
                    error_message = f"回答の生成中にエラーが繰り返し発生しました: {e}"
                    # JSONモードでのエラーの場合は辞書で、テキストモードでは文字列で返す
                    if response_schema:
                        return {"error": error_message}
                    return error_message

        # リトライしても成功しなかった場合の最終的な戻り値
        error_message = "回答を生成できませんでした。APIリトライの上限に達しました。"
        if response_schema:
            return {"error": error_message}
        return error_message
