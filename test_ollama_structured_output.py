# test_ollama_structured_output_v2.py

import ollama
import json
from pydantic import BaseModel, Field, ValidationError # ValidationErrorをインポート

# 1. 出力してほしいJSONの構造をPydanticモデルで定義
class Person(BaseModel):
    name: str = Field(description="抽出された人物の名前")
    age: int = Field(description="抽出された人物の年齢")
    city: str = Field(description="抽出された人物が住んでいる都市")

def test_structured_output_v2():
    """Ollamaの構造化出力機能をテストする関数 (エラーハンドリング強化版)"""
    print("--- Ollama構造化出力テスト開始 (v2) ---")

    # Ollamaがローカルで起動していることを確認してください
    # `ollama pull gemma3` などでモデルを事前にダウンロードしておいてください
    # 構造化出力はモデルによってサポート状況が異なります
    model_name = 'qwen3:0.6b' # 前回使用したモデル名を指定
    print(f"\nモデル '{model_name}' を使用します。")

    messages = [
        {
            'role': 'user',
            # プロンプトは前回と同じ
            'content': """
            
            # 役割
            あなたは、患者様とそのご家族にリハビリテーション計画を説明する、経験豊富で説明上手なリハビリテーション科の専門医です。
            専門用語を避け、誰にでも理解できる平易な言葉で、誠実かつ丁寧に説明する文章を使用して、患者の個別性を最大限に尊重し、一貫性のあるリハビリテーション総合実施計画書を作成してください。

            # 患者データ (事実情報)
            ```json
            {
  "基本情報": {
    "年齢": "60代後半",
    "性別": "男",
    "算定病名": "左変形性股関節症による人工股関節全置換術後",
    "発症日・手術日": "2025-09-10",
    "リハ開始日": "2025-09-17",
    "併存疾患・合併症": "骨粗鬆症、高血圧症（内服治療中、血圧コントロール良好）"
  },
  "心身機能・構造": {
    "疼痛": "あり（患者の他のデータに基づき、具体的な症状やADLへの影響を推測して記述してください）",
    "関節可動域制限": "あり（患者の他のデータに基づき、具体的な症状やADLへの影響を推測して記述してください）",
    "筋力低下": "あり（患者の他のデータに基づき、具体的な症状やADLへの影響を推測して記述してください）"
  },
  "ADL評価": {
    "FIM(現在値)": {
      "Eating": "7点",
      "Grooming": "6点",
      "Bathing": "5点",
      "Dressing Upper": "7点",
      "Dressing Lower": "4点",
      "Toileting": "6点",
      "Bladder Management": "7点",
      "Bowel Management": "7点",
      "Transfer Bed Chair Wc": "5点",
      "Transfer Toilet": "5点",
      "Transfer Tub Shower": "4点",
      "Locomotion Walk Walkingaids Wc": "4点",
      "Locomotion Stairs": "1点",
      "Comprehension": "7点",
      "Expression": "7点"
    }
  },
  "栄養状態": {
    "身長(cm)": "168.0",
    "体重(kg)": "63.0",
    "BMI": "22.3"
  },
  "社会保障サービス": {
    "要介護": "あり"
  },
  "生活状況・目標(本人・家族)": {
    "社会活動(現状・希望)": "地域でのゴルフサークル活動への復帰。夫婦での旅行（国内）の再開。",
    "趣味": "ゴルフ、旅行、園芸（ベランダでの鉢植え程度）"
  },
  "担当者からの所見": "特になし"
}
            ```

            # 作成指示
            上記の「患者データ」を統合的に解釈し、以下のJSONスキーマに厳密に従って、**計画書全体の項目**を日本語で生成してください。
            - **最重要**: 生成する文章は、患者様やそのご家族が直接読んでも理解できるよう、**専門用語を避け、できるだけ平易な言葉で記述してください**。
            - ただし、**病名や疾患名はそのまま使用してください**。
            - 専門用語の言い換え例: 「ADL」→「日常生活の動作」、「ROM訓練」→「関節を動かす練習」、「嚥下」→「飲み込み」、「拘縮」→「関節が硬くなること」、「麻痺」→「手足が動きにくくなること」
            - 患者データから判断して該当しない、または情報が不足している場合は、必ず「特記なし」とだけ記述してください。
            - スキーマの`description`をよく読み、具体的で分かりやすい内容を記述してください。
            - 各項目は、他の項目との関連性や一貫性を保つように記述してください。

            ```json
            {
  "properties": {
    "main_risks_txt": {
      "description": "算定病名、併存疾患、ADL状況から考えられる安静度やリハビリテーション施行上のリスクを具体的に考察して簡潔に記述(50文字程度)",
      "title": "Main Risks Txt",
      "type": "string"
    },
    "main_contraindications_txt": {
      "description": "術式や疾患特有の禁忌や、リハビリを行う上での医学的な特記事項・注意点を考察して簡潔に記述(50文字程度)",
      "title": "Main Contraindications Txt",
      "type": "string"
    },
    "func_pain_txt": {
      "description": "患者データの'func_pain_chk'がTrueの場合、どの部位に、どのような動作で、どの程度の痛み(NRS等)が生じる可能性があるかを臨床的に推測して簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Pain Txt",
      "type": "string"
    },
    "func_rom_limitation_txt": {
      "description": "患者データの'func_rom_limitation_chk'がTrueの場合、その制限が具体的にどの日常生活動作(ADL)の妨げになっているかを考察して簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Rom Limitation Txt",
      "type": "string"
    },
    "func_muscle_weakness_txt": {
      "description": "患者データの'func_muscle_weakness_chk'がTrueの場合、その筋力低下が原因で困難となっている具体的な動作との関連性を考察して簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Muscle Weakness Txt",
      "type": "string"
    },
    "func_swallowing_disorder_txt": {
      "description": "患者データの'func_swallowing_disorder_chk'がTrueの場合、栄養情報にある嚥下調整食コードなどを参考に、具体的な食事形態や注意点を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Swallowing Disorder Txt",
      "type": "string"
    },
    "func_behavioral_psychiatric_disorder_txt": {
      "description": "患者データの'func_behavioral_psychiatric_disorder_chk'がTrueの場合、リハビリ中の関わり方や環境設定での具体的な注意点を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Behavioral Psychiatric Disorder Txt",
      "type": "string"
    },
    "func_nutritional_disorder_txt": {
      "description": "患者データの'func_nutritional_disorder_chk'がTrueの場合、具体的な状態（例：低体重、特定の栄養素の欠乏）や食事摂取における課題を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Nutritional Disorder Txt",
      "type": "string"
    },
    "func_excretory_disorder_txt": {
      "description": "患者データの'func_excretory_disorder_chk'がTrueの場合、具体的な症状（例：尿失禁、便秘、カテーテル留置）を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Excretory Disorder Txt",
      "type": "string"
    },
    "func_pressure_ulcer_txt": {
      "description": "患者データの'func_pressure_ulcer_chk'がTrueの場合、発生部位と重症度（DESIGN-Rなど）を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Pressure Ulcer Txt",
      "type": "string"
    },
    "func_contracture_deformity_txt": {
      "description": "患者データの'func_contracture_deformity_chk'がTrueの場合、具体的な部位とADLへの影響を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Contracture Deformity Txt",
      "type": "string"
    },
    "func_motor_muscle_tone_abnormality_txt": {
      "description": "患者データの'func_motor_muscle_tone_abnormality_chk'がTrueの場合、具体的な状態（痙性、固縮、低緊張など）と部位を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Motor Muscle Tone Abnormality Txt",
      "type": "string"
    },
    "func_disorientation_txt": {
      "description": "患者データの'func_disorientation_chk'がTrueの場合、どの見当識（時間、場所、人物）に問題があるかを簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Disorientation Txt",
      "type": "string"
    },
    "func_memory_disorder_txt": {
      "description": "患者データの'func_memory_disorder_chk'がTrueの場合、具体的な症状（短期記憶の低下、エピソード記憶の欠落など）を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。",
      "title": "Func Memory Disorder Txt",
      "type": "string"
    },
    "adl_equipment_and_assistance_details_txt": {
      "description": "FIM/BIの各項目点数から、ADL自立度向上のために適切と考えられる福祉用具の選定案や、具体的な介助方法を提案(200文字程度から400文字程度)",
      "title": "Adl Equipment And Assistance Details Txt",
      "type": "string"
    },
    "goals_1_month_txt": {
      "description": "患者データ、特にADL状況や担当者所見から、1ヶ月で達成可能かつ具体的な短期目標（SMARTゴール）を設定(100文字から200文字程度)",
      "title": "Goals 1 Month Txt",
      "type": "string"
    },
    "goals_at_discharge_txt": {
      "description": "患者の全体像を考慮し、退院時に達成を目指す現実的な長期目標を設定(100文字から150文字程度)",
      "title": "Goals At Discharge Txt",
      "type": "string"
    },
    "policy_treatment_txt": {
      "description": "全ての情報を統合し、リハビリテーションの全体的な治療方針を専門的に記述(100文字から500文字程度)",
      "title": "Policy Treatment Txt",
      "type": "string"
    },
    "policy_content_txt": {
      "description": "治療方針に基づき、理学療法・作業療法・言語聴覚療法の具体的な訓練メニュー案を箇条書き形式で複数提案(100文字から250文字程度)。作業療法や理学療法など、職種が変わるときのみ改行してください。改行をしないでください。(100文字から250文字程度)",
      "title": "Policy Content Txt",
      "type": "string"
    },
    "goal_a_action_plan_txt": {
      "description": "設定した活動目標（ADLなど）を達成するための具体的な対応方針、環境調整、指導内容を記述(100文字から500文字程度)",
      "title": "Goal A Action Plan Txt",
      "type": "string"
    },
    "goal_s_env_action_plan_txt": {
      "description": "退院後の生活を見据え、必要と考えられる住宅改修、社会資源の活用（介護保険サービス、障害福祉サービス等）に関する具体的な対応方針を記述(100文字から500文字程度)",
      "title": "Goal S Env Action Plan Txt",
      "type": "string"
    },
    "goal_p_action_plan_txt": {
      "description": "参加目標（復職、就学、家庭内役割など）を達成するための具体的な対応方針、関連機関との連携、家族への指導内容などを記述(100文字から300文字程度)",
      "title": "Goal P Action Plan Txt",
      "type": "string"
    },
    "goal_s_psychological_action_plan_txt": {
      "description": "心理面での目標（障害受容、精神的支援など）に対する具体的な関わり方、声かけ、家族への説明内容などを記述(100文字から200文字程度)",
      "title": "Goal S Psychological Action Plan Txt",
      "type": "string"
    },
    "goal_s_3rd_party_action_plan_txt": {
      "description": "主介護者や家族の負担軽減、環境の変化に対する具体的な支援策や社会資源の活用提案などを記述(100文字から200文字程度)",
      "title": "Goal S 3Rd Party Action Plan Txt",
      "type": "string"
    }
  },
  "required": [
    "main_risks_txt",
    "main_contraindications_txt",
    "func_pain_txt",
    "func_rom_limitation_txt",
    "func_muscle_weakness_txt",
    "func_swallowing_disorder_txt",
    "func_behavioral_psychiatric_disorder_txt",
    "func_nutritional_disorder_txt",
    "func_excretory_disorder_txt",
    "func_pressure_ulcer_txt",
    "func_contracture_deformity_txt",
    "func_motor_muscle_tone_abnormality_txt",
    "func_disorientation_txt",
    "func_memory_disorder_txt",
    "adl_equipment_and_assistance_details_txt",
    "goals_1_month_txt",
    "goals_at_discharge_txt",
    "policy_treatment_txt",
    "policy_content_txt",
    "goal_a_action_plan_txt",
    "goal_s_env_action_plan_txt",
    "goal_p_action_plan_txt",
    "goal_s_psychological_action_plan_txt",
    "goal_s_3rd_party_action_plan_txt"
  ],
  "title": "RehabPlanSchema",
  "type": "object"
}
            ```
            ---
            生成するJSON:
            """
            
        }
    ]

    raw_content = None # Ollamaの生応答を格納する変数を初期化
    success = False # テスト成功フラグ

    try:
        print(f"\nOllama APIを呼び出します...")
        response = ollama.chat(
            model=model_name,
            messages=messages,
            format='json',
            stream=False
        )

        print("\n--- Ollamaからの生の応答 (message.content) ---")
        raw_content = response['message']['content']
        print(raw_content)

        # 2. JSON形式チェックを追加
        print("\n--- JSON形式チェック ---")
        try:
            # json.loadsでパースできるか試す
            json.loads(raw_content)
            print("有効なJSON形式です。")
        except json.JSONDecodeError as json_err:
            print(f"JSON形式エラー: Ollamaからの応答は有効なJSONではありません。エラー詳細: {json_err}")
            # Pydantic検証に進まずに終了
            return False

        # 3. Pydanticモデルでの検証 (エラー詳細表示を強化)
        print("\n--- Pydanticモデルでの検証 ---")
        try:
            # JSON文字列をパースしてPydanticオブジェクトに変換
            parsed_person = Person.model_validate_json(raw_content)
            print("検証成功！ ✨")
            print(parsed_person)
            success = True # 検証成功

        # PydanticのValidationErrorを具体的に捕捉
        except ValidationError as val_err:
            print("Pydantic検証エラー: Ollamaの応答が期待するスキーマと一致しません。")
            # エラーの詳細（どのフィールドで何が問題か）を表示
            print("--- エラー詳細 ---")
            for error in val_err.errors():
                loc_str = " -> ".join(map(str, error['loc'])) # エラー発生箇所
                print(f"  フィールド: {loc_str}")
                print(f"  エラータイプ: {error['type']}")
                print(f"  メッセージ: {error['msg']}")
                # print(f"  入力値: {error.get('input', 'N/A')}") # デバッグ用に値も表示
            print("-----------------")
            success = False # 検証失敗

        except Exception as e:
            # その他の予期せぬエラー
            print(f"予期せぬ検証エラーが発生しました: {e}")
            success = False # 検証失敗

    except Exception as e:
        print(f"\nOllama API呼び出し中にエラーが発生しました: {e}")
        print("考えられる原因:")
        print("  - Ollamaサーバーが起動していない (ollama serve)")
        print(f"  - モデル '{model_name}' がダウンロードされていない (ollama pull {model_name})")
        print("  - ネットワーク接続の問題")
        success = False # API呼び出し失敗

    finally:
        print("\n--- テスト終了 ---")
        return success

if __name__ == "__main__":
    test_successful = test_structured_output_v2()
    if test_successful:
        print("\n結論: Ollamaは指定されたモデルで構造化出力（JSON）に成功しました。✅")
    else:
        print("\n結論: Ollamaの構造化出力に失敗しました。❌")
        print("上記のエラー詳細を確認し、以下の点を検討してください:")
        print("  1. プロンプトの調整: モデルがスキーマをより理解しやすいように指示を追加する (例: '必ずageとcityを含めてください')")
        print("  2. モデルの変更: 構造化出力の能力が高いとされる別のモデル (qwen3, gpt-ossなど) を試す")
        print("  3. Ollamaのバージョン確認: 最新バージョンを使用しているか確認する")