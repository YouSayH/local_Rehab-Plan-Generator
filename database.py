import os
from datetime import date, datetime
from dotenv import load_dotenv

from sqlalchemy import create_engine, Column, Integer, String, Date, Text, Boolean, ForeignKey, DECIMAL, TIMESTAMP, Table
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

# データベース接続URLを作成
# "mysql+pymysql" の部分で、SQLAlchemyが内部的にPyMySQLを使うことを指定
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

# SQLAlchemyのエンジンを作成
engine = create_engine(DATABASE_URL, echo=False)

# セッションを作成するためのクラス（ファクトリ）を定義
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルクラスが継承するための基本クラスを作成
Base = declarative_base()


# モデル定義
# staffとpatientsの中間テーブル（多対多）をモデルクラスを介さずに定義
staff_patients_association = Table(
    "staff_patients",
    Base.metadata,
    Column("staff_id", Integer, ForeignKey("staff.id"), primary_key=True),
    Column("patient_id", Integer, ForeignKey("patients.patient_id"), primary_key=True),
)


class Patient(Base):
    __tablename__ = "patients"
    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    date_of_birth = Column(Date)
    gender = Column(String(10))
    created_at = Column(TIMESTAMP)

    # PatientからRehabilitationPlanを 'plans' という名前で参照
    plans = relationship("RehabilitationPlan", back_populates="patient", cascade="all, delete-orphan")
    # Patientから担当のStaffを 'staff_members' という名前で参照
    staff_members = relationship("Staff", secondary=staff_patients_association, back_populates="assigned_patients")

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )


class Staff(Base):
    __tablename__ = "staff"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="general")
    created_at = Column(TIMESTAMP)

    # Staffから担当のPatientを 'assigned_patients' という名前で参照
    assigned_patients = relationship("Patient", secondary=staff_patients_association, back_populates="staff_members")


