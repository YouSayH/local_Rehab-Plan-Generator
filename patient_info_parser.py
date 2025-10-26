import os
import json
import time
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from schemas import PATIENT_INFO_EXTRACTION_GROUPS # 分割したスキーマのリストをインポート
import logging

load_dotenv()

# ログ設定 (gemini_client.pyと同じファイルに出力)
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
log_file_path = os.path.join(log_directory, "gemini_prompts.log")

# ロガーの設定 (ファイル出力のみ、フォーマット指定)
# すでにgemini_client.pyで設定されている場合は不要だが、念のため追加
logger = logging.getLogger(__name__) # 新しいロガーインスタンスを取得
if not logger.hasHandlers(): # ハンドラが未設定の場合のみ設定
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

class PatientInfoParser:
    """
    Gemini APIを使用して、非構造化テキストから構造化された患者情報を抽出するクラス。
    スキーマが大きすぎることによるAPIエラーを回避するため、情報を複数のグループに分けて段階的に抽出する。
    """
    def __init__(self, api_key: str = None):
        # gemini_client.py と同様に、環境変数から自動でキーを読み込む方式に変更
        if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
            raise ValueError("APIキーが設定されていません。環境変数 'GOOGLE_API_KEY' または 'GEMINI_API_KEY' を設定してください。")
        
        self.client = genai.Client()
        # 構造化出力をサポートするモデルを選択
        self.model_name = 'gemini-2.5-flash-lite'

    def _build_prompt(self, text: str, group_schema: type[BaseModel], extracted_data_so_far: dict) -> str:
        """段階的抽出のためのプロンプトを構築する"""
        
        # これまでに抽出されたデータを簡潔なサマリーにする
        summary = json.dumps(extracted_data_so_far, indent=2, ensure_ascii=False) if extracted_data_so_far else "まだありません。"

        # 今回の抽出対象スキーマをJSON形式の文字列としてプロンプトに含める
        schema_json = json.dumps(group_schema.model_json_schema(), indent=2, ensure_ascii=False)

        return f"""あなたは医療情報抽出の専門家です。以下の「カルテテキスト」から患者の最新の状態を抽出し、後述する「JSONスキーマ」に従って構造化データを作成してください。

# 指示事項
- テキスト内には、異なる日付の情報が混在している可能性があります。**必ず最も新しい日付の情報や、文脈上最新と思われる情報（例：「現在」「本日」）を優先して抽出してください。**
- 古い情報（例：「初回評価時」「〇月〇日時点では」）は、新しい情報で上書きしてください。
- 例えば、「7/1に疼痛NRS 5/10だったが、7/10にはNRS 3/10に軽減」という記述があれば、疼痛は「NRS 3/10」としてください。
- **最重要**: 今回のタスクでは、以下の「JSONスキーマ」で定義されている項目のみを抽出対象とします。
- **ADLスコアの時系列解釈**: テキスト内に複数の日付のADLスコア（FIMやBI）がある場合、**最も新しいスコアを `_current_val`** に、**その直前のスコア（2番目に新しいスコア）を `_start_val`** に設定してください。スコアが1つしか記録されていない場合は、`_current_val` と `_start_val` の両方に同じ値を設定してください。
- **ADLの記述をFIMスコアに変換してください。** 具体的には、「自立」は7点、「監視・準備」は6点、「最小介助」は5点、「中等度介助」は3点、「全介助」は1点として解釈し、対応する`_fim_current_val`項目に数値を設定してください。
- **基本動作・活動目標のレベル解釈**: テキスト内の記述（例：「寝返りは自立」）を解釈し、対応するラジオボタン用のフィールド（例：`func_basic_rolling_level`）に適切な選択肢の文字列（例：`'independent'`）を設定してください。同時に、関連するチェックボックス（例：`func_basic_rolling_chk` と `func_basic_rolling_independent_chk`）も `true` に設定してください。「一部介助」や「軽介助」は `'partial_assist'` と解釈してください。
- テキストから情報が読み取れない項目は、無理に推測せず、`null`値としてください。
- **`True`の値の保持**: 「これまでに抽出された情報」で既に `True` になっているチェックボックス項目は、カルテテキストから反証（例：「意識障害なし」という明確な記述）が見つからない限り、`True` のまま保持してください。`null` で上書きしないでください。
- **障害者手帳の情報を解釈してください。** 例えば、「右上肢機能障害3級」という記述があれば、`social_disability_certificate_physical_chk`を`true`に、`social_disability_certificate_physical_type_txt`に「上肢」と設定し、`social_disability_certificate_physical_rank_val`に`3`を設定してください。`social_disability_certificate_physical_type_txt`に設定する値は、['視覚', '聴覚', '平衡機能', '言語機能', '音声機能', '咀嚼機能', '上肢', '下肢', '体幹', '心臓機能', '腎臓機能', '呼吸器機能', 'ぼうこう又は直腸機能', '小腸機能', 'ヒト免疫不全ウイルスによる免疫機能', '肝臓機能']の中から最も適切なものを選択してください。
- **嚥下調整食の必要性**: 「嚥下調整食の必要性あり」という記述があれば `nutrition_swallowing_diet_slct` を `'True'` に、「必要性なし」なら `'None'` に設定してください。 `学会分類コード` の情報があれば `nutrition_swallowing_diet_code_txt` に設定してください。
- **栄養状態の評価**: テキスト内の「栄養状態は低栄養リスク」などの記述を解釈し、`nutrition_status_assessment_slct` フィールドに `['no_problem', 'malnutrition', 'malnutrition_risk', 'overnutrition', 'other']` の中から最も適切な値を設定してください。
- **栄養補給方法の親子関係**: 「経口摂取」や「食事」という記述があれば、`nutrition_method_oral_chk`と`nutrition_method_oral_meal_chk`の両方を`true`にしてください。「経管栄養」や「経鼻栄養」という記述があれば`nutrition_method_tube_chk`を`true`にしてください。
- **不整脈の有無**: `func_circulatory_arrhythmia_status_slct` には、不整脈の有無を `'yes'` または `'no'` で設定してください。

## これまでに抽出された情報（今回の抽出の参考にしてください）
```json
{summary}
```

## カルテテキスト (全文)
---
{text}
---
"""

    def parse_text(self, text: str) -> dict:
        """
        与えられたテキストを解析し、複数のスキーマグループに基づいて段階的に情報を抽出し、結果をマージして返す。

        Args:
            text: 解析対象のカルテなどのテキスト。

        Returns:
            抽出された患者情報の辞書。エラー時はエラー情報を格納した辞書を返す。
        """
        final_result = {}
        
        for group_schema in PATIENT_INFO_EXTRACTION_GROUPS:
            print(f"--- Processing group: {group_schema.__name__} ---")
            prompt = self._build_prompt(text, group_schema, final_result)

            logger.info(f"--- Parsing Group: {group_schema.__name__} ---") # loggerを使用
            logger.info("Parsing Prompt:\n" + prompt) # loggerを使用

            try:
                generation_config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=group_schema,
                )

                # リトライ処理を追加
                max_retries = 3
                backoff_factor = 2  # 初回待機時間（秒）
                response = None

                for attempt in range(max_retries):
                    try:
                        response = self.client.models.generate_content(model=self.model_name, contents=prompt, config=generation_config)
                        break  # 成功した場合はループを抜ける
                    except (ResourceExhausted, ServiceUnavailable) as e:
                        if attempt < max_retries - 1:
                            wait_time = backoff_factor * (2 ** attempt)
                            print(f"   [警告] APIレート制限またはサーバーエラー。{wait_time}秒後に再試行します... ({attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                        else:
                            print(f"   [エラー] API呼び出しが{max_retries}回失敗しました。")
                            raise e # 最終的に失敗した場合はエラーを再送出
                # リトライ処理ここまで
                
                if response and response.parsed:
                    group_result = response.parsed.model_dump(mode='json')
                    
                    # データ正規化処理を追加
                    if 'gender' in group_result and group_result['gender']:
                        if '男性' in group_result['gender']:
                            group_result['gender'] = '男'
                        elif '女性' in group_result['gender']:
                            group_result['gender'] = '女'
                    # データ正規化処理ここまで

                    final_result.update(group_result) # マージして次のステップへ
                else:
                    print(f"   [警告] グループ {group_schema.__name__} の解析で有効な結果が得られませんでした。")

            except Exception as e:
                print(f"グループ {group_schema.__name__} の解析中にエラーが発生しました: {e}")
                # 一つのグループで失敗しても処理を続行する
                continue
            
            # APIのレート制限を避けるため、各グループの処理の間に短い待機時間を設ける
            time.sleep(5)

        if not final_result:
            return {"error": "患者情報の解析に失敗しました。", "details": "どのグループからも有効な情報を抽出できませんでした。"}

        return final_result