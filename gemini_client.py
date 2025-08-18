import os
import json
import textwrap

# import google.generativeai as genai ←2025,9月までしかサポートなし
# https://ai.google.dev/gemini-api/docs/libraries?hl=ja  新ライブラリ
# https://ai.google.dev/gemini-api/docs/quickstart?hl=ja 使い方
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

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
class RehabPlanSchema(BaseModel):
    # --- 事実の要約 ---
    # main_comorbidities_txt: str = Field(description="患者データから併存疾患・合併症を要約して記述")

    # --- 臨床推論に基づく生成 ---
    main_risks_txt: str = Field(
        description="算定病名、併存疾患、ADL状況から考えられる安静度やリハビリテーション施行上のリスクを具体的に考察して記述"
    )
    main_contraindications_txt: str = Field(
        description="術式や疾患特有の禁忌や、リハビリを行う上での医学的な特記事項・注意点を考察して記述"
    )

    func_pain_txt: str = Field(
        description="「疼痛あり」の場合、どの部位に、どのような動作で、どの程度の痛み(NRS等)が生じる可能性があるかを臨床的に推測して記述。ない場合は「特記なし」と記述。"
    )
    func_rom_limitation_txt: str = Field(
        description="「関節可動域制限あり」の場合、その制限が具体的にどの日常生活動作(ADL)の妨げになっているかを考察して記述。ない場合は「特記なし」と記述。"
    )
    func_muscle_weakness_txt: str = Field(
        description="「筋力低下あり」の場合、その筋力低下が原因で困難となっている具体的な動作との関連性を考察して記述。ない場合は「特記なし」と記述。"
    )
    func_swallowing_disorder_txt: str = Field(
        description="「摂食嚥下障害あり」の場合、栄養情報にある嚥下調整食コードなどを参考に、具体的な食事形態や注意点を記述。ない場合は「特記なし」と記述。"
    )
    func_behavioral_psychiatric_disorder_txt: str = Field(
        description="「精神行動障害あり」の場合、リハビリ中の関わり方や環境設定での具体的な注意点を記述。ない場合は「特記なし」と記述。"
    )

    adl_equipment_and_assistance_details_txt: str = Field(
        description="FIM/BIの各項目点数から、ADL自立度向上のために適切と考えられる福祉用具の選定案や、具体的な介助方法を提案"
    )

    goals_1_month_txt: str = Field(
        description="患者データ、特にADL状況や担当者所見から、1ヶ月で達成可能かつ具体的な短期目標（SMARTゴール）を設定"
    )
    goals_at_discharge_txt: str = Field(description="患者の全体像を考慮し、退院時に達成を目指す現実的な長期目標を設定")

    policy_treatment_txt: str = Field(description="全ての情報を統合し、リハビリテーションの全体的な治療方針を専門的に記述")
    policy_content_txt: str = Field(
        description="治療方針に基づき、理学療法・作業療法・言語聴覚療法の具体的な訓練メニュー案を箇条書き形式（改行は\\n）で複数提案"
    )

    # goal_p_household_role_txt: str = Field(
    #     description="患者の年齢、性別、ADL状況から、退院後に担う可能性のある現実的な家庭内役割の具体例を提案"
    # )
    # goal_p_hobby_txt: str = Field(description="患者のQOL向上に繋がりそうな趣味活動の具体例を提案")

    goal_a_action_plan_txt: str = Field(
        description="設定した活動目標（ADLなど）を達成するための具体的な対応方針、環境調整、指導内容を記述"
    )
    goal_s_env_action_plan_txt: str = Field(
        description="退院後の生活を見据え、必要と考えられる住宅改修、社会資源の活用（介護保険サービス、障害福祉サービス等）に関する具体的な対応方針を記述"
    )


# ヘルパー関数
# DBカラム名と日本語名のマッピング
CELL_NAME_MAPPING = {
    "func_consciousness_disorder_chk": "意識障害",
    "func_respiratory_disorder_chk": "呼吸機能障害",
    "func_circulatory_disorder_chk": "循環障害",
    "func_risk_hypertension_chk": "高血圧症",
    "func_risk_diabetes_chk": "糖尿病",
    "func_swallowing_disorder_chk": "摂食嚥下障害",
    "func_excretory_disorder_chk": "排泄機能障害",
    "func_pain_chk": "疼痛",
    "func_rom_limitation_chk": "関節可動域制限",
    "func_muscle_weakness_chk": "筋力低下",
    "func_motor_paralysis_chk": "麻痺",
    "func_sensory_dysfunction_chk": "感覚機能障害",
    "func_speech_disorder_chk": "音声発話障害",
    "func_higher_brain_dysfunction_chk": "高次脳機能障害",
    "func_behavioral_psychiatric_disorder_chk": "精神行動障害",
    "func_disorientation_chk": "見当識障害",
    "func_memory_disorder_chk": "記憶障害",
}