class RehabilitationPlan(Base):
    __tablename__ = "rehabilitation_plans"
    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)
    created_by_staff_id = Column(Integer, ForeignKey("staff.id"))
    created_at = Column(TIMESTAMP)

    patient = relationship("Patient", back_populates="plans")

    # schema.sql に基づく全カラム定義
    # 【1枚目】
    header_evaluation_date = Column(Date)
    header_disease_name_txt = Column(Text)
    header_treatment_details_txt = Column(Text)
    header_onset_date = Column(Date)
    header_rehab_start_date = Column(Date)
    header_therapy_pt_chk = Column(Boolean, default=False)
    header_therapy_ot_chk = Column(Boolean, default=False)
    header_therapy_st_chk = Column(Boolean, default=False)
    main_comorbidities_txt = Column(Text)
    main_risks_txt = Column(Text)
    main_contraindications_txt = Column(Text)
    func_consciousness_disorder_chk = Column(Boolean, default=False)
    func_consciousness_disorder_jcs_gcs_txt = Column(String(255))
    func_respiratory_disorder_chk = Column(Boolean, default=False)
    func_respiratory_o2_therapy_chk = Column(Boolean, default=False)
    func_respiratory_o2_therapy_l_min_txt = Column(String(255))
    func_respiratory_tracheostomy_chk = Column(Boolean, default=False)
    func_respiratory_ventilator_chk = Column(Boolean, default=False)
    func_circulatory_disorder_chk = Column(Boolean, default=False)
    func_circulatory_ef_chk = Column(Boolean, default=False)
    func_circulatory_ef_val = Column(Integer)
    func_circulatory_arrhythmia_chk = Column(Boolean, default=False)
    func_circulatory_arrhythmia_status_slct = Column(String(50))
    func_risk_factors_chk = Column(Boolean, default=False)
    func_risk_hypertension_chk = Column(Boolean, default=False)
    func_risk_dyslipidemia_chk = Column(Boolean, default=False)
    func_risk_diabetes_chk = Column(Boolean, default=False)
    func_risk_smoking_chk = Column(Boolean, default=False)
    func_risk_obesity_chk = Column(Boolean, default=False)
    func_risk_hyperuricemia_chk = Column(Boolean, default=False)
    func_risk_ckd_chk = Column(Boolean, default=False)
    func_risk_family_history_chk = Column(Boolean, default=False)
    func_risk_angina_chk = Column(Boolean, default=False)
    func_risk_omi_chk = Column(Boolean, default=False)
    func_risk_other_chk = Column(Boolean, default=False)
    func_risk_other_txt = Column(Text)
    func_swallowing_disorder_chk = Column(Boolean, default=False)
    func_swallowing_disorder_txt = Column(Text)
    func_nutritional_disorder_chk = Column(Boolean, default=False)
    func_nutritional_disorder_txt = Column(Text)
    func_excretory_disorder_chk = Column(Boolean, default=False)
    func_excretory_disorder_txt = Column(Text)
    func_pressure_ulcer_chk = Column(Boolean, default=False)
    func_pressure_ulcer_txt = Column(Text)
    func_pain_chk = Column(Boolean, default=False)
    func_pain_txt = Column(Text)
    func_other_chk = Column(Boolean, default=False)
    func_other_txt = Column(Text)
    func_rom_limitation_chk = Column(Boolean, default=False)
    func_rom_limitation_txt = Column(Text)
    func_contracture_deformity_chk = Column(Boolean, default=False)
    func_contracture_deformity_txt = Column(Text)
    func_muscle_weakness_chk = Column(Boolean, default=False)
    func_muscle_weakness_txt = Column(Text)
    func_motor_dysfunction_chk = Column(Boolean, default=False)
    func_motor_paralysis_chk = Column(Boolean, default=False)
    func_motor_involuntary_movement_chk = Column(Boolean, default=False)
    func_motor_ataxia_chk = Column(Boolean, default=False)
    func_motor_parkinsonism_chk = Column(Boolean, default=False)
    func_motor_muscle_tone_abnormality_chk = Column(Boolean, default=False)
    func_motor_muscle_tone_abnormality_txt = Column(Text)
    func_sensory_dysfunction_chk = Column(Boolean, default=False)
    func_sensory_hearing_chk = Column(Boolean, default=False)
    func_sensory_vision_chk = Column(Boolean, default=False)
    func_sensory_superficial_chk = Column(Boolean, default=False)
    func_sensory_deep_chk = Column(Boolean, default=False)
    func_speech_disorder_chk = Column(Boolean, default=False)
    func_speech_articulation_chk = Column(Boolean, default=False)
    func_speech_aphasia_chk = Column(Boolean, default=False)
    func_speech_stuttering_chk = Column(Boolean, default=False)
    func_speech_other_chk = Column(Boolean, default=False)
    func_speech_other_txt = Column(Text)
    func_higher_brain_dysfunction_chk = Column(Boolean, default=False)
    func_higher_brain_memory_chk = Column(Boolean, default=False)
    func_higher_brain_attention_chk = Column(Boolean, default=False)
    func_higher_brain_apraxia_chk = Column(Boolean, default=False)
    func_higher_brain_agnosia_chk = Column(Boolean, default=False)
    func_higher_brain_executive_chk = Column(Boolean, default=False)
    func_behavioral_psychiatric_disorder_chk = Column(Boolean, default=False)
    func_behavioral_psychiatric_disorder_txt = Column(Text)
    func_disorientation_chk = Column(Boolean, default=False)
    func_disorientation_txt = Column(Text)
    func_memory_disorder_chk = Column(Boolean, default=False)
    func_memory_disorder_txt = Column(Text)
    func_developmental_disorder_chk = Column(Boolean, default=False)
    func_developmental_asd_chk = Column(Boolean, default=False)
    func_developmental_ld_chk = Column(Boolean, default=False)
    func_developmental_adhd_chk = Column(Boolean, default=False)
    func_basic_rolling_chk = Column(Boolean, default=False)
    func_basic_rolling_independent_chk = Column(Boolean, default=False)
    func_basic_rolling_partial_assistance_chk = Column(Boolean, default=False)
    func_basic_rolling_assistance_chk = Column(Boolean, default=False)
    func_basic_rolling_not_performed_chk = Column(Boolean, default=False)
    func_basic_getting_up_chk = Column(Boolean, default=False)
    func_basic_getting_up_independent_chk = Column(Boolean, default=False)
    func_basic_getting_up_partial_assistance_chk = Column(Boolean, default=False)
    func_basic_getting_up_assistance_chk = Column(Boolean, default=False)
    func_basic_getting_up_not_performed_chk = Column(Boolean, default=False)
    func_basic_standing_up_chk = Column(Boolean, default=False)
    func_basic_standing_up_independent_chk = Column(Boolean, default=False)
    func_basic_standing_up_partial_assistance_chk = Column(Boolean, default=False)
    func_basic_standing_up_assistance_chk = Column(Boolean, default=False)
    func_basic_standing_up_not_performed_chk = Column(Boolean, default=False)
    func_basic_sitting_balance_chk = Column(Boolean, default=False)
    func_basic_sitting_balance_independent_chk = Column(Boolean, default=False)
    func_basic_sitting_balance_partial_assistance_chk = Column(Boolean, default=False)
    func_basic_sitting_balance_assistance_chk = Column(Boolean, default=False)
    func_basic_sitting_balance_not_performed_chk = Column(Boolean, default=False)
    func_basic_standing_balance_chk = Column(Boolean, default=False)
    func_basic_standing_balance_independent_chk = Column(Boolean, default=False)
    func_basic_standing_balance_partial_assistance_chk = Column(Boolean, default=False)
    func_basic_standing_balance_assistance_chk = Column(Boolean, default=False)
    func_basic_standing_balance_not_performed_chk = Column(Boolean, default=False)
    func_basic_other_chk = Column(Boolean, default=False)
    func_basic_other_txt = Column(Text)
    adl_eating_fim_start_val = Column(Integer)
    adl_eating_fim_current_val = Column(Integer)
    adl_eating_bi_start_val = Column(Integer)
    adl_eating_bi_current_val = Column(Integer)
    adl_grooming_fim_start_val = Column(Integer)
    adl_grooming_fim_current_val = Column(Integer)
    adl_grooming_bi_start_val = Column(Integer)
    adl_grooming_bi_current_val = Column(Integer)
    adl_bathing_fim_start_val = Column(Integer)
    adl_bathing_fim_current_val = Column(Integer)
    adl_bathing_bi_start_val = Column(Integer)
    adl_bathing_bi_current_val = Column(Integer)
    adl_dressing_upper_fim_start_val = Column(Integer)
    adl_dressing_upper_fim_current_val = Column(Integer)
    adl_dressing_lower_fim_start_val = Column(Integer)
    adl_dressing_lower_fim_current_val = Column(Integer)
    adl_dressing_bi_start_val = Column(Integer)
    adl_dressing_bi_current_val = Column(Integer)
    adl_toileting_fim_start_val = Column(Integer)
    adl_toileting_fim_current_val = Column(Integer)
    adl_toileting_bi_start_val = Column(Integer)
    adl_toileting_bi_current_val = Column(Integer)
    adl_bladder_management_fim_start_val = Column(Integer)
    adl_bladder_management_fim_current_val = Column(Integer)
    adl_bladder_management_bi_start_val = Column(Integer)
    adl_bladder_management_bi_current_val = Column(Integer)
    adl_bowel_management_fim_start_val = Column(Integer)
    adl_bowel_management_fim_current_val = Column(Integer)
    adl_bowel_management_bi_start_val = Column(Integer)
    adl_bowel_management_bi_current_val = Column(Integer)
    adl_transfer_bed_chair_wc_fim_start_val = Column(Integer)
    adl_transfer_bed_chair_wc_fim_current_val = Column(Integer)
    adl_transfer_toilet_fim_start_val = Column(Integer)
    adl_transfer_toilet_fim_current_val = Column(Integer)
    adl_transfer_tub_shower_fim_start_val = Column(Integer)
    adl_transfer_tub_shower_fim_current_val = Column(Integer)
    adl_transfer_bi_start_val = Column(Integer)
    adl_transfer_bi_current_val = Column(Integer)
    adl_locomotion_walk_walkingAids_wc_fim_start_val = Column(Integer)
    adl_locomotion_walk_walkingAids_wc_fim_current_val = Column(Integer)
    adl_locomotion_walk_walkingAids_wc_bi_start_val = Column(Integer)
    adl_locomotion_walk_walkingAids_wc_bi_current_val = Column(Integer)
    adl_locomotion_stairs_fim_start_val = Column(Integer)
    adl_locomotion_stairs_fim_current_val = Column(Integer)
    adl_locomotion_stairs_bi_start_val = Column(Integer)
    adl_locomotion_stairs_bi_current_val = Column(Integer)
    adl_comprehension_fim_start_val = Column(Integer)
    adl_comprehension_fim_current_val = Column(Integer)
    adl_expression_fim_start_val = Column(Integer)
    adl_expression_fim_current_val = Column(Integer)
    adl_social_interaction_fim_start_val = Column(Integer)
    adl_social_interaction_fim_current_val = Column(Integer)
    adl_problem_solving_fim_start_val = Column(Integer)
    adl_problem_solving_fim_current_val = Column(Integer)
    adl_memory_fim_start_val = Column(Integer)
    adl_memory_fim_current_val = Column(Integer)
    adl_equipment_and_assistance_details_txt = Column(Text)
    nutrition_height_chk = Column(Boolean, default=False)
    nutrition_height_val = Column(DECIMAL(5, 1))
    nutrition_weight_chk = Column(Boolean, default=False)
    nutrition_weight_val = Column(DECIMAL(5, 1))
    nutrition_bmi_chk = Column(Boolean, default=False)
    nutrition_bmi_val = Column(DECIMAL(4, 1))
    nutrition_method_oral_chk = Column(Boolean, default=False)
    nutrition_method_oral_meal_chk = Column(Boolean, default=False)
    nutrition_method_oral_supplement_chk = Column(Boolean, default=False)
    nutrition_method_tube_chk = Column(Boolean, default=False)
    nutrition_method_iv_chk = Column(Boolean, default=False)
    nutrition_method_iv_peripheral_chk = Column(Boolean, default=False)
    nutrition_method_iv_central_chk = Column(Boolean, default=False)
    nutrition_method_peg_chk = Column(Boolean, default=False)
    nutrition_swallowing_diet_slct = Column(String(50))
    nutrition_swallowing_diet_code_txt = Column(String(255))
    nutrition_status_assessment_slct = Column(String(50))
    nutrition_status_assessment_other_txt = Column(Text)
    nutrition_required_energy_val = Column(Integer)
    nutrition_required_protein_val = Column(Integer)
    nutrition_total_intake_energy_val = Column(Integer)
    nutrition_total_intake_protein_val = Column(Integer)
    social_care_level_status_chk = Column(Boolean, default=False)
    social_care_level_applying_chk = Column(Boolean, default=False)
    social_care_level_support_chk = Column(Boolean, default=False)
    social_care_level_support_num1_slct = Column(Boolean, default=False)
    social_care_level_support_num2_slct = Column(Boolean, default=False)
    social_care_level_care_slct = Column(Boolean, default=False)
    social_care_level_care_num1_slct = Column(Boolean, default=False)
    social_care_level_care_num2_slct = Column(Boolean, default=False)
    social_care_level_care_num3_slct = Column(Boolean, default=False)
    social_care_level_care_num4_slct = Column(Boolean, default=False)
    social_care_level_care_num5_slct = Column(Boolean, default=False)
    social_disability_certificate_physical_chk = Column(Boolean, default=False)
    social_disability_certificate_physical_txt = Column(Text)
    social_disability_certificate_physical_type_txt = Column(String(255))
    social_disability_certificate_physical_rank_val = Column(Integer)
    social_disability_certificate_mental_chk = Column(Boolean, default=False)
    social_disability_certificate_mental_rank_val = Column(Integer)
    social_disability_certificate_intellectual_chk = Column(Boolean, default=False)
    social_disability_certificate_intellectual_txt = Column(Text)
    social_disability_certificate_intellectual_grade_txt = Column(String(255))
    social_disability_certificate_other_chk = Column(Boolean, default=False)
    social_disability_certificate_other_txt = Column(Text)
    goals_1_month_txt = Column(Text)
    goals_at_discharge_txt = Column(Text)
    goals_planned_hospitalization_period_chk = Column(Boolean, default=False)
    goals_planned_hospitalization_period_txt = Column(Text)
    goals_discharge_destination_chk = Column(Boolean, default=False)
    goals_discharge_destination_txt = Column(Text)
    goals_long_term_care_needed_chk = Column(Boolean, default=False)
    policy_treatment_txt = Column(Text)
    policy_content_txt = Column(Text)
    signature_rehab_doctor_txt = Column(String(255))
    signature_primary_doctor_txt = Column(String(255))
    signature_pt_txt = Column(String(255))
    signature_ot_txt = Column(String(255))
    signature_st_txt = Column(String(255))
    signature_nurse_txt = Column(String(255))
    signature_dietitian_txt = Column(String(255))
    signature_social_worker_txt = Column(String(255))
    signature_explained_to_txt = Column(String(255))
    signature_explanation_date = Column(Date)
    signature_explainer_txt = Column(String(255))

    # 【2枚目】
    goal_p_residence_chk = Column(Boolean, default=False)
    goal_p_residence_slct = Column(String(50))
    goal_p_residence_other_txt = Column(Text)
    goal_p_return_to_work_chk = Column(Boolean, default=False)
    goal_p_return_to_work_status_slct = Column(String(50))
    goal_p_return_to_work_status_other_txt = Column(Text)
    goal_p_return_to_work_commute_change_chk = Column(Boolean, default=False)
    goal_p_schooling_chk = Column(Boolean, default=False)
    goal_p_schooling_status_possible_chk = Column(Boolean, default=False)
    goal_p_schooling_status_needs_consideration_chk = Column(Boolean, default=False)
    goal_p_schooling_status_change_course_chk = Column(Boolean, default=False)
    goal_p_schooling_status_not_possible_chk = Column(Boolean, default=False)
    goal_p_schooling_status_other_chk = Column(Boolean, default=False)
    goal_p_schooling_status_other_txt = Column(Text)
    goal_p_schooling_destination_chk = Column(Boolean, default=False)
    goal_p_schooling_destination_txt = Column(Text)
    goal_p_schooling_commute_change_chk = Column(Boolean, default=False)
    goal_p_schooling_commute_change_txt = Column(Text)
    goal_p_household_role_chk = Column(Boolean, default=False)
    goal_p_household_role_txt = Column(Text)
    goal_p_social_activity_chk = Column(Boolean, default=False)
    goal_p_social_activity_txt = Column(Text)
    goal_p_hobby_chk = Column(Boolean, default=False)
    goal_p_hobby_txt = Column(Text)
    goal_a_bed_mobility_chk = Column(Boolean, default=False)
    goal_a_bed_mobility_independent_chk = Column(Boolean, default=False)
    goal_a_bed_mobility_assistance_chk = Column(Boolean, default=False)
    goal_a_bed_mobility_not_performed_chk = Column(Boolean, default=False)
    goal_a_bed_mobility_equipment_chk = Column(Boolean, default=False)
    goal_a_bed_mobility_environment_setup_chk = Column(Boolean, default=False)
    goal_a_indoor_mobility_chk = Column(Boolean, default=False)
    goal_a_indoor_mobility_independent_chk = Column(Boolean, default=False)
    goal_a_indoor_mobility_assistance_chk = Column(Boolean, default=False)
    goal_a_indoor_mobility_not_performed_chk = Column(Boolean, default=False)
    goal_a_indoor_mobility_equipment_chk = Column(Boolean, default=False)
    goal_a_indoor_mobility_equipment_txt = Column(Text)
    goal_a_outdoor_mobility_chk = Column(Boolean, default=False)
    goal_a_outdoor_mobility_independent_chk = Column(Boolean, default=False)
    goal_a_outdoor_mobility_assistance_chk = Column(Boolean, default=False)
    goal_a_outdoor_mobility_not_performed_chk = Column(Boolean, default=False)
    goal_a_outdoor_mobility_equipment_chk = Column(Boolean, default=False)
    goal_a_outdoor_mobility_equipment_txt = Column(Text)
    goal_a_driving_chk = Column(Boolean, default=False)
    goal_a_driving_independent_chk = Column(Boolean, default=False)
    goal_a_driving_assistance_chk = Column(Boolean, default=False)
    goal_a_driving_not_performed_chk = Column(Boolean, default=False)
    goal_a_driving_modification_chk = Column(Boolean, default=False)
    goal_a_driving_modification_txt = Column(Text)
    goal_a_public_transport_chk = Column(Boolean, default=False)
    goal_a_public_transport_independent_chk = Column(Boolean, default=False)
    goal_a_public_transport_assistance_chk = Column(Boolean, default=False)
    goal_a_public_transport_not_performed_chk = Column(Boolean, default=False)
    goal_a_public_transport_type_chk = Column(Boolean, default=False)
    goal_a_public_transport_type_txt = Column(Text)
    goal_a_toileting_chk = Column(Boolean, default=False)
    goal_a_toileting_independent_chk = Column(Boolean, default=False)
    goal_a_toileting_assistance_chk = Column(Boolean, default=False)
    goal_a_toileting_assistance_clothing_chk = Column(Boolean, default=False)
    goal_a_toileting_assistance_wiping_chk = Column(Boolean, default=False)
    goal_a_toileting_assistance_catheter_chk = Column(Boolean, default=False)
    goal_a_toileting_type_chk = Column(Boolean, default=False)
    goal_a_toileting_type_western_chk = Column(Boolean, default=False)
    goal_a_toileting_type_japanese_chk = Column(Boolean, default=False)
    goal_a_toileting_type_other_chk = Column(Boolean, default=False)
    goal_a_toileting_type_other_txt = Column(Text)
    goal_a_eating_chk = Column(Boolean, default=False)
    goal_a_eating_independent_chk = Column(Boolean, default=False)
    goal_a_eating_assistance_chk = Column(Boolean, default=False)
    goal_a_eating_not_performed_chk = Column(Boolean, default=False)
    goal_a_eating_method_chopsticks_chk = Column(Boolean, default=False)
    goal_a_eating_method_fork_etc_chk = Column(Boolean, default=False)
    goal_a_eating_method_tube_feeding_chk = Column(Boolean, default=False)
    goal_a_eating_diet_form_txt = Column(Text)
    goal_a_grooming_chk = Column(Boolean, default=False)
    goal_a_grooming_independent_chk = Column(Boolean, default=False)
    goal_a_grooming_assistance_chk = Column(Boolean, default=False)
    goal_a_dressing_chk = Column(Boolean, default=False)
    goal_a_dressing_independent_chk = Column(Boolean, default=False)
    goal_a_dressing_assistance_chk = Column(Boolean, default=False)
    goal_a_bathing_chk = Column(Boolean, default=False)
    goal_a_bathing_independent_chk = Column(Boolean, default=False)
    goal_a_bathing_assistance_chk = Column(Boolean, default=False)
    goal_a_bathing_type_tub_chk = Column(Boolean, default=False)
    goal_a_bathing_type_shower_chk = Column(Boolean, default=False)
    goal_a_bathing_assistance_body_washing_chk = Column(Boolean, default=False)
    goal_a_bathing_assistance_transfer_chk = Column(Boolean, default=False)
    goal_a_housework_meal_chk = Column(Boolean, default=False)
    goal_a_housework_meal_all_chk = Column(Boolean, default=False)
    goal_a_housework_meal_not_performed_chk = Column(Boolean, default=False)
    goal_a_housework_meal_partial_chk = Column(Boolean, default=False)
    goal_a_housework_meal_partial_txt = Column(Text)
    goal_a_writing_chk = Column(Boolean, default=False)
    goal_a_writing_independent_chk = Column(Boolean, default=False)
    goal_a_writing_independent_after_hand_change_chk = Column(Boolean, default=False)
    goal_a_writing_other_chk = Column(Boolean, default=False)
    goal_a_writing_other_txt = Column(Text)
    goal_a_ict_chk = Column(Boolean, default=False)
    goal_a_ict_independent_chk = Column(Boolean, default=False)
    goal_a_ict_assistance_chk = Column(Boolean, default=False)
    goal_a_communication_chk = Column(Boolean, default=False)
    goal_a_communication_independent_chk = Column(Boolean, default=False)
    goal_a_communication_assistance_chk = Column(Boolean, default=False)
    goal_a_communication_device_chk = Column(Boolean, default=False)
    goal_a_communication_letter_board_chk = Column(Boolean, default=False)
    goal_a_communication_cooperation_chk = Column(Boolean, default=False)
    goal_s_psychological_support_chk = Column(Boolean, default=False)
    goal_s_psychological_support_txt = Column(Text)
    goal_s_disability_acceptance_chk = Column(Boolean, default=False)
    goal_s_disability_acceptance_txt = Column(Text)
    goal_s_psychological_other_chk = Column(Boolean, default=False)
    goal_s_psychological_other_txt = Column(Text)
    goal_s_env_home_modification_chk = Column(Boolean, default=False)
    goal_s_env_home_modification_txt = Column(Text)
    goal_s_env_assistive_device_chk = Column(Boolean, default=False)
    goal_s_env_assistive_device_txt = Column(Text)
    goal_s_env_social_security_chk = Column(Boolean, default=False)
    goal_s_env_social_security_physical_disability_cert_chk = Column(Boolean, default=False)
    goal_s_env_social_security_disability_pension_chk = Column(Boolean, default=False)
    goal_s_env_social_security_intractable_disease_cert_chk = Column(Boolean, default=False)
    goal_s_env_social_security_other_chk = Column(Boolean, default=False)
    goal_s_env_social_security_other_txt = Column(Text)
    goal_s_env_care_insurance_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_details_txt = Column(Text)
    goal_s_env_care_insurance_outpatient_rehab_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_home_rehab_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_day_care_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_home_nursing_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_home_care_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_health_facility_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_nursing_home_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_care_hospital_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_other_chk = Column(Boolean, default=False)
    goal_s_env_care_insurance_other_txt = Column(Text)
    goal_s_env_disability_welfare_chk = Column(Boolean, default=False)
    goal_s_env_disability_welfare_after_school_day_service_chk = Column(Boolean, default=False)
    goal_s_env_disability_welfare_child_development_support_chk = Column(Boolean, default=False)
    goal_s_env_disability_welfare_life_care_chk = Column(Boolean, default=False)
    goal_s_env_disability_welfare_other_chk = Column(Boolean, default=False)
    goal_s_env_other_chk = Column(Boolean, default=False)
    goal_s_env_other_txt = Column(Text)
    goal_s_3rd_party_main_caregiver_chk = Column(Boolean, default=False)
    goal_s_3rd_party_main_caregiver_txt = Column(Text)
    goal_s_3rd_party_family_structure_change_chk = Column(Boolean, default=False)
    goal_s_3rd_party_family_structure_change_txt = Column(Text)
    goal_s_3rd_party_household_role_change_chk = Column(Boolean, default=False)
    goal_s_3rd_party_household_role_change_txt = Column(Text)
    goal_s_3rd_party_family_activity_change_chk = Column(Boolean, default=False)
    goal_s_3rd_party_family_activity_change_txt = Column(Text)
    goal_p_action_plan_txt = Column(Text)
    goal_a_action_plan_txt = Column(Text)
    goal_s_psychological_action_plan_txt = Column(Text)
    goal_s_env_action_plan_txt = Column(Text)
    goal_s_3rd_party_action_plan_txt = Column(Text)


# データ操作関数
def get_patient_data_for_plan(patient_id: int):
    """【SQLAlchemy版】患者の基本情報と最新の計画書データを取得する"""
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if not patient:
            return None

        # 患者の基本情報を辞書に変換
        patient_data = {c.name: getattr(patient, c.name) for c in patient.__table__.columns}
        patient_data["age"] = patient.age

        # 最新の計画を取得
        latest_plan = (
            db.query(RehabilitationPlan)
            .filter(RehabilitationPlan.patient_id == patient_id)
            .order_by(RehabilitationPlan.created_at.desc())
            .first()
        )

        if latest_plan:
            # 計画データを辞書に変換してマージ
            plan_data = {c.name: getattr(latest_plan, c.name) for c in latest_plan.__table__.columns}
            patient_data.update(plan_data)

        return patient_data
    finally:
        db.close()


def save_patient_master_data(form_data: dict):
    """
    患者の事実情報（マスターデータ）を保存する。
    patient_idが存在すれば更新、なければ新規作成する。
    計画書は常に最新の1件を更新する（履歴は作成しない）←今後履歴を確認できるようにしたい。
    """
    db = SessionLocal()
    try:
        patient_id_str = form_data.get("patient_id")
        patient = None

        # 1. 患者オブジェクトの特定（既存 or 新規）
        if patient_id_str:
            patient_id = int(patient_id_str)
            patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
            if not patient:
                raise Exception(f"更新対象の患者ID: {patient_id} が見つかりません。")
        else:
            patient = Patient()
            # db.add(patient)　ここでは実行しない。id関係

        # 2. 患者基本情報の更新 (Patientテーブル)
        patient.name = form_data.get("name")
        patient.gender = form_data.get("gender")
        # 年齢から生年月日を簡易的に計算（本来は生年月日を直接入力すべき）
        if form_data.get("age"):
            try:
                birth_year = date.today().year - int(form_data.get("age"))
                patient.date_of_birth = date(birth_year, 1, 1)
            except (ValueError, TypeError):
                # 年齢が不正な値の場合は何もしない
                pass
        if not patient_id_str:
            db.add(patient)

        # 新規患者の場合はここで一度コミットして patient_id を確定させる
        # 既存患者の場合も、名前などの変更をこの時点でコミットする
        db.commit()
        # 確定したpatient_idを取得
        saved_patient_id = patient.patient_id

        # 3. 最新の計画書レコードの特定（既存 or 新規）
        latest_plan = (
            db.query(RehabilitationPlan)
            .filter(RehabilitationPlan.patient_id == saved_patient_id)
            .order_by(RehabilitationPlan.created_at.desc())
            .first()
        )

        if not latest_plan:
            # この患者にとって初めてのレコード作成
            latest_plan = RehabilitationPlan(patient_id=saved_patient_id)
            db.add(latest_plan)

        # チェックボックスの値をリセット
        columns = RehabilitationPlan.__table__.columns
        for col in columns:
            if isinstance(col.type, Boolean):
                setattr(latest_plan, col.name, False)

        # RehabilitationPlanテーブルの情報を更新
        processed_dates = set()

        for key, value in form_data.items():
            if key in ["plan_id", "patient_id", "name", "age", "gender"]:
                continue

            # 日付フィールドの結合処理
            if key.endswith(("_year", "_month", "_day")):
                base_key = key.rsplit("_", 1)[0]
                if base_key in processed_dates:
                    continue
                processed_dates.add(base_key)

                year = form_data.get(f"{base_key}_year")
                month = form_data.get(f"{base_key}_month")
                day = form_data.get(f"{base_key}_day")

                date_value = None
                if year and month and day:
                    try:
                        date_value = date(int(year), int(month), int(day))
                    except (ValueError, TypeError):
                        print(f"   [警告] 無効な日付: {base_key} -> {year}-{month}-{day}")

                # base_keyがRehabilitationPlanの属性であることを確認してから設定
                if hasattr(latest_plan, base_key):
                    setattr(latest_plan, base_key, date_value)

                continue

            if key in columns:
                column_type = columns[key].type
                processed_value = None

                if isinstance(column_type, Boolean):
                    processed_value = key in form_data
                elif value is not None and value != "":
                    try:
                        if isinstance(column_type, Integer):
                            processed_value = int(value)
                        elif isinstance(column_type, DECIMAL):
                            processed_value = float(value)
                        elif isinstance(column_type, Date):
                            processed_value = datetime.strptime(value, "%Y-%m-%d").date()
                        else:
                            processed_value = str(value)
                    except (ValueError, TypeError) as e:
                        print(f"   [警告] 型変換エラー: key='{key}', value='{value}', error='{e}'")
                        processed_value = None

                setattr(latest_plan, key, processed_value)

        # 最後に計画書の変更をコミット
        db.commit()

        return saved_patient_id

    except Exception as e:
        db.rollback()
        print(f"   [エラー] データベース保存中にエラーが発生しました: {e}")
        raise
    finally:
        db.close()


def save_new_plan(patient_id: int, staff_id: int, form_data: dict):
    """
    【最終修正版】
    Webフォームからのデータで新しい計画書を保存する。
    plan_idを無視し、各値を正しい型に変換して堅牢に保存する。
    """
    db = SessionLocal()
    try:
        # 新しい計画書オブジェクトを作成
        new_plan = RehabilitationPlan(
            patient_id=patient_id,
            created_by_staff_id=staff_id,
            created_at=datetime.now(),  # 現在時刻を記録
        )

        # RehabilitationPlanモデルの全てのカラム定義を取得
        columns = RehabilitationPlan.__table__.columns

        # フォームから送られてきたデータ（form_data）をループ
        for key, value in form_data.items():
            # plan_idやpatient_idなど、自動設定されるキーはスキップ
            if key in ["plan_id", "patient_id", "created_by_staff_id", "created_at"]:
                continue

            # フォームのキーがモデルのカラムに存在する場合のみ処理
            if key in columns:
                column_type = columns[key].type

                # 値を適切な型に変換
                processed_value = None
                if value is not None and value != "":
                    try:
                        if isinstance(column_type, Boolean):
                            processed_value = str(value).lower() in ["true", "on", "1"]
                        elif isinstance(column_type, Integer):
                            processed_value = int(value)
                        elif isinstance(column_type, DECIMAL):
                            processed_value = float(value)
                        elif isinstance(column_type, Date):
                            processed_value = datetime.strptime(value, "%Y-%m-%d").date()
                        else:  # String, Text
                            processed_value = str(value)  # 明示的に文字列に変換
                    except (ValueError, TypeError) as e:
                        print(f"   [警告] 型変換エラー: key='{key}', value='{value}', error='{e}'")
                        processed_value = None

                # 変換した値をオブジェクトに設定
                setattr(new_plan, key, processed_value)

        db.add(new_plan)
        db.commit()
        print("   [成功] 新しい計画書データをデータベースに保存しました。")
    except Exception as e:
        db.rollback()
        print(f"   [エラー] データベース保存中にエラーが発生しました: {e}")
        raise  # エラーを呼び出し元に通知
    finally:
        db.close()


def get_staff_by_username(username: str):
    db = SessionLocal()
    try:
        staff = db.query(Staff).filter(Staff.username == username).first()
        if staff:
            return {c.name: getattr(staff, c.name) for c in staff.__table__.columns}
        return None
    finally:
        db.close()


def get_staff_by_id(staff_id: int):
    db = SessionLocal()
    try:
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        if staff:
            return {c.name: getattr(staff, c.name) for c in staff.__table__.columns}
        return None
    finally:
        db.close()


def create_staff(username: str, hashed_password: str, role: str = "general"):
    db = SessionLocal()
    try:
        new_staff = Staff(username=username, password=hashed_password, role=role)
        db.add(new_staff)
        db.commit()
    finally:
        db.close()


def get_assigned_patients(staff_id: int):
    db = SessionLocal()
    try:
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        if staff:
            return [{"id": p.patient_id, "name": p.name} for p in staff.assigned_patients]
        return []
    finally:
        db.close()


def assign_patient_to_staff(staff_id: int, patient_id: int):
    db = SessionLocal()
    try:
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if staff and patient:
            staff.assigned_patients.append(patient)
            db.commit()
    except IntegrityError:
        db.rollback()
        raise
    finally:
        db.close()


def unassign_patient_from_staff(staff_id: int, patient_id: int):
    db = SessionLocal()
    try:
        staff = db.query(Staff).filter(Staff.id == staff_id).first()
        patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
        if staff and patient and patient in staff.assigned_patients:
            staff.assigned_patients.remove(patient)
            db.commit()
    finally:
        db.close()


def get_all_staff():
    db = SessionLocal()
    try:
        staff_list = db.query(Staff.id, Staff.username, Staff.role).order_by(Staff.id).all()
        return [{"id": s.id, "username": s.username, "role": s.role} for s in staff_list]
    finally:
        db.close()


def get_all_patients():
    db = SessionLocal()
    try:
        patient_list = db.query(Patient.patient_id, Patient.name).order_by(Patient.patient_id).all()
        return [{"patient_id": p.patient_id, "name": p.name} for p in patient_list]
    finally:
        db.close()


def delete_staff_by_id(staff_id: int):
    db = SessionLocal()
    try:
        staff_to_delete = db.query(Staff).filter(Staff.id == staff_id).first()
        if staff_to_delete:
            db.delete(staff_to_delete)
            db.commit()
    finally:
        db.close()


def init_db():
    # モデルの定義をデータベースに反映（テーブル作成）
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print("データベースのテーブルを初期化（作成）します...")
    init_db()
    print("完了しました。")
