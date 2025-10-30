import os
import json
import time
import textwrap
from datetime import date
import pprint
from typing import Optional
import ollama
from pydantic import BaseModel, Field, create_model, ValidationError
from dotenv import load_dotenv

import logging

from schemas import (
    RehabPlanSchema,
    RisksAndPrecautions,
    FunctionalLimitations,
    Goals,
    TreatmentPolicy,
    ActionPlans,
    CurrentAssessment,
    ComprehensiveTreatmentPlan,
    GENERATION_GROUPS,
)

# 初期設定
load_dotenv()

log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
log_file_path = os.path.join(log_directory, "gemini_prompts.log")

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_file_path,
    filemode="a",
    encoding="utf-8",
)

# プロトタイプ開発用の設定
USE_DUMMY_DATA = False


# Pydanticを使用して、AIに生成してほしいJSONの構造を定義します。
# Field(description=...) を使用して、各項目が何を意味するのかをAIに明確に伝えます。


# ヘルパー関数


def _format_value(value):
    """値を人間が読みやすい形に整形する"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "あり" if value else "なし"
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


# DBカラム名と日本語名のマッピング
CELL_NAME_MAPPING = {
    # ヘッダー・基本情報
    "header_disease_name_txt": "算定病名",
    "header_treatment_details_txt": "治療内容",
    "header_onset_date": "発症日・手術日",
    "header_rehab_start_date": "リハ開始日",
    "main_comorbidities_txt": "併存疾患・合併症",
    "header_therapy_pt_chk": "理学療法",
    "header_therapy_ot_chk": "作業療法",
    "header_therapy_st_chk": "言語聴覚療法",
    # 心身機能・構造 (全般)
    "func_consciousness_disorder_chk": "意識障害",
    "func_consciousness_disorder_jcs_gcs_txt": "意識障害(JCS/GCS)",
    "func_respiratory_disorder_chk": "呼吸機能障害",
    "func_respiratory_o2_therapy_chk": "酸素療法",
    "func_respiratory_tracheostomy_chk": "気管切開",
    "func_respiratory_ventilator_chk": "人工呼吸器",
    "func_circulatory_disorder_chk": "循環障害",
    "func_circulatory_ef_chk": "心駆出率(EF)測定",
    "func_circulatory_arrhythmia_chk": "不整脈",
    "func_risk_factors_chk": "危険因子",
    "func_risk_hypertension_chk": "高血圧症",
    "func_risk_dyslipidemia_chk": "脂質異常症",
    "func_risk_diabetes_chk": "糖尿病",
    "func_risk_smoking_chk": "喫煙",
    "func_risk_obesity_chk": "肥満",
    "func_risk_hyperuricemia_chk": "高尿酸血症",
    "func_risk_ckd_chk": "慢性腎臓病(CKD)",
    "func_risk_family_history_chk": "家族歴",
    "func_risk_angina_chk": "狭心症",
    "func_risk_omi_chk": "陳旧性心筋梗塞",
    "func_swallowing_disorder_chk": "摂食嚥下障害",
    "func_swallowing_disorder_txt": "摂食嚥下障害(詳細)",
    "func_nutritional_disorder_chk": "栄養障害",
    "func_nutritional_disorder_txt": "栄養障害(詳細)",
    "func_excretory_disorder_chk": "排泄機能障害",
    "func_excretory_disorder_txt": "排泄機能障害(詳細)",
    "func_pressure_ulcer_chk": "褥瘡",
    "func_pressure_ulcer_txt": "褥瘡(詳細)",
    "func_pain_chk": "疼痛",
    "func_pain_txt": "疼痛(詳細)",
    "func_rom_limitation_chk": "関節可動域制限",
    "func_rom_limitation_txt": "関節可動域制限(詳細)",
    "func_contracture_deformity_chk": "拘縮・変形",
    "func_contracture_deformity_txt": "拘縮・変形(詳細)",
    "func_muscle_weakness_chk": "筋力低下",
    "func_muscle_weakness_txt": "筋力低下(詳細)",
    # 心身機能・構造 (運動・感覚)
    "func_motor_dysfunction_chk": "運動機能障害",
    "func_motor_paralysis_chk": "麻痺",
    "func_motor_involuntary_movement_chk": "不随意運動",
    "func_motor_ataxia_chk": "運動失調",
    "func_motor_parkinsonism_chk": "パーキンソニズム",
    "func_motor_muscle_tone_abnormality_chk": "筋緊張異常",
    "func_sensory_dysfunction_chk": "感覚機能障害",
    "func_sensory_hearing_chk": "聴覚障害",
    "func_sensory_vision_chk": "視覚障害",
    "func_sensory_superficial_chk": "表在感覚障害",
    "func_sensory_deep_chk": "深部感覚障害",
    # 心身機能・構造 (言語・高次脳)
    "func_speech_disorder_chk": "音声発話障害",
    "func_speech_articulation_chk": "構音障害",
    "func_speech_aphasia_chk": "失語症",
    "func_speech_stuttering_chk": "吃音",
    "func_higher_brain_dysfunction_chk": "高次脳機能障害",
    "func_higher_brain_memory_chk": "記憶障害(高次脳)",
    "func_higher_brain_attention_chk": "注意障害",
    "func_higher_brain_apraxia_chk": "失行",
    "func_higher_brain_agnosia_chk": "失認",
    "func_higher_brain_executive_chk": "遂行機能障害",
    "func_behavioral_psychiatric_disorder_chk": "精神行動障害",
    "func_behavioral_psychiatric_disorder_txt": "精神行動障害(詳細)",
    "func_disorientation_chk": "見当識障害",
    "func_disorientation_txt": "見当識障害(詳細)",
    "func_memory_disorder_chk": "記憶障害",
    "func_memory_disorder_txt": "記憶障害(詳細)",
    "func_developmental_disorder_chk": "発達障害",
    "func_developmental_asd_chk": "自閉症スペクトラム症(ASD)",
    "func_developmental_ld_chk": "学習障害(LD)",
    "func_developmental_adhd_chk": "注意欠陥多動性障害(ADHD)",
    # 基本動作
    "func_basic_rolling_chk": "寝返り",
    "func_basic_getting_up_chk": "起き上がり",
    "func_basic_standing_up_chk": "立ち上がり",
    "func_basic_sitting_balance_chk": "座位保持",
    "func_basic_standing_balance_chk": "立位保持",
    # 栄養
    "nutrition_height_val": "身長(cm)",
    "nutrition_weight_val": "体重(kg)",
    "nutrition_bmi_val": "BMI",
    "nutrition_method_oral_chk": "栄養補給(経口)",
    "nutrition_method_tube_chk": "栄養補給(経管)",
    "nutrition_method_iv_chk": "栄養補給(静脈)",
    "nutrition_method_peg_chk": "栄養補給(胃ろう)",
    "nutrition_swallowing_diet_True_chk": "嚥下調整食の必要性",
    "nutrition_swallowing_diet_code_txt": "嚥下調整食コード",
    "nutrition_status_assessment_malnutrition_chk": "栄養状態(低栄養)",
    "nutrition_status_assessment_malnutrition_risk_chk": "栄養状態(低栄養リスク)",
    "nutrition_status_assessment_overnutrition_chk": "栄養状態(過栄養)",
    "nutrition_required_energy_val": "必要熱量(kcal)",
    "nutrition_required_protein_val": "必要タンパク質量(g)",
    "nutrition_total_intake_energy_val": "総摂取熱量(kcal)",
    "nutrition_total_intake_protein_val": "総摂取タンパク質量(g)",
    # 社会保障サービス
    "social_care_level_status_chk": "介護保険",
    "social_care_level_applying_chk": "介護保険(申請中)",
    "social_care_level_support_chk": "要支援",
    "social_care_level_care_slct": "要介護",
    "social_disability_certificate_physical_chk": "身体障害者手帳",
    "social_disability_certificate_mental_chk": "精神障害者保健福祉手帳",
    "social_disability_certificate_intellectual_chk": "療育手帳",
    # 参加 (事実情報)
    "goal_p_residence_chk": "住居場所",
    "goal_p_return_to_work_chk": "復職",
    "goal_p_schooling_chk": "就学",
    "goal_p_household_role_txt": "家庭内役割(現状・希望)",
    "goal_p_social_activity_txt": "社会活動(現状・希望)",
    "goal_p_hobby_txt": "趣味",
    # 活動 (事実情報)
    "goal_a_bed_mobility_chk": "床上移動",
    "goal_a_indoor_mobility_chk": "屋内移動",
    "goal_a_outdoor_mobility_chk": "屋外移動",
    "goal_a_driving_chk": "自動車運転",
    "goal_a_public_transport_chk": "公共交通機関利用",
    "goal_a_toileting_chk": "排泄(移乗以外)",
    "goal_a_eating_chk": "食事",
    "goal_a_grooming_chk": "整容",
    "goal_a_dressing_chk": "更衣",
    "goal_a_bathing_chk": "入浴",
    "goal_a_housework_meal_chk": "家事",
    "goal_a_writing_chk": "書字",
    "goal_a_ict_chk": "ICT機器利用",
    "goal_a_communication_chk": "コミュニケーション",
}

def _prepare_patient_facts(patient_data: dict) -> dict:
    """プロンプトに渡すための患者の事実情報を整形する"""
    print(
        f"DEBUG [gemini_client.py]: therapist_notes received = '{str(patient_data.get('therapist_notes'))[:100]}...'"
    )
    therapist_notes = patient_data.get("therapist_notes", "").strip()

    facts = {
        "基本情報": {},
        "心身機能・構造": {},
        "基本動作": {},
        "ADL評価": {"FIM(現在値)": {}, "BI(現在値)": {}},
        "栄養状態": {},
        "社会保障サービス": {},
        "生活状況・目標(本人・家族)": {},
        "担当者からの所見": therapist_notes if therapist_notes else "特になし",
    }
    print(
        f"DEBUG [gemini_client.py]: '担当者からの所見' in facts dict = {facts.get('担当者からの所見')}"
    )

    # 年齢を5歳刻み（前半/後半）で丸める匿名化処理
    age = patient_data.get("age")
    if age is not None:
        try:
            age_int = int(age)
            decade = (age_int // 10) * 10
            if age_int % 10 < 5:
                half = "前半"
            else:
                half = "後半"
            facts["基本情報"]["年齢"] = f"{decade}代{half}"
        except (ValueError, TypeError):
            facts["基本情報"]["年齢"] = "不明"  # 変換に失敗した場合
    else:
        facts["基本情報"]["年齢"] = "不明"  # 年齢が設定されていない場合

    facts["基本情報"]["性別"] = _format_value(patient_data.get("gender"))

    # 1. チェックボックスと関連しない項目を先に埋める
    for key, value in patient_data.items():
        formatted_value = _format_value(value)
        if formatted_value is None:
            continue

        # チェックボックスやそれに関連するテキストは、後の専用ロジックで処理するためスキップ
        if (
            "_chk" in key
            or "_txt" in key
            and key in [t[1] for t in CHECK_TO_TEXT_MAP.items()]
        ):
            continue

        jp_name = CELL_NAME_MAPPING.get(key)
        if not jp_name:
            continue

        category = None
        if key.startswith(("header_", "main_")):
            category = "基本情報"
        elif key.startswith("func_basic_"):
            category = "基本動作"
        elif key.startswith("nutrition_"):
            category = "栄養状態"
        elif key.startswith("social_"):
            category = "社会保障サービス"
        elif key.startswith("goal_p_"):
            category = "生活状況・目標(本人・家族)"
        elif key.startswith("func_"):
            category = "心身機能・構造"

        if category:
            facts[category][jp_name] = formatted_value

    # 2. チェックボックスの状態を最優先で、かつ正確に反映させる
    #    CHECK_TO_TEXT_MAPを基準にループすることで、処理を確実にする
    for chk_key, txt_key in CHECK_TO_TEXT_MAP.items():
        jp_name = CELL_NAME_MAPPING.get(chk_key)
        if not jp_name:
            continue

        is_checked_value = patient_data.get(chk_key)
        is_truly_checked = str(is_checked_value).lower() in ["true", "1", "on"]

        if not is_truly_checked:
            continue

        txt_value = patient_data.get(txt_key)
        # 記述が空の場合は、AIに推論を促す特別な指示を与える
        if not txt_value or txt_value.strip() == "特記なし":
            facts["心身機能・構造"][jp_name] = (
                "あり（患者の他のデータに基づき、具体的な症状やADLへの影響を推測して記述してください）"
            )
        else:
            facts["心身機能・構造"][jp_name] = txt_value

    # 3. ADL評価スコアを抽出
    for key, value in patient_data.items():
        val = _format_value(value)
        if val is not None and "_val" in key:
            if "fim_current_val" in key:
                item_name = (
                    key.replace("adl_", "")
                    .replace("_fim_current_val", "")
                    .replace("_", " ")
                    .title()
                )
                facts["ADL評価"]["FIM(現在値)"][item_name] = f"{val}点"
            elif "bi_current_val" in key:
                item_name = (
                    key.replace("adl_", "")
                    .replace("_bi_current_val", "")
                    .replace("_", " ")
                    .title()
                )
                facts["ADL評価"]["BI(現在値)"][item_name] = f"{val}点"

    # 空のカテゴリやサブカテゴリを最終的に削除
    facts = {k: v for k, v in facts.items() if v or k == "担当者からの所見"}
    if "ADL評価" in facts:
        facts["ADL評価"] = {k: v for k, v in facts["ADL評価"].items() if v}
        if not facts["ADL評価"]:
            del facts["ADL評価"]

    # "心身機能・構造" カテゴリ自体が空になった場合は、それも削除
    if "心身機能・構造" in facts and not facts["心身機能・構造"]:
        del facts["心身機能・構造"]

    return facts

CHECK_TO_TEXT_MAP = {
    "func_pain_chk": "func_pain_txt",
    "func_rom_limitation_chk": "func_rom_limitation_txt",
    "func_muscle_weakness_chk": "func_muscle_weakness_txt",
    "func_swallowing_disorder_chk": "func_swallowing_disorder_txt",
    "func_behavioral_psychiatric_disorder_chk": "func_behavioral_psychiatric_disorder_txt",
    "func_nutritional_disorder_chk": "func_nutritional_disorder_txt",
    "func_excretory_disorder_chk": "func_excretory_disorder_txt",
    "func_pressure_ulcer_chk": "func_pressure_ulcer_txt",
    "func_contracture_deformity_chk": "func_contracture_deformity_txt",
    "func_motor_muscle_tone_abnormality_chk": "func_motor_muscle_tone_abnormality_txt",
    "func_disorientation_chk": "func_disorientation_txt",
    "func_memory_disorder_chk": "func_memory_disorder_txt",
}


# ユーザーが既に入力した項目はAI生成をスキップする
USER_INPUT_FIELDS = ["main_comorbidities_txt"]

# --- Ollama用関数 (新規追加) ---
OLLAMA_MODEL_NAME = 'qwen3:8b'

def _build_ollama_group_prompt(group_schema: type[BaseModel], patient_facts_str: str, generated_plan_so_far: dict) -> str:
    """Ollama用のグループ生成プロンプトを構築する"""
    return textwrap.dedent(f"""
        # 役割
        あなたは、患者様とそのご家族にリハビリテーション計画を説明する、経験豊富で説明上手なリハビリテーション科の専門医です。
        専門用語を避け、誰にでも理解できる平易な言葉で、誠実かつ丁寧に説明する文章を使用して、患者の個別性を最大限に尊重し、一貫性のあるリハビリテーション総合実施計画書を作成してください。

        # 患者データ (事実情報)
        ```json
        {patient_facts_str}
        ```

        # これまでの生成結果 (参考にしてください)
        ```json
        {json.dumps(generated_plan_so_far, indent=2, ensure_ascii=False, default=str)}
        ```

        # 作成指示
        上記の「患者データ」と「これまでの生成結果」を統合的に解釈し、**以下のJSONスキーマで定義されている項目のみ**を日本語で生成してください。
        - **最重要**: 生成する文章は、患者様やそのご家族が直接読んでも理解できるよう、**専門用語を避け、できるだけ平易な言葉で記述してください**。
        - ただし、**病名や疾患名はそのまま使用してください**。
        - 患者データから判断して該当しない、または情報が不足している場合は、必ず「特記なし」とだけ記述してください。
        - スキーマの`description`をよく読み、具体的で分かりやすい内容を記述してください。
        - 各項目は、他の項目との関連性や一貫性を保つように記述してください。

        ```json
        {json.dumps(group_schema.model_json_schema(), indent=2, ensure_ascii=False)}
        ```
        ---
        生成するJSON ({group_schema.__name__} の項目のみ):
    """)

def generate_ollama_plan_stream(patient_data: dict):
    """
    Ollamaを使用して計画案をグループごとに段階的に生成し、ストリーミングで返す関数。
    """
    if USE_DUMMY_DATA:
        print("--- ダミーデータを使用しています ---")
        dummy_plan = get_dummy_plan()
        for key, value in dummy_plan.items():
            time.sleep(0.05)
            event_data = json.dumps({"key": key, "value": value, "model_type": "ollama_general"})
            yield f"event: update\ndata: {event_data}\n\n"
        yield "event: finished\ndata: {}\n\n"
        return

    try:
        patient_facts = _prepare_patient_facts(patient_data)
        patient_facts_str = json.dumps(patient_facts, indent=2, ensure_ascii=False, default=str)
        generated_plan_so_far = {}

        for group_schema in GENERATION_GROUPS:
            print(f"\n--- Ollama Generating Group: {group_schema.__name__} ---")
            prompt = _build_ollama_group_prompt(group_schema, patient_facts_str, generated_plan_so_far)
            logging.info(f"--- Ollama Generating Group: {group_schema.__name__} ---")
            logging.info("Prompt:\n" + prompt)

            stream = ollama.chat(
                model=OLLAMA_MODEL_NAME,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
                stream=True
            )

            accumulated_json_string = ""
            for chunk in stream:
                if chunk['message']['content']:
                    accumulated_json_string += chunk['message']['content']

            print(f"--- Ollama Response (Group: {group_schema.__name__}) ---")
            print(accumulated_json_string)
            try:
                # 1. まずJSONとしてパース
                raw_response_dict = json.loads(accumulated_json_string)

                # 2. ネストされた構造かチェックし、必要なら中身を取り出す ★★★修正点★★★
                data_to_validate = {} # 型ヒントを Dict に変更
                if isinstance(raw_response_dict, dict):
                    # よくあるネストキーのリスト (必要に応じて追加)
                    nested_keys = ['properties', 'attributes', 'data']
                    extracted = False
                    for key in nested_keys:
                        if key in raw_response_dict and isinstance(raw_response_dict[key], dict):
                            data_to_validate = raw_response_dict[key]
                            print(f"   [情報] ネストされたキー '{key}' からデータを取り出しました。")
                            extracted = True
                            break
                    # ネストキーが見つからなければ、トップレベルをそのまま使う
                    if not extracted:
                         # トップレベルに description キーがある場合も、その値が辞書なら取り出す
                        if 'description' in raw_response_dict and isinstance(raw_response_dict.get(group_schema.__name__.lower()), dict): # スキーマ名がキーの場合
                            data_to_validate = raw_response_dict.get(group_schema.__name__.lower(), raw_response_dict)
                        # それ以外はトップレベルの辞書を検証対象とする
                        else:
                            data_to_validate = {k: v for k, v in raw_response_dict.items() if k != 'description'} # descriptionを除外

                else:
                     # 予期せず辞書でない場合 (エラー処理)
                    raise ValueError("Ollamaの応答が予期しない形式です（辞書ではありません）。")


                # 3. 取り出したデータでPydantic検証 ★★★修正点★★★
                # group_result_obj = group_schema.model_validate_json(accumulated_json_string) # 元のコード
                group_result_obj = group_schema.model_validate(data_to_validate) # 辞書を直接渡す
                group_result_dict = group_result_obj.model_dump()

                generated_plan_so_far.update(group_result_dict)

                for key, value in group_result_dict.items():
                    if value is not None:
                        event_data = json.dumps({"key": key, "value": str(value), "model_type": "ollama_general"})
                        yield f"event: update\ndata: {event_data}\n\n"
                print(f"--- Group {group_schema.__name__} processed successfully ---")

            except ValidationError as val_err:
                print(f"グループ {group_schema.__name__} のスキーマ検証に失敗しました。")
                print(f"検証対象データ: {data_to_validate}") # ★★★デバッグ用★★★
                print(val_err)
                error_message = f"グループ {group_schema.__name__} の生成でスキーマエラー: {val_err}"
                error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
                yield error_event
            except json.JSONDecodeError as json_err:
                print(f"グループ {group_schema.__name__} のJSONパースに失敗しました: {json_err}")
                error_message = f"グループ {group_schema.__name__} の生成でJSON形式エラー: {json_err}"
                error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
                yield error_event
            except Exception as e:
                print(f"グループ {group_schema.__name__} の処理中に予期せぬエラー: {e}")
                error_message = f"グループ {group_schema.__name__} の生成中に予期せぬエラー: {e}"
                error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
                yield error_event

            time.sleep(1)

        print("\n--- Ollamaによる全グループの生成完了 ---")
        yield "event: finished\ndata: {}\n\n"

    except Exception as e:
        print(f"Ollamaの段階的生成処理中に予期せぬエラーが発生しました: {e}")
        error_message = f"Ollama処理全体でエラーが発生しました: {e}"
        error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
        yield error_event


# テスト用ダミーデータ
def get_dummy_plan():
    """開発用のダミーの計画書データを返す"""
    return {
        "main_comorbidities_txt": "高血圧症、2型糖尿病（ユーザー入力）",
        "main_risks_txt": "高血圧症があり、訓練中の血圧変動に注意。転倒リスクも高いため、移動・移乗時は必ず見守りを行う。",
        "main_contraindications_txt": "右肩関節の可動域制限に対し、無理な他動運動は避けること。疼痛を誘発しない範囲で実施する。",
        "func_pain_txt": "右肩関節において、挙上120度以上でシャープな痛み(NRS 7/10)を認める。更衣や整容動作時に特に注意が必要。",
        "func_rom_limitation_txt": "右肩関節の挙上・外旋制限により、更衣（特に上衣の袖通し）や、洗髪、整髪動作に支障をきたしている。",
        "func_muscle_weakness_txt": "右肩周囲筋の筋力低下(MMT4レベル)により、物品の保持や高所へのリーチ動作が困難となっている。",
        "func_swallowing_disorder_txt": "嚥下調整食コード2-1であり、食事は刻み食・とろみ付きで提供。誤嚥予防のため、一口量を少なくし、交互嚥下を促す必要がある。",
        "func_behavioral_psychiatric_disorder_txt": "注意障害があり、一つの課題に集中することが難しい。訓練は静かな環境で、短時間集中型で実施することが望ましい。",
        "adl_equipment_and_assistance_details_txt": "食事：自助具（リーチャー）の使用を検討。\n移乗：ベッドから車椅子への移乗は軽介助レベル。トイレ移乗は手すりがあれば見守りで可能。\n歩行：屋内はT字杖を使用し見守りレベル。屋外は車椅子を使用。",
        "goals_1_month_txt": "【ADL】トイレ動作が手すりを使用して見守りレベルで自立する。\n【機能】T字杖歩行にて病棟内を安定して20m連続歩行可能となる。",
        "goals_at_discharge_txt": "自宅の環境（手すり設置後）にて、日中の屋内ADLが見守り〜自立レベルとなる。家族の介助負担を軽減する。",
        "policy_treatment_txt": "残存機能の最大化とADL自立度向上を目的とし、特に移乗・歩行能力の再獲得に焦点を当てる。また、高次脳機能障害へのアプローチも並行して行い、安全な在宅生活への移行を支援する。",
        "policy_content_txt": "・関節可動域訓練：右肩関節の疼痛のない範囲での自動介助運動\n・筋力増強訓練：右上下肢の漸増抵抗運動\n・ADL訓練：食事、更衣、トイレ動作の実地訓練\n・歩行訓練：平行棒内歩行からT字杖歩行へ移行\n・高次脳機能訓練：卓上での注意・記憶課題",
        "goal_p_household_role_txt": "食事の配膳や、洗濯物をたたむなどの軽作業を担う。",
        "goal_p_hobby_txt": "好きな音楽を聴く、家族とテレビを観るなどの座位で楽しめる趣味活動を再開する。",
        "goal_a_action_plan_txt": "トイレ動作については、動作を口頭指示で分解し、一つ一つの動きを確認しながら反復練習を行う。歩行については、正しい歩行パターンを意識させながら、まずは短い距離から開始し、徐々に距離を延長する。",
        "goal_s_env_action_plan_txt": "退院前訪問指導を計画し、家屋内の手すり設置場所（トイレ、廊下、浴室）や段差解消について本人・家族と検討する。必要に応じて介護保険サービス（訪問リハビリ、デイケア）の導入をケアマネージャーと連携して進める。",
    }


# このファイルが直接実行された場合のテストコード
if __name__ == "__main__":
    print("--- Ollama クライアント 段階的生成テスト実行 ---")

    sample_patient_data = {
        "name": "テスト患者", "age": 75, "gender": "男性",
        "header_disease_name_txt": "脳梗塞右片麻痺",
        "therapist_notes": "テスト用所見",
        "func_pain_chk": True, "func_muscle_weakness_chk": True,
    }

    USE_DUMMY_DATA = False

    # Ollama用関数を呼び出すように変更
    stream_generator = generate_ollama_plan_stream(sample_patient_data)

    print("\n--- ストリームイベント ---")
    final_plan = {}
    error = None
    for event in stream_generator:
        print(event.strip())
        if "event: update" in event:
            try:
                data_str = event.split("data: ", 1)[1].strip()
                data = json.loads(data_str)
                final_plan[data["key"]] = data["value"]
            except Exception as e: print(f"Updateイベント解析エラー: {e}")
        elif "event: error" in event:
            try:
                data_str = event.split("data: ", 1)[1].strip()
                error = json.loads(data_str)
                print(f"!!! エラー受信: {error}")
            except Exception as e: print(f"Errorイベント解析エラー: {e}")

    if error:
        print("\n--- テスト実行中にエラーが検出されました ---")
        pprint.pprint(error)
    else:
        print("\n--- テスト完了 ---")
        print("最終生成結果:")
        pprint.pprint(final_plan)