def _prepare_patient_facts(patient_data: dict) -> dict:
    """プロンプトに渡すための患者の事実情報を整形するヘルパー関数"""
    facts = {
        "基本情報": {
            "年代": f"{patient_data.get('age', '不明')}歳代",
            "性別": patient_data.get("gender", "不明"),
            "算定病名": patient_data.get("header_disease_name_txt", "情報なし"),
            "治療内容": patient_data.get("header_treatment_details_txt", "情報なし"),
        },
        "心身機能の特記事項": [],
        "ADL状況 (FIM現在値)": {},
        "栄養関連情報": {"嚥下調整食コード": patient_data.get("nutrition_swallowing_diet_code_txt", "なし")},
        "担当者からの所見": patient_data.get("therapist_notes", "特になし"),
    }

    # 心身機能のチェック項目を日本語に変換してリスト化
    for key, jp_name in CELL_NAME_MAPPING.items():
        if patient_data.get(key):
            facts["心身機能の特記事項"].append(jp_name)
    if not facts["心身機能の特記事項"]:
        facts["心身機能の特記事項"] = "特記なし"

    # FIMの現在値を抽出
    for key, value in patient_data.items():
        if key.startswith("adl_") and key.endswith("_fim_current_val"):
            item_name = key.replace("adl_", "").replace("_fim_current_val", "").capitalize()
            if value is not None:
                facts["ADL状況 (FIM現在値)"][item_name] = f"{value}点"
    if not facts["ADL状況 (FIM現在値)"]:
        facts["ADL状況 (FIM現在値)"] = "データなし"

    return facts


# メイン関数
def generate_rehab_plan(patient_data):
    """
    患者データを基にプロンプトを生成し、Gemini APIにリハビリ計画の作成を依頼する
    """
    if USE_DUMMY_DATA:
        print("--- ダミーデータを使用しています ---")
        return get_dummy_plan()

    try:
        # 1. プロンプト用に患者の事実情報を整形
        patient_facts = _prepare_patient_facts(patient_data)

        # 2. プロンプトを部品に分割して安全に組み立てる
        prompt_start = textwrap.dedent("""
            # 役割
            あなたは、経験豊富なリハビリテーション科の指導医です。提供された客観的な患者データを基に、専門的な臨床推論を行い、リハビリテーション実施計画書の各項目を日本語で作成してください。

            # 患者データ (事実情報)
        """)

        prompt_end = textwrap.dedent("""
            # 作成指示
            上記の患者データを深く分析し、以下の各項目について、日本の医療現場で通用する専門的かつ具体的な内容を生成してください。生成する内容は、JSON形式で、指示されたスキーマに厳密に従う必要があります。事実だけでなく、あなたの専門的な考察を加えてください。
        """)

        json_data_string = json.dumps(patient_facts, indent=2, ensure_ascii=False)
        prompt = f"{prompt_start}\n```json\n{json_data_string}\n```\n\n{prompt_end}"

        print("--- 生成されたプロンプト ---\n" + prompt + "\n--------------------------")

        # 3. API呼び出し設定
        # JSONのように構造化した出力を設定する方法
        # https://ai.google.dev/gemini-api/docs/structured-output?hl=ja

        # configでJSON形式とそのスキーマを指定することで、安定してJSONを出力させます。
        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RehabPlanSchema,
        )

        # 4. API呼び出し実行
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=generation_config)

        # 5. 結果の処理 パースした結果(.parsed)を使用します。
        if response.parsed:
            # Pydanticモデルを辞書に変換して返す
            ai_plan = response.parsed.model_dump()
            # ユーザーが既に入力した併存疾患はAIの生成で上書きしない
            if patient_data.get("main_comorbidities_txt"):
                ai_plan["main_comorbidities_txt"] = patient_data["main_comorbidities_txt"]
            return ai_plan
        else:
            print("JSONパースエラー: レスポンスをスキーマに沿ってパースできませんでした。")
            print(f"--- AIからの不正な応答 ---\n{response.text}\n--------------------")
            return {"error": "AIからの応答をJSONとして解析できませんでした。"}

    except Exception as e:
        print(f"Gemini API呼び出し中に予期せぬエラーが発生しました: {e}")
        return {"error": f"AIとの通信中にエラーが発生しました: {e}"}


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

    generated_plan = generate_rehab_plan(sample_patient_data)

    print("\n--- 生成された計画 (結果) ---")
    import pprint

    # pprintを使うと、辞書を人間が読みやすい形に整形して表示してくれます。
    pprint.pprint(generated_plan)
    print("--------------------------")

    if "error" in generated_plan:
        print("\nテスト実行中にエラーが検出されました。")
    else:
        print("\nテストが正常に完了しました。")
