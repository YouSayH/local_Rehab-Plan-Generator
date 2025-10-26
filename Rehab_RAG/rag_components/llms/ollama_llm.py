# Rehab_RAG/rag_components/llms/ollama_llm.py
import ollama
import json
from pydantic import BaseModel, ValidationError
from typing import Optional, Type
import logging # ログ出力用に追加

# ロガーの設定 (gemini_llm.pyと同様)
logger = logging.getLogger(__name__)

class OllamaLLM:
    """
    Ollamaを使用してテキスト生成を行うラッパークラス。
    構造化出力（JSON）にも対応。
    """
    def __init__(self, model_name: str = "qwen3:8b", temperature: float = 0.1, top_p: float = 0.9):
        """
        コンストラクタ。

        Args:
            model_name (str): 使用するOllamaモデル名 (例: "qwen3:8b")
        """
        self.model_name = model_name
        print(f"Ollama LLMラッパー初期化完了 (モデル: {self.model_name})")
        self.options = {
            "temperature": 0.6, # 決定性を高めるために 0.0 にする
            "top_p": top_p       # top_p も低め (0.5など) にしても良いかも
        }
        logger.info(f"Ollama LLM Wrapper initialized (Model: {self.model_name})") # ログ追加

    def generate(self, prompt: str, response_schema: Optional[Type[BaseModel]] = None, **kwargs):
        """
        与えられたプロンプトを元に、Ollamaから応答を生成します。
        スキーマが指定されていればJSONモードで実行します。
        """

        logger.info(f"--- Calling Ollama API (Model: {self.model_name}) ---") # ログ追加
        format_param = '' # デフォルトはテキスト
        if response_schema:
            logger.info(f"Generating with JSON schema enforcement: {response_schema.__name__}")
            try:
                # PydanticモデルからJSONスキーマ辞書を取得
                schema_dict = response_schema.model_json_schema() 
                format_param = schema_dict # スキーマ辞書を format に渡す
            except Exception as e:
                logger.error(f"Pydanticモデル ({response_schema.__name__}) からJSONスキーマの取得に失敗: {e}")
                return {"error": f"内部エラー: スキーマ定義の取得に失敗しました ({response_schema.__name__})。"}
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': 'あなたは常に日本語で応答するアシスタントです。'},
                    {'role': 'user', 'content': prompt}
                    ],
                format=format_param,
                options=self.options
            )
            generated_content = response.get('message', {}).get('content', '')
            if not generated_content:
                 # レスポンスが空の場合のエラーハンドリング
                 logger.error("Ollamaからの応答が空です。")
                 return {"error": "AIからの応答が空でした。モデルまたはプロンプトを確認してください。"}

            # レスポンスがスキーマ付きで要求された場合のみJSONとして処理
            if response_schema and isinstance(format_param, dict):
                logger.info("Ollama Raw JSON Response (before validation):\n" + generated_content)
                try:
                    # JSON文字列をパースする必要は *ない* かもしれない (ollamaライブラリが自動でやるか確認)
                    # → ドキュメントによると .message.content は文字列なのでパースは必要
                    json_data = json.loads(generated_content) 
                    
                    # Pydanticモデルでバリデーション
                    validated_data = response_schema.model_validate(json_data)
                    logger.info(f"Ollama JSON Response validated successfully against {response_schema.__name__}.")
                    return validated_data # 検証済みPydanticオブジェクトを返す
                except ValidationError as e:
                    error_msg = f"Ollama応答のスキーマ検証に失敗しました: {e}"
                    logger.error(error_msg + f". Data tried: {generated_content[:500]}...")
                    return {"error": f"AIの応答形式が指定されたスキーマ ({response_schema.__name__}) と一致しません。詳細: {e.errors()}"}
                except json.JSONDecodeError as e:
                    error_msg = f"Ollama応答のJSONパースに失敗しました (スキーマ強制モード): {e}"
                    logger.error(error_msg + f". Data received: {generated_content[:500]}...")
                    return {"error": f"AIの応答がJSON形式ではありませんでした (スキーマ強制モード)。受信データ: {generated_content[:100]}..."}
            elif format_param == 'json': # スキーマなし、'json'フォーマットのみ要求した場合 (現状の単体生成と同じ)
                logger.info("Ollama Raw JSON Response (no schema enforcement):\n" + generated_content)
                try:
                    # JSONとしてパースだけ試みる (検証はしない)
                    json_data = json.loads(generated_content)
                    return json_data # パースした辞書を返す
                except json.JSONDecodeError as e:
                     error_msg = f"Ollama応答のJSONパースに失敗しました (jsonモード): {e}"
                     logger.error(error_msg + f". Data received: {generated_content[:500]}...")
                     return {"error": f"AIの応答がJSON形式ではありませんでした (jsonモード)。受信データ: {generated_content[:100]}..."}
            else: # テキスト応答の場合
                logger.info("Ollama Text Response generated successfully.")
                return generated_content

        except Exception as e:
            logger.error(f"Ollama API呼び出し中にエラーが発生しました: {e}", exc_info=True)
            return {"error": f"Ollama APIとの通信中にエラーが発生しました: {e}"}