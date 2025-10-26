from pydantic import BaseModel, Field

# Pydanticを使用して、AIに生成してほしいJSONの構造を定義します。
# Field(description=...) を使用して、各項目が何を意味するのかをAIに明確に伝えます。
class RehabPlanSchema(BaseModel):
    # 事実の要約
    # main_comorbidities_txt: str = Field(description="患者データから併存疾患・合併症を要約して記述")

    # 臨床推論に基づく生成
    main_risks_txt: str = Field(
        description="算定病名、併存疾患、ADL状況から考えられる安静度やリハビリテーション施行上のリスクを具体的に考察して簡潔に記述(60文字程度)"
    )
    main_contraindications_txt: str = Field(
        description="術式や疾患特有の禁忌や、リハビリを行う上での医学的な特記事項・注意点を考察して簡潔に記述(60文字程度)"
    )

    func_pain_txt: str = Field(
        description="患者データの'func_pain_chk'がTrueの場合、どの部位に、どのような動作で、どの程度の痛み(NRS等)が生じる可能性があるかを臨床的に推測して簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_rom_limitation_txt: str = Field(
        description="患者データの'func_rom_limitation_chk'がTrueの場合、その制限が具体的にどの日常生活動作(ADL)の妨げになっているかを考察して簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_muscle_weakness_txt: str = Field(
        description="患者データの'func_muscle_weakness_chk'がTrueの場合、その筋力低下が原因で困難となっている具体的な動作との関連性を考察して簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_swallowing_disorder_txt: str = Field(
        description="患者データの'func_swallowing_disorder_chk'がTrueの場合、栄養情報にある嚥下調整食コードなどを参考に、具体的な食事形態や注意点を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_behavioral_psychiatric_disorder_txt: str = Field(
        description="患者データの'func_behavioral_psychiatric_disorder_chk'がTrueの場合、リハビリ中の関わり方や環境設定での具体的な注意点を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )

    func_nutritional_disorder_txt: str = Field(
        description="患者データの'func_nutritional_disorder_chk'がTrueの場合、具体的な状態（例：低体重、特定の栄養素の欠乏）や食事摂取における課題を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_excretory_disorder_txt: str = Field(
        description="患者データの'func_excretory_disorder_chk'がTrueの場合、具体的な症状（例：尿失禁、便秘、カテーテル留置）を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_pressure_ulcer_txt: str = Field(
        description="患者データの'func_pressure_ulcer_chk'がTrueの場合、発生部位と重症度（DESIGN-Rなど）を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_contracture_deformity_txt: str = Field(
        description="患者データの'func_contracture_deformity_chk'がTrueの場合、具体的な部位とADLへの影響を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_motor_muscle_tone_abnormality_txt: str = Field(
        description="患者データの'func_motor_muscle_tone_abnormality_chk'がTrueの場合、具体的な状態（痙性、固縮、低緊張など）と部位を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_disorientation_txt: str = Field(
        description="患者データの'func_disorientation_chk'がTrueの場合、どの見当識（時間、場所、人物）に問題があるかを簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )
    func_memory_disorder_txt: str = Field(
        description="患者データの'func_memory_disorder_chk'がTrueの場合、具体的な症状（短期記憶の低下、エピソード記憶の欠落など）を簡潔に記述(20文字程度)。Falseまたはデータがない場合は必ず「特記なし」と記述してください。"
    )

    adl_equipment_and_assistance_details_txt: str = Field(
        description="FIM/BIの各項目点数から、ADL自立度向上のために適切と考えられる福祉用具の選定案や、具体的な介助方法を提案"
    )

    goals_1_month_txt: str = Field(
        description="患者データ、特にADL状況や担当者所見から、1ヶ月で達成可能かつ具体的な短期目標（SMARTゴール）を設定(100文字から200文字程度)"
    )
    goals_at_discharge_txt: str = Field(
        description="患者の全体像を考慮し、退院時に達成を目指す現実的な長期目標を設定(100文字から150文字程度)"
    )

    policy_treatment_txt: str = Field(
        description="全ての情報を統合し、リハビリテーションの全体的な治療方針を専門的に記述(100文字から500文字程度)"
    )
    policy_content_txt: str = Field(
        description="治療方針に基づき、理学療法・作業療法・言語聴覚療法の具体的な訓練メニュー案を箇条書き形式で複数提案(100文字から300文字程度)"
    )

    # goal_p_household_role_txt: str = Field(
    #     description="患者の年齢、性別、ADL状況から、退院後に担う可能性のある現実的な家庭内役割の具体例を提案"
    # )
    # goal_p_hobby_txt: str = Field(description="患者のQOL向上に繋がりそうな趣味活動の具体例を提案")

    goal_a_action_plan_txt: str = Field(
        description="設定した活動目標（ADLなど）を達成するための具体的な対応方針、環境調整、指導内容を記述(100文字から500文字程度)"
    )
    goal_s_env_action_plan_txt: str = Field(
        description="退院後の生活を見据え、必要と考えられる住宅改修、社会資源の活用（介護保険サービス、障害福祉サービス等）に関する具体的な対応方針を記述(100文字から500文字程度)"
    )
    goal_p_action_plan_txt: str = Field(
        description="参加目標（復職、就学、家庭内役割など）を達成するための具体的な対応方針、関連機関との連携、家族への指導内容などを記述(100文字から300文字程度)"
    )
    goal_s_psychological_action_plan_txt: str = Field(
        description="心理面での目標（障害受容、精神的支援など）に対する具体的な関わり方、声かけ、家族への説明内容などを記述(100文字から300文字程度)"
    )
    goal_s_3rd_party_action_plan_txt: str = Field(
        description="主介護者や家族の負担軽減、環境の変化に対する具体的な支援策や社会資源の活用提案などを記述(100文字から300文字程度)"
    )


# --- グループ化された生成のためのスキーマ定義 ---
class RisksAndPrecautions(BaseModel):
    main_risks_txt: str = RehabPlanSchema.model_fields['main_risks_txt']
    main_contraindications_txt: str = RehabPlanSchema.model_fields['main_contraindications_txt']


class FunctionalLimitations(BaseModel):
    func_pain_txt: str = RehabPlanSchema.model_fields['func_pain_txt']
    func_rom_limitation_txt: str = RehabPlanSchema.model_fields['func_rom_limitation_txt']
    func_muscle_weakness_txt: str = RehabPlanSchema.model_fields['func_muscle_weakness_txt']
    func_swallowing_disorder_txt: str = RehabPlanSchema.model_fields['func_swallowing_disorder_txt']
    func_behavioral_psychiatric_disorder_txt: str = RehabPlanSchema.model_fields['func_behavioral_psychiatric_disorder_txt']
    func_nutritional_disorder_txt: str = RehabPlanSchema.model_fields['func_nutritional_disorder_txt']
    func_excretory_disorder_txt: str = RehabPlanSchema.model_fields['func_excretory_disorder_txt']
    func_pressure_ulcer_txt: str = RehabPlanSchema.model_fields['func_pressure_ulcer_txt']
    func_contracture_deformity_txt: str = RehabPlanSchema.model_fields['func_contracture_deformity_txt']
    func_motor_muscle_tone_abnormality_txt: str = RehabPlanSchema.model_fields['func_motor_muscle_tone_abnormality_txt']
    func_disorientation_txt: str = RehabPlanSchema.model_fields['func_disorientation_txt']
    func_memory_disorder_txt: str = RehabPlanSchema.model_fields['func_memory_disorder_txt']

class Goals(BaseModel):
    goals_1_month_txt: str = RehabPlanSchema.model_fields['goals_1_month_txt']
    goals_at_discharge_txt: str = RehabPlanSchema.model_fields['goals_at_discharge_txt']

class TreatmentPolicy(BaseModel):
    policy_treatment_txt: str = RehabPlanSchema.model_fields['policy_treatment_txt']
    policy_content_txt: str = RehabPlanSchema.model_fields['policy_content_txt']
    adl_equipment_and_assistance_details_txt: str = RehabPlanSchema.model_fields['adl_equipment_and_assistance_details_txt']

class ActionPlans(BaseModel):
    goal_a_action_plan_txt: str = RehabPlanSchema.model_fields['goal_a_action_plan_txt']
    goal_s_env_action_plan_txt: str = RehabPlanSchema.model_fields['goal_s_env_action_plan_txt']
    goal_p_action_plan_txt: str = RehabPlanSchema.model_fields['goal_p_action_plan_txt']
    goal_s_psychological_action_plan_txt: str = RehabPlanSchema.model_fields['goal_s_psychological_action_plan_txt']
    goal_s_3rd_party_action_plan_txt: str = RehabPlanSchema.model_fields['goal_s_3rd_party_action_plan_txt']

class CurrentAssessment(RisksAndPrecautions, FunctionalLimitations):
    """患者の現状評価（リスク、禁忌、機能障害）をまとめて生成するためのスキーマ"""
    pass

class ComprehensiveTreatmentPlan(TreatmentPolicy, ActionPlans):
    """目標達成のための包括的な治療計画（全体方針、ADL詳細、個別計画）をまとめて生成するためのスキーマ"""
    pass

# 生成をグループ単位で行うためのリスト
GENERATION_GROUPS = [
    CurrentAssessment,          # ステップ1: 現状評価（リスク、禁忌、機能障害）
    Goals,                      # ステップ2: 目標設定
    ComprehensiveTreatmentPlan, # ステップ3: 包括的な治療計画
]