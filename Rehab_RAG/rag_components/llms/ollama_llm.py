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
    def __init__(self, model_name: str):
        """
        コンストラクタ。

        Args:
            model_name (str): 使用するOllamaモデル名 (例: "qwen3:8b")
        """
        self.model_name = model_name
        print(f"Ollama LLMラッパー初期化完了 (モデル: {self.model_name})")
        logger.info(f"Ollama LLM Wrapper initialized (Model: {self.model_name})") # ログ追加

    def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_output_tokens: Optional[int] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ):
        """
        与えられたプロンプトを元に、Ollamaから応答を生成します。
        スキーマが指定されていればJSONモードで実行します。
        """
        options = {"temperature": temperature}
        if max_output_tokens:
            options["num_predict"] = max_output_tokens # Ollamaでは num_predict

        logger.info(f"--- Calling Ollama API (Model: {self.model_name}) ---") # ログ追加
        if response_schema:
            logger.info(f"Generating with JSON schema: {response_schema.__name__}") # ログ追加
        # logger.debug(f"Prompt:\n{prompt[:500]}...") # 必要ならプロンプトもログに（長すぎる場合は注意）

        try:
            # スキーマが指定されている場合はJSONモードで実行
            if response_schema:
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{'role': 'user', 'content': prompt}],
                    format='json',
                    options=options,
                    stream=False
                )
                raw_content = response['message']['content']
                logger.info(f"Ollama Raw JSON Response:\n{raw_content}") # ログ追加

                # JSONパースとPydantic検証
                try:
                    parsed_json = json.loads(raw_content)
                    data_to_validate = parsed_json

                    # ネストされた応答の可能性を考慮
                    if isinstance(parsed_json, dict):
                        potential_keys = ['properties', 'attributes', 'data']
                        extracted = False # ★ 追加: ネスト抽出フラグ ★
                        for key in potential_keys:
                           if key in parsed_json and isinstance(parsed_json[key], dict):
                               data_to_validate = parsed_json[key]
                               logger.info(f"Extracted data from nested key: '{key}'") # ログ追加
                               extracted = True # ★ 追加 ★
                               break
                        # ★ 修正: elif のインデントを if と同じレベルに ★
                        # ★ 修正: ネストキーが見つからなかった場合にのみ実行されるように extracted フラグをチェック ★
                        if not extracted:
                           if response_schema.__name__.lower() in parsed_json and isinstance(parsed_json[response_schema.__name__.lower()], dict):
                               data_to_validate = parsed_json[response_schema.__name__.lower()]
                               logger.info(f"Extracted data from nested schema name key: '{response_schema.__name__.lower()}'") # ログ追加
                           elif 'description' in parsed_json: # descriptionを除外
                               data_to_validate = {k: v for k, v in parsed_json.items() if k != 'description'}
                               logger.info("Removed 'description' key before validation.") # ログ追加
                           # ★ 修正: 上記のどの条件にも当てはまらない場合は、そのまま parsed_json を使う (else は不要) ★

                    validated_data = response_schema.model_validate(data_to_validate)
                    logger.info("Ollama JSON response validated successfully.") # ログ追加
                    return validated_data # Pydanticオブジェクトを返す (rag_executor.py側で .model_dump() する想定)
                except json.JSONDecodeError as json_err:
                    error_msg = f"OllamaからのJSON応答のパースに失敗しました: {json_err}. Raw content: {raw_content}"
                    logger.error(error_msg) # ログ追加
                    return {"error": error_msg}
                except ValidationError as val_err:
                    error_msg = f"Ollama応答のスキーマ検証に失敗しました: {val_err}. Data tried: {json.dumps(data_to_validate, ensure_ascii=False, indent=2)}" # 検証対象もログに
                    logger.error(error_msg) # ログ追加
                    return {"error": error_msg}
                except Exception as e:
                    error_msg = f"JSON処理中に予期せぬエラー: {e}. Raw content: {raw_content}"
                    logger.error(error_msg, exc_info=True) # トレースバックも記録
                    return {"error": error_msg}

            # スキーマ指定がない場合は通常のテキスト生成
            else:
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{'role': 'user', 'content': prompt}],
                    format='',
                    options=options,
                    stream=False
                )
                generated_text = response['message']['content']
                logger.info("Ollama Text Response generated successfully.") # ログ追加
                # logger.debug(f"Generated Text:\n{generated_text[:500]}...") # 必要なら生成テキストもログに
                return generated_text

        except Exception as e:
            error_message = f"Ollama API呼び出し中にエラーが発生しました: {e}"
            logger.error(error_message, exc_info=True) # トレースバックも記録
            if response_schema:
                return {"error": error_message}
            return error_message # テキストモードではエラーメッセージ文字列を返す