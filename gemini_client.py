import os
import json
import time
import textwrap
from datetime import date
import pprint
# import google.generativeai as genai ←2025,9月までしかサポートなし
# https://ai.google.dev/gemini-api/docs/libraries?hl=ja  新ライブラリ
# https://ai.google.dev/gemini-api/docs/quickstart?hl=ja 使い方
from google import genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# RAG実行のコード(司令塔)をインポート
from rag_executor import RAGExecutor

# データをschemas.pyとして分離した。
# これはgemini_clientのまま使うとrag_executorとgemini_clientで循環参照が起こってしまうため
from schemas import (
    RehabPlanSchema,
    RisksAndPrecautions,
    FunctionalLimitations,
    Goals,
    TreatmentPolicy,
    ActionPlans,
    CurrentAssessment,
    ComprehensiveTreatmentPlan,
    GENERATION_GROUPS
)

# 初期設定
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("APIキーが.envファイルに設定されていません。'GOOGLE_API_KEY=...' を追加してください。")

# genai.configure(api_key=API_KEY)
# ↓↓新しい書き方
client = genai.Client()  # APIキーは環境変数 `GOOGLE_API_KEY` または `GEMINI_API_KEY` から自動で読み込まれる

# プロトタイプ開発用の設定
# Trueにすると、実際にAPIを呼び出さずにダミーデータを返します。
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
    "func_consciousness_disorder_chk": "意識障害", "func_consciousness_disorder_jcs_gcs_txt": "意識障害(JCS/GCS)",
    "func_respiratory_disorder_chk": "呼吸機能障害", "func_respiratory_o2_therapy_chk": "酸素療法", "func_respiratory_tracheostomy_chk": "気管切開", "func_respiratory_ventilator_chk": "人工呼吸器",
    "func_circulatory_disorder_chk": "循環障害", "func_circulatory_ef_chk": "心駆出率(EF)測定", "func_circulatory_arrhythmia_chk": "不整脈",
    "func_risk_factors_chk": "危険因子", "func_risk_hypertension_chk": "高血圧症", "func_risk_dyslipidemia_chk": "脂質異常症", "func_risk_diabetes_chk": "糖尿病", "func_risk_smoking_chk": "喫煙", "func_risk_obesity_chk": "肥満", "func_risk_hyperuricemia_chk": "高尿酸血症", "func_risk_ckd_chk": "慢性腎臓病(CKD)", "func_risk_family_history_chk": "家族歴", "func_risk_angina_chk": "狭心症", "func_risk_omi_chk": "陳旧性心筋梗塞",
    "func_swallowing_disorder_chk": "摂食嚥下障害", "func_swallowing_disorder_txt": "摂食嚥下障害(詳細)",
    "func_nutritional_disorder_chk": "栄養障害", "func_nutritional_disorder_txt": "栄養障害(詳細)",
    "func_excretory_disorder_chk": "排泄機能障害", "func_excretory_disorder_txt": "排泄機能障害(詳細)",
    "func_pressure_ulcer_chk": "褥瘡", "func_pressure_ulcer_txt": "褥瘡(詳細)",
    "func_pain_chk": "疼痛", "func_pain_txt": "疼痛(詳細)",
    "func_rom_limitation_chk": "関節可動域制限", "func_rom_limitation_txt": "関節可動域制限(詳細)",
    "func_contracture_deformity_chk": "拘縮・変形", "func_contracture_deformity_txt": "拘縮・変形(詳細)",
    "func_muscle_weakness_chk": "筋力低下", "func_muscle_weakness_txt": "筋力低下(詳細)",
    # 心身機能・構造 (運動・感覚)
    "func_motor_dysfunction_chk": "運動機能障害", "func_motor_paralysis_chk": "麻痺", "func_motor_involuntary_movement_chk": "不随意運動", "func_motor_ataxia_chk": "運動失調", "func_motor_parkinsonism_chk": "パーキンソニズム", "func_motor_muscle_tone_abnormality_chk": "筋緊張異常",
    "func_sensory_dysfunction_chk": "感覚機能障害", "func_sensory_hearing_chk": "聴覚障害", "func_sensory_vision_chk": "視覚障害", "func_sensory_superficial_chk": "表在感覚障害", "func_sensory_deep_chk": "深部感覚障害",
    # 心身機能・構造 (言語・高次脳)
    "func_speech_disorder_chk": "音声発話障害", "func_speech_articulation_chk": "構音障害", "func_speech_aphasia_chk": "失語症", "func_speech_stuttering_chk": "吃音",
    "func_higher_brain_dysfunction_chk": "高次脳機能障害", "func_higher_brain_memory_chk": "記憶障害(高次脳)", "func_higher_brain_attention_chk": "注意障害", "func_higher_brain_apraxia_chk": "失行", "func_higher_brain_agnosia_chk": "失認", "func_higher_brain_executive_chk": "遂行機能障害",
    "func_behavioral_psychiatric_disorder_chk": "精神行動障害", "func_behavioral_psychiatric_disorder_txt": "精神行動障害(詳細)",
    "func_disorientation_chk": "見当識障害", "func_disorientation_txt": "見当識障害(詳細)",
    "func_memory_disorder_chk": "記憶障害", "func_memory_disorder_txt": "記憶障害(詳細)",
    "func_developmental_disorder_chk": "発達障害", "func_developmental_asd_chk": "自閉症スペクトラム症(ASD)", "func_developmental_ld_chk": "学習障害(LD)", "func_developmental_adhd_chk": "注意欠陥多動性障害(ADHD)",
    # 基本動作
    "func_basic_rolling_chk": "寝返り", "func_basic_getting_up_chk": "起き上がり", "func_basic_standing_up_chk": "立ち上がり", "func_basic_sitting_balance_chk": "座位保持", "func_basic_standing_balance_chk": "立位保持",
    # 栄養
    "nutrition_height_val": "身長(cm)", "nutrition_weight_val": "体重(kg)", "nutrition_bmi_val": "BMI",
    "nutrition_method_oral_chk": "栄養補給(経口)", "nutrition_method_tube_chk": "栄養補給(経管)", "nutrition_method_iv_chk": "栄養補給(静脈)", "nutrition_method_peg_chk": "栄養補給(胃ろう)",
    "nutrition_swallowing_diet_True_chk": "嚥下調整食の必要性", "nutrition_swallowing_diet_code_txt": "嚥下調整食コード",
    "nutrition_status_assessment_malnutrition_chk": "栄養状態(低栄養)", "nutrition_status_assessment_malnutrition_risk_chk": "栄養状態(低栄養リスク)", "nutrition_status_assessment_overnutrition_chk": "栄養状態(過栄養)",
    "nutrition_required_energy_val": "必要熱量(kcal)", "nutrition_required_protein_val": "必要タンパク質量(g)",
    "nutrition_total_intake_energy_val": "総摂取熱量(kcal)", "nutrition_total_intake_protein_val": "総摂取タンパク質量(g)",
    # 社会保障サービス
    "social_care_level_status_chk": "介護保険", "social_care_level_applying_chk": "介護保険(申請中)", "social_care_level_support_chk": "要支援", "social_care_level_care_slct": "要介護",
    "social_disability_certificate_physical_chk": "身体障害者手帳", "social_disability_certificate_mental_chk": "精神障害者保健福祉手帳", "social_disability_certificate_intellectual_chk": "療育手帳",
    # 参加 (事実情報)
    "goal_p_residence_chk": "住居場所", "goal_p_return_to_work_chk": "復職", "goal_p_schooling_chk": "就学",
    "goal_p_household_role_txt": "家庭内役割(現状・希望)", "goal_p_social_activity_txt": "社会活動(現状・希望)", "goal_p_hobby_txt": "趣味",
    # 活動 (事実情報)
    "goal_a_bed_mobility_chk": "床上移動", "goal_a_indoor_mobility_chk": "屋内移動", "goal_a_outdoor_mobility_chk": "屋外移動", "goal_a_driving_chk": "自動車運転", "goal_a_public_transport_chk": "公共交通機関利用",
    "goal_a_toileting_chk": "排泄(移乗以外)", "goal_a_eating_chk": "食事", "goal_a_grooming_chk": "整容", "goal_a_dressing_chk": "更衣", "goal_a_bathing_chk": "入浴", "goal_a_housework_meal_chk": "家事",
    "goal_a_writing_chk": "書字", "goal_a_ict_chk": "ICT機器利用", "goal_a_communication_chk": "コミュニケーション",
}



def _prepare_patient_facts(patient_data: dict) -> dict:
    """プロンプトに渡すための患者の事実情報を整形する"""
    print(f"DEBUG [gemini_client.py]: therapist_notes received = '{str(patient_data.get('therapist_notes'))[:100]}...'")
    facts = {
        "基本情報": {},
        "心身機能・構造": {},
        "基本動作": {},
        "ADL評価": {"FIM(現在値)": {}, "BI(現在値)": {}},
        "栄養状態": {},
        "社会保障サービス": {},
        "生活状況・目標(本人・家族)": {},
        "担当者からの所見": _format_value(patient_data.get("therapist_notes", "特になし")),
    }
    print(f"DEBUG [gemini_client.py]: '担当者からの所見' in facts dict = {facts.get('担当者からの所見')}")

    facts["基本情報"]["年齢"] = f"{patient_data.get('age', '不明')}歳"
    facts["基本情報"]["性別"] = _format_value(patient_data.get("gender"))

    # 1. チェックボックスと関連しない項目を先に埋める
    for key, value in patient_data.items():
        formatted_value = _format_value(value)
        if formatted_value is None: continue

        # チェックボックスやそれに関連するテキストは、後の専用ロジックで処理するためスキップ
        if "_chk" in key or "_txt" in key and key in [t[1] for t in CHECK_TO_TEXT_MAP.items()]:
            continue

        jp_name = CELL_NAME_MAPPING.get(key)
        if not jp_name: continue

        category = None
        if key.startswith(("header_", "main_")): category = "基本情報"
        elif key.startswith("func_basic_"): category = "基本動作"
        elif key.startswith("nutrition_"): category = "栄養状態"
        elif key.startswith("social_"): category = "社会保障サービス"
        elif key.startswith("goal_p_"): category = "生活状況・目標(本人・家族)"
        elif key.startswith("func_"): category = "心身機能・構造"

        if category:
            facts[category][jp_name] = formatted_value

    # 2. チェックボックスの状態を最優先で、かつ正確に反映させる
    #    CHECK_TO_TEXT_MAPを基準にループすることで、処理を確実にする
    for chk_key, txt_key in CHECK_TO_TEXT_MAP.items():
        is_checked_value = patient_data.get(chk_key)
        is_truly_checked = str(is_checked_value).lower() in ['true', '1', 'on']

        # チェックが入っていない項目は、プロンプトに含めずにスキップする
        if not is_truly_checked:
            continue

        # --- ここからは、チェックが入っている項目のみが処理される ---
        jp_name = CELL_NAME_MAPPING.get(chk_key)
        if not jp_name: continue

        # データベースに具体的な記述があるか確認
        txt_value = patient_data.get(txt_key)
        
        # 記述が空の場合は、AIに推論を促す特別な指示を与える
        if not txt_value or txt_value.strip() == "特記なし":
            facts["心身機能・構造"][jp_name] = "あり（患者の他のデータに基づき、具体的な症状やADLへの影響を推測して記述してください）"
        else:
            # 具体的な記述があれば、それを事実として使用
            facts["心身機能・構造"][jp_name] = txt_value
    
    # 3. ADL評価スコアを抽出
    for key, value in patient_data.items():
        val = _format_value(value)
        if val is not None and "_val" in key:
            if "fim_current_val" in key:
                item_name = key.replace("adl_", "").replace("_fim_current_val", "").replace("_", " ").title()
                facts["ADL評価"]["FIM(現在値)"][item_name] = f"{val}点"
            elif "bi_current_val" in key:
                item_name = key.replace("adl_", "").replace("_bi_current_val", "").replace("_", " ").title()
                facts["ADL評価"]["BI(現在値)"][item_name] = f"{val}点"

    # 空のカテゴリやサブカテゴリを最終的に削除
    # facts = {k: v for k, v in facts.items() if v}
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


def _build_group_prompt(group_schema: type[BaseModel], patient_facts_str: str, generated_plan_so_far: dict) -> str:
    """グループ生成用のプロンプトを構築する"""
    return textwrap.dedent(f"""
        # 役割
        あなたは、経験豊富なリハビリテーション科の指導医です。
        患者の個別性を最大限に尊重し、一貫性のあるリハビリテーション実施計画書を作成してください。

        # 患者データ (事実情報)
        これは、患者の客観的な評価結果や基本情報です。
        ```json
        {patient_facts_str}
        ```

        # これまでの生成結果
        これは、あなたがこれまでに生成した計画書の一部です。
        この内容を十分に参照し、矛盾のない、より質の高い記述を生成してください。
        ```json
        {json.dumps(generated_plan_so_far, indent=2, ensure_ascii=False)}
        ```

        # 作成指示
        上記の「患者データ」と「これまでの生成結果」を統合的に解釈し、以下のJSONスキーマに厳密に従って、各項目を日本語で生成してください。
        - スキーマの`description`をよく読み、専門的かつ具体的な内容を記述してください。
        - 各項目は、他の項目との関連性や一貫性を保つように記述してください。
        - 患者データから判断して該当しない、または情報が不足している場合は、必ず「特記なし」とだけ記述してください。

        ```json
        {json.dumps(group_schema.model_json_schema(), indent=2, ensure_ascii=False)}
        ```
    """)

def generate_rehab_plan_stream(patient_data: dict, rag_executor: RAGExecutor):
    """
    患者データを基に、リハビリ計画の各項目を一つずつ生成し、ストリーミングで返すジェネレータ関数。
    """

    if USE_DUMMY_DATA:
        print("--- ダミーデータを使用しています ---")
        dummy_plan = get_dummy_plan()
        for key, value in dummy_plan.items():
            time.sleep(0.2)
            event_data = json.dumps({"key": key, "value": value})
            yield f"event: update\ndata: {event_data}\n\n"
        yield "event: finished\ndata: {}\n\n"
        return

    try:
        # 1. プロンプト用に患者の事実情報を整形
        patient_facts = _prepare_patient_facts(patient_data)
        patient_facts_str = json.dumps(patient_facts, indent=2, ensure_ascii=False)

        generated_plan_so_far = {}

        # ユーザーが既に入力済みの項目を先に処理
        for field_name in USER_INPUT_FIELDS:
            if patient_data.get(field_name):
                value = patient_data[field_name]
                generated_plan_so_far[field_name] = value
                event_data = json.dumps({"key": field_name, "value": value, "model_type": "general"})
                yield f"event: update\ndata: {event_data}\n\n"

        # 2. グループごとに生成
        for group_schema in GENERATION_GROUPS:
            # 3. プロンプトの構築
            prompt = _build_group_prompt(group_schema, patient_facts_str, generated_plan_so_far)

            # 4. API呼び出し実行 (JSONモード)
            generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=group_schema,
            )

            # --- リトライ処理の追加 ---
            max_retries = 3
            backoff_factor = 2  # 初回待機時間（秒）
            response = None

            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-lite", contents=prompt, config=generation_config
                    )
                    break  # 成功した場合はループを抜ける
                except (ResourceExhausted, ServiceUnavailable) as e:
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        print(f"API rate limit or overload error: {e}. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"API call failed after {max_retries} retries.")
                        raise e  # 最終的に失敗した場合はエラーを再送出

            if not response.parsed:
                raise Exception(f"グループ {group_schema.__name__} のJSON生成に失敗しました。応答: {response.text}")

            group_result = response.parsed.model_dump()

            # 5. グループ内の各項目を処理してストリームに流す
            for field_name, generated_text in group_result.items():
                final_text = generated_text

                # チェックなし項目の上書き処理
                is_truly_checked = True
                if field_name in CHECK_TO_TEXT_MAP.values():
                    chk_key = next((chk for chk, txt in CHECK_TO_TEXT_MAP.items() if txt == field_name), None)
                    if chk_key:
                        is_checked_in_db = patient_data.get(chk_key)
                        is_truly_checked = str(is_checked_in_db).lower() in ['true', '1', 'on']

                if not is_truly_checked:
                    final_text = "特記なし"
                # チェックありなのに「特記なし」と生成された場合の復元処理
                elif is_truly_checked and generated_text == "特記なし":
                    original_text = patient_data.get(field_name)
                    if original_text and original_text != "特記なし":
                        final_text = original_text

                # 生成結果を格納し、ストリームに流す
                generated_plan_so_far[field_name] = final_text
                event_data = json.dumps({"key": field_name, "value": final_text, "model_type": "general"})
                yield f"event: update\ndata: {event_data}\n\n"

        print("--- Gemini汎用項目の生成完了 ---")
        # Geminiによる生成が完了したことをフロントエンドに教える
        yield "event: general_finished\ndata: {}\n\n"

        print("\n--- RAGモデルによる生成を開始 ---")
        try:
            # # RAG実行の司令塔をインスタンス化  
            # rag_executor = RAGExecutor()   app.pyで最初にインスタンス化するようにした。

            rag_result = rag_executor.execute(patient_facts)

            specialized_plan_dict = rag_result.get("answer", {})
            contexts = rag_result.get("contexts", [])

            if "error" in specialized_plan_dict:
                print(f"RAG Executorからのエラー: {specialized_plan_dict['error']}")
                rag_keys = ['policy_treatment_txt', 'policy_content_txt', 'goal_a_action_plan_txt', 'goal_s_env_action_plan_txt', 'goal_p_action_plan_txt']

                # エラーが発生した場合も、キーごとにエラーメッセージを流す
                # for key in specialized_plan_dict.keys(): # スキーマではなく辞書のキーを直接使用
                #     error_value = f"RAGエラー: {specialized_plan_dict['error']}"
                #     event_data = json.dumps({"key": key, "value": error_value, "model_type": "specialized"})
                #     yield f"event: update\ndata: {event_data}\n\n"

                for key in rag_keys:
                    error_value = f"RAGエラー: {specialized_plan_dict['error']}"
                    event_data = json.dumps({"key": key, "value": error_value, "model_type": "specialized"})
                    yield f"event: update\ndata: {event_data}\n\n"

            else:
                # 成功した場合、取得した辞書を項目ごとにストリームに流す
                for key, value in specialized_plan_dict.items():
                    event_data = json.dumps({"key": key, "value": value, "model_type": "specialized"})
                    yield f"event: update\ndata: {event_data}\n\n"

                # 全ての専門項目の生成が終わった後、根拠情報のリストを送信する
                if contexts:
                    contexts_for_frontend = []
                    for i, ctx in enumerate(contexts):
                        metadata = ctx.get("metadata", {})
                        contexts_for_frontend.append({
                            "id": i + 1,
                            "content": ctx.get("content", ""),
                            "source": metadata.get('source', 'N/A'),
                            "disease": metadata.get('disease', 'N/A'),
                            "section": metadata.get('section', 'N/A')
                        })
                    
                    context_event_data = json.dumps(contexts_for_frontend)
                    yield f"event: context_update\ndata: {context_event_data}\n\n"




        except Exception as e:
            print(f"RAG Executorの実行中にエラーが発生しました: {e}")
            # RAG実行全体でエラーが起きた場合
            # RAGが生成するべきキーのリストを事前に定義しておく
            rag_keys = ['policy_treatment_txt', 'policy_content_txt', 'goal_a_action_plan_txt', 'goal_s_env_action_plan_txt', 'goal_p_action_plan_txt']
            for key in rag_keys:
                error_value = f"RAG実行エラー: {e}"
                event_data = json.dumps({"key": key, "value": error_value, "model_type": "specialized"})
                yield f"event: update\ndata: {event_data}\n\n"
        yield "event: finished\ndata: {}\n\n"

    except Exception as e:
        print(f"Gemini API呼び出し中に予期せぬエラーが発生しました: {e}")
        error_message = f"AIとの通信中にエラーが発生しました: {e}"
        error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
        yield error_event



# メイン関数 (旧関数)
def generate_rehab_plan(patient_data, rag_executor: RAGExecutor):
    """
    [非推奨] 患者データを基にプロンプトを生成し、Gemini APIにリハビリ計画の作成を依頼する
    この関数は下位互換性のために残されていますが、新しいストリーミング方式の使用が推奨されます。
    """
    stream = generate_rehab_plan_stream(patient_data, rag_executor)
    full_plan = {}
    for event in stream:
        if event.startswith("event: update"):
            data_str = event.split("data: ")[1].strip()
            data = json.loads(data_str)
            full_plan[data['key']] = data['value']
        elif event.startswith("event: error"):
            data_str = event.split("data: ")[1].strip()
            return json.loads(data_str)
    return full_plan


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
    print("--- Geminiクライアントモジュールのテスト実行 ---")

    sample_patient_data = {
        "name": "テスト患者",
        "age": 75,
        "gender": "男性",
        "header_disease_name_txt": "脳梗塞右片麻痺",
        "therapist_notes": "本人の退院意欲は高いが、自宅の段差に対して不安を感じている。趣味は囲碁。",
        # 事実データ (DBから取得される想定)
        "func_motor_paralysis_chk": True,
        "func_muscle_weakness_chk": True,
        "func_pain_chk": True,
        "func_swallowing_disorder_chk": True,
        "nutrition_swallowing_diet_code_txt": "2-1",
        "adl_eating_fim_current_val": 4,
        "adl_transfer_bed_chair_wc_fim_current_val": 3,
        "adl_locomotion_walk_walkingAids_wc_fim_current_val": 2,
    }

    USE_DUMMY_DATA = False

    stream_generator = generate_rehab_plan_stream(sample_patient_data)

    print("\n--- 生成された計画 (結果) ---")
    final_plan = {}
    error = None
    for event in stream_generator:
        print(event) # ストリームの各イベントを表示
        if "event: update" in event:
            data = json.loads(event.split("data: ")[1])
            final_plan[data['key']] = data['value']
        elif "event: error" in event:
            error = json.loads(event.split("data: ")[1])

    if error:
        print(f"\nテスト実行中にエラーが検出されました: {error}")
    else:
        print("\nテストが正常に完了しました。")
        pprint.pprint(final_plan)
