-- =================================================================
-- リハビリテーション総合実施計画書 自動作成システム用データベーススキーマ
-- =================================================================
-- TODO あくまでもテスト用に作ったものなので、作り直す必要があります。


-- 1. データベースの作成
CREATE DATABASE IF NOT EXISTS rehab_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE rehab_db;



-- 外部キー制約を一時的に無効化
SET FOREIGN_KEY_CHECKS = 0;

-- テーブルを削除
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS staff_patients;
DROP TABLE IF EXISTS rehabilitation_plans;
DROP TABLE IF EXISTS liked_item_details; 
DROP TABLE IF EXISTS regeneration_history;

-- 外部キー制約を再度有効化
SET FOREIGN_KEY_CHECKS = 1;


-- =================================================================
-- 2. 患者マスターテーブル
-- =================================================================
-- TODO 患者情報が少ないかも。今後増やしていこうと思う。
CREATE TABLE IF NOT EXISTS patients (
    `patient_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '患者を一意に識別するID',
    `name` VARCHAR(255) NOT NULL COMMENT '患者氏名',
    `date_of_birth` DATE NULL COMMENT '生年月日',
    `gender` VARCHAR(10) NULL COMMENT '性別 (例: 男, 女)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時'
) ENGINE = InnoDB COMMENT = '患者の基本情報を格納するマスターテーブル';




-- =================================================================
-- 3. 職員マスターテーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS staff (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '職員を一意に識別するID',
    `username` VARCHAR(255) NOT NULL UNIQUE COMMENT 'ログイン用のユーザー名',
    `password` VARCHAR(255) NOT NULL COMMENT 'ハッシュ化されたパスワード',
    `occupation` VARCHAR(255) NOT NULL COMMENT '職種',
    `role` VARCHAR(50) NOT NULL DEFAULT 'general' COMMENT '役割 (admin, generalなど)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時'
) ENGINE = InnoDB COMMENT = '職員（アプリのユーザー）情報を格納するテーブル';


-- =================================================================
-- 4. 職員と患者の関連テーブル (担当者機能のため追加)
-- =================================================================
CREATE TABLE IF NOT EXISTS staff_patients (
    `staff_id` INT NOT NULL COMMENT '外部キー (staffテーブルを参照)',
    `patient_id` INT NOT NULL COMMENT '外部キー (patientsテーブルを参照)',
    PRIMARY KEY (`staff_id`, `patient_id`),
    CONSTRAINT `fk_staff_id` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_staff_patient_id` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '職員と担当患者の関連を管理する中間テーブル';


-- =================================================================
-- 5. リハビリテーション計画書テーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS rehabilitation_plans (
    `plan_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '計画書を一意に識別するID',
    `patient_id` INT NOT NULL COMMENT '外部キー (patientsテーブルを参照)',
    `created_by_staff_id` INT NULL COMMENT '作成した職員のID (staffテーブル参照)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時',
    `liked_items_json` TEXT NULL COMMENT 'いいね情報のスナップショットをJSONで保存',

    -- 【1枚目】----------------------------------------------------
    -- ヘッダー・基本情報
    `header_evaluation_date` DATE NULL COMMENT '計画評価実施日',
    `header_disease_name_txt` TEXT NULL COMMENT '算定病名',
    `header_treatment_details_txt` TEXT NULL COMMENT '治療内容',
    `header_onset_date` DATE NULL COMMENT '発症日・手術日',
    `header_rehab_start_date` DATE NULL COMMENT 'リハ開始日',
    `header_therapy_pt_chk` BOOLEAN DEFAULT FALSE COMMENT '理学療法',
    `header_therapy_ot_chk` BOOLEAN DEFAULT FALSE COMMENT '作業療法',
    `header_therapy_st_chk` BOOLEAN DEFAULT FALSE COMMENT '言語療法',

    -- 併存疾患・リスク・特記事項 (AI生成 + ユーザー編集)
    `main_comorbidities_txt` TEXT NULL,
    `main_risks_txt` TEXT NULL,
    `main_contraindications_txt` TEXT NULL,

    -- 心身機能・構造
    `func_consciousness_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_consciousness_disorder_jcs_gcs_txt` VARCHAR(255) NULL,
    `func_respiratory_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_respiratory_o2_therapy_chk` BOOLEAN DEFAULT FALSE,
    `func_respiratory_o2_therapy_l_min_txt` VARCHAR(255) NULL,
    `func_respiratory_tracheostomy_chk` BOOLEAN DEFAULT FALSE,
    `func_respiratory_ventilator_chk` BOOLEAN DEFAULT FALSE,
    `func_circulatory_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_circulatory_ef_chk` BOOLEAN DEFAULT FALSE,
    `func_circulatory_ef_val` INT NULL,
    `func_circulatory_arrhythmia_chk` BOOLEAN DEFAULT FALSE,
    `func_circulatory_arrhythmia_status_slct` VARCHAR(50) NULL,
    `func_risk_factors_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_hypertension_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_dyslipidemia_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_diabetes_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_smoking_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_obesity_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_hyperuricemia_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_ckd_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_family_history_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_angina_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_omi_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_other_chk` BOOLEAN DEFAULT FALSE,
    `func_risk_other_txt` TEXT NULL,
    `func_swallowing_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_swallowing_disorder_txt` TEXT NULL,
    `func_nutritional_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_nutritional_disorder_txt` TEXT NULL,
    `func_excretory_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_excretory_disorder_txt` TEXT NULL,
    `func_pressure_ulcer_chk` BOOLEAN DEFAULT FALSE,
    `func_pressure_ulcer_txt` TEXT NULL,
    `func_pain_chk` BOOLEAN DEFAULT FALSE,
    `func_pain_txt` TEXT NULL,
    `func_other_chk` BOOLEAN DEFAULT FALSE,
    `func_other_txt` TEXT NULL,
    `func_rom_limitation_chk` BOOLEAN DEFAULT FALSE,
    `func_rom_limitation_txt` TEXT NULL,
    `func_contracture_deformity_chk` BOOLEAN DEFAULT FALSE,
    `func_contracture_deformity_txt` TEXT NULL,
    `func_muscle_weakness_chk` BOOLEAN DEFAULT FALSE,
    `func_muscle_weakness_txt` TEXT NULL,
    `func_motor_dysfunction_chk` BOOLEAN DEFAULT FALSE,
    `func_motor_paralysis_chk` BOOLEAN DEFAULT FALSE,
    `func_motor_involuntary_movement_chk` BOOLEAN DEFAULT FALSE,
    `func_motor_ataxia_chk` BOOLEAN DEFAULT FALSE,
    `func_motor_parkinsonism_chk` BOOLEAN DEFAULT FALSE,
    `func_motor_muscle_tone_abnormality_chk` BOOLEAN DEFAULT FALSE,
    `func_motor_muscle_tone_abnormality_txt` TEXT NULL,
    `func_sensory_dysfunction_chk` BOOLEAN DEFAULT FALSE,
    `func_sensory_hearing_chk` BOOLEAN DEFAULT FALSE,
    `func_sensory_vision_chk` BOOLEAN DEFAULT FALSE,
    `func_sensory_superficial_chk` BOOLEAN DEFAULT FALSE,
    `func_sensory_deep_chk` BOOLEAN DEFAULT FALSE,
    `func_speech_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_speech_articulation_chk` BOOLEAN DEFAULT FALSE,
    `func_speech_aphasia_chk` BOOLEAN DEFAULT FALSE,
    `func_speech_stuttering_chk` BOOLEAN DEFAULT FALSE,
    `func_speech_other_chk` BOOLEAN DEFAULT FALSE,
    `func_speech_other_txt` TEXT NULL,
    `func_higher_brain_dysfunction_chk` BOOLEAN DEFAULT FALSE,
    `func_higher_brain_memory_chk` BOOLEAN DEFAULT FALSE,
    `func_higher_brain_attention_chk` BOOLEAN DEFAULT FALSE,
    `func_higher_brain_apraxia_chk` BOOLEAN DEFAULT FALSE,
    `func_higher_brain_agnosia_chk` BOOLEAN DEFAULT FALSE,
    `func_higher_brain_executive_chk` BOOLEAN DEFAULT FALSE,
    `func_behavioral_psychiatric_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_behavioral_psychiatric_disorder_txt` TEXT NULL,
    `func_disorientation_chk` BOOLEAN DEFAULT FALSE,
    `func_disorientation_txt` TEXT NULL,
    `func_memory_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_memory_disorder_txt` TEXT NULL,
    `func_developmental_disorder_chk` BOOLEAN DEFAULT FALSE,
    `func_developmental_asd_chk` BOOLEAN DEFAULT FALSE,
    `func_developmental_ld_chk` BOOLEAN DEFAULT FALSE,
    `func_developmental_adhd_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_rolling_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_rolling_independent_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_rolling_partial_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_rolling_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_rolling_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_getting_up_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_getting_up_independent_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_getting_up_partial_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_getting_up_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_getting_up_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_up_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_up_independent_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_up_partial_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_up_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_up_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_sitting_balance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_sitting_balance_independent_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_sitting_balance_partial_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_sitting_balance_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_sitting_balance_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_balance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_balance_independent_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_balance_partial_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_balance_assistance_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_standing_balance_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_other_chk` BOOLEAN DEFAULT FALSE,
    `func_basic_other_txt` TEXT NULL,

    -- ADL (FIM/BI)
    `adl_eating_fim_start_val` INT NULL, `adl_eating_fim_current_val` INT NULL, `adl_eating_bi_start_val` INT NULL, `adl_eating_bi_current_val` INT NULL,
    `adl_grooming_fim_start_val` INT NULL, `adl_grooming_fim_current_val` INT NULL, `adl_grooming_bi_start_val` INT NULL, `adl_grooming_bi_current_val` INT NULL,
    `adl_bathing_fim_start_val` INT NULL, `adl_bathing_fim_current_val` INT NULL, `adl_bathing_bi_start_val` INT NULL, `adl_bathing_bi_current_val` INT NULL,
    `adl_dressing_upper_fim_start_val` INT NULL, `adl_dressing_upper_fim_current_val` INT NULL,
    `adl_dressing_lower_fim_start_val` INT NULL, `adl_dressing_lower_fim_current_val` INT NULL,
    `adl_dressing_bi_start_val` INT NULL, `adl_dressing_bi_current_val` INT NULL,
    `adl_toileting_fim_start_val` INT NULL, `adl_toileting_fim_current_val` INT NULL, `adl_toileting_bi_start_val` INT NULL, `adl_toileting_bi_current_val` INT NULL,
    `adl_bladder_management_fim_start_val` INT NULL, `adl_bladder_management_fim_current_val` INT NULL, `adl_bladder_management_bi_start_val` INT NULL, `adl_bladder_management_bi_current_val` INT NULL,
    `adl_bowel_management_fim_start_val` INT NULL, `adl_bowel_management_fim_current_val` INT NULL, `adl_bowel_management_bi_start_val` INT NULL, `adl_bowel_management_bi_current_val` INT NULL,
    `adl_transfer_bed_chair_wc_fim_start_val` INT NULL, `adl_transfer_bed_chair_wc_fim_current_val` INT NULL,
    `adl_transfer_toilet_fim_start_val` INT NULL, `adl_transfer_toilet_fim_current_val` INT NULL,
    `adl_transfer_tub_shower_fim_start_val` INT NULL, `adl_transfer_tub_shower_fim_current_val` INT NULL,
    `adl_transfer_bi_start_val` INT NULL, `adl_transfer_bi_current_val` INT NULL,
    `adl_locomotion_walk_walkingAids_wc_fim_start_val` INT NULL, `adl_locomotion_walk_walkingAids_wc_fim_current_val` INT NULL, `adl_locomotion_walk_walkingAids_wc_bi_start_val` INT NULL, `adl_locomotion_walk_walkingAids_wc_bi_current_val` INT NULL,
    `adl_locomotion_stairs_fim_start_val` INT NULL, `adl_locomotion_stairs_fim_current_val` INT NULL, `adl_locomotion_stairs_bi_start_val` INT NULL, `adl_locomotion_stairs_bi_current_val` INT NULL,
    `adl_comprehension_fim_start_val` INT NULL, `adl_comprehension_fim_current_val` INT NULL,
    `adl_expression_fim_start_val` INT NULL, `adl_expression_fim_current_val` INT NULL,
    `adl_social_interaction_fim_start_val` INT NULL, `adl_social_interaction_fim_current_val` INT NULL,
    `adl_problem_solving_fim_start_val` INT NULL, `adl_problem_solving_fim_current_val` INT NULL,
    `adl_memory_fim_start_val` INT NULL, `adl_memory_fim_current_val` INT NULL,
    `adl_equipment_and_assistance_details_txt` TEXT NULL,

    -- 栄養
    `nutrition_height_chk` BOOLEAN DEFAULT FALSE, `nutrition_height_val` DECIMAL(5,1) NULL,
    `nutrition_weight_chk` BOOLEAN DEFAULT FALSE, `nutrition_weight_val` DECIMAL(5,1) NULL,
    `nutrition_bmi_chk` BOOLEAN DEFAULT FALSE, `nutrition_bmi_val` DECIMAL(4,1) NULL,
    `nutrition_method_oral_chk` BOOLEAN DEFAULT FALSE, `nutrition_method_oral_meal_chk` BOOLEAN DEFAULT FALSE,
    `nutrition_method_oral_supplement_chk` BOOLEAN DEFAULT FALSE, `nutrition_method_tube_chk` BOOLEAN DEFAULT FALSE,
    `nutrition_method_iv_chk` BOOLEAN DEFAULT FALSE, `nutrition_method_iv_peripheral_chk` BOOLEAN DEFAULT FALSE,
    `nutrition_method_iv_central_chk` BOOLEAN DEFAULT FALSE, `nutrition_method_peg_chk` BOOLEAN DEFAULT FALSE,
    `nutrition_swallowing_diet_slct` VARCHAR(50) NULL COMMENT '嚥下調整食の選択',
    `nutrition_swallowing_diet_code_txt` VARCHAR(255) NULL,
    `nutrition_status_assessment_slct` VARCHAR(50) NULL COMMENT '栄養状態評価の選択',
    `nutrition_status_assessment_other_txt` TEXT NULL,
    `nutrition_required_energy_val` INT NULL, `nutrition_required_protein_val` INT NULL,
    `nutrition_total_intake_energy_val` INT NULL, `nutrition_total_intake_protein_val` INT NULL,

    -- 社会保障サービス
    `social_care_level_status_chk` BOOLEAN DEFAULT FALSE, `social_care_level_applying_chk` BOOLEAN DEFAULT FALSE,
    `social_care_level_support_chk` BOOLEAN DEFAULT FALSE, `social_care_level_support_num1_slct` BOOLEAN DEFAULT FALSE,
    `social_care_level_support_num2_slct` BOOLEAN DEFAULT FALSE, `social_care_level_care_slct` BOOLEAN DEFAULT FALSE,
    `social_care_level_care_num1_slct` BOOLEAN DEFAULT FALSE, `social_care_level_care_num2_slct` BOOLEAN DEFAULT FALSE,
    `social_care_level_care_num3_slct` BOOLEAN DEFAULT FALSE, `social_care_level_care_num4_slct` BOOLEAN DEFAULT FALSE,
    `social_care_level_care_num5_slct` BOOLEAN DEFAULT FALSE, `social_disability_certificate_physical_chk` BOOLEAN DEFAULT FALSE,
    `social_disability_certificate_physical_txt` TEXT NULL, `social_disability_certificate_physical_type_txt` VARCHAR(255) NULL,
    `social_disability_certificate_physical_rank_val` INT NULL, `social_disability_certificate_mental_chk` BOOLEAN DEFAULT FALSE,
    `social_disability_certificate_mental_rank_val` INT NULL, `social_disability_certificate_intellectual_chk` BOOLEAN DEFAULT FALSE,
    `social_disability_certificate_intellectual_txt` TEXT NULL, `social_disability_certificate_intellectual_grade_txt` VARCHAR(255) NULL,
    `social_disability_certificate_other_chk` BOOLEAN DEFAULT FALSE, `social_disability_certificate_other_txt` TEXT NULL,

    -- 目標・方針・署名
    `goals_1_month_txt` TEXT NULL, `goals_at_discharge_txt` TEXT NULL,
    `goals_planned_hospitalization_period_chk` BOOLEAN DEFAULT FALSE, `goals_planned_hospitalization_period_txt` TEXT NULL,
    `goals_discharge_destination_chk` BOOLEAN DEFAULT FALSE, `goals_discharge_destination_txt` TEXT NULL,
    `goals_long_term_care_needed_chk` BOOLEAN DEFAULT FALSE,
    `policy_treatment_txt` TEXT NULL, `policy_content_txt` TEXT NULL,
    `signature_rehab_doctor_txt` VARCHAR(255) NULL, `signature_primary_doctor_txt` VARCHAR(255) NULL,
    `signature_pt_txt` VARCHAR(255) NULL, `signature_ot_txt` VARCHAR(255) NULL,
    `signature_st_txt` VARCHAR(255) NULL, `signature_nurse_txt` VARCHAR(255) NULL,
    `signature_dietitian_txt` VARCHAR(255) NULL, `signature_social_worker_txt` VARCHAR(255) NULL,
    `signature_explained_to_txt` VARCHAR(255) NULL, `signature_explanation_date` DATE NULL, `signature_explainer_txt` VARCHAR(255) NULL,

    -- 【2枚目】----------------------------------------------------
    -- 目標(参加)
    `goal_p_residence_chk` BOOLEAN DEFAULT FALSE, `goal_p_residence_slct` VARCHAR(50) NULL,
    `goal_p_residence_other_txt` TEXT NULL, 
    `goal_p_return_to_work_chk` BOOLEAN DEFAULT FALSE,
    `goal_p_return_to_work_status_slct` VARCHAR(50) NULL, `goal_p_return_to_work_status_other_txt` TEXT NULL,
    `goal_p_return_to_work_commute_change_chk` BOOLEAN DEFAULT FALSE, `goal_p_schooling_chk` BOOLEAN DEFAULT FALSE,
    `goal_p_schooling_status_possible_chk` BOOLEAN DEFAULT FALSE, `goal_p_schooling_status_needs_consideration_chk` BOOLEAN DEFAULT FALSE,
    `goal_p_schooling_status_change_course_chk` BOOLEAN DEFAULT FALSE, `goal_p_schooling_status_not_possible_chk` BOOLEAN DEFAULT FALSE,
    `goal_p_schooling_status_other_chk` BOOLEAN DEFAULT FALSE, `goal_p_schooling_status_other_txt` TEXT NULL,
    `goal_p_schooling_destination_chk` BOOLEAN DEFAULT FALSE, `goal_p_schooling_destination_txt` TEXT NULL,
    `goal_p_schooling_commute_change_chk` BOOLEAN DEFAULT FALSE, `goal_p_schooling_commute_change_txt` TEXT NULL,
    `goal_p_household_role_chk` BOOLEAN DEFAULT FALSE, `goal_p_household_role_txt` TEXT NULL,
    `goal_p_social_activity_chk` BOOLEAN DEFAULT FALSE, `goal_p_social_activity_txt` TEXT NULL,
    `goal_p_hobby_chk` BOOLEAN DEFAULT FALSE, `goal_p_hobby_txt` TEXT NULL,

    -- 目標(活動)
    `goal_a_bed_mobility_chk` BOOLEAN DEFAULT FALSE, `goal_a_bed_mobility_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_bed_mobility_assistance_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_bed_mobility_not_performed_chk` BOOLEAN DEFAULT FALSE, `goal_a_bed_mobility_equipment_chk` BOOLEAN DEFAULT FALSE, `goal_a_bed_mobility_environment_setup_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_indoor_mobility_chk` BOOLEAN DEFAULT FALSE, `goal_a_indoor_mobility_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_indoor_mobility_assistance_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_indoor_mobility_not_performed_chk` BOOLEAN DEFAULT FALSE, `goal_a_indoor_mobility_equipment_chk` BOOLEAN DEFAULT FALSE, `goal_a_indoor_mobility_equipment_txt` TEXT NULL,
    `goal_a_outdoor_mobility_chk` BOOLEAN DEFAULT FALSE, `goal_a_outdoor_mobility_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_outdoor_mobility_assistance_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_outdoor_mobility_not_performed_chk` BOOLEAN DEFAULT FALSE, `goal_a_outdoor_mobility_equipment_chk` BOOLEAN DEFAULT FALSE, `goal_a_outdoor_mobility_equipment_txt` TEXT NULL,
    `goal_a_driving_chk` BOOLEAN DEFAULT FALSE, `goal_a_driving_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_driving_assistance_chk` BOOLEAN DEFAULT FALSE, `goal_a_driving_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_driving_modification_chk` BOOLEAN DEFAULT FALSE, `goal_a_driving_modification_txt` TEXT NULL, `goal_a_public_transport_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_public_transport_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_public_transport_assistance_chk` BOOLEAN DEFAULT FALSE, `goal_a_public_transport_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_public_transport_type_chk` BOOLEAN DEFAULT FALSE, `goal_a_public_transport_type_txt` TEXT NULL, `goal_a_toileting_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_toileting_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_toileting_assistance_chk` BOOLEAN DEFAULT FALSE, `goal_a_toileting_assistance_clothing_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_toileting_assistance_wiping_chk` BOOLEAN DEFAULT FALSE, `goal_a_toileting_assistance_catheter_chk` BOOLEAN DEFAULT FALSE, `goal_a_toileting_type_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_toileting_type_western_chk` BOOLEAN DEFAULT FALSE, `goal_a_toileting_type_japanese_chk` BOOLEAN DEFAULT FALSE, `goal_a_toileting_type_other_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_toileting_type_other_txt` TEXT NULL, `goal_a_eating_chk` BOOLEAN DEFAULT FALSE, `goal_a_eating_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_eating_assistance_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_eating_not_performed_chk` BOOLEAN DEFAULT FALSE, `goal_a_eating_method_chopsticks_chk` BOOLEAN DEFAULT FALSE, `goal_a_eating_method_fork_etc_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_eating_method_tube_feeding_chk` BOOLEAN DEFAULT FALSE, `goal_a_eating_diet_form_txt` TEXT NULL, `goal_a_grooming_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_grooming_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_grooming_assistance_chk` BOOLEAN DEFAULT FALSE, `goal_a_dressing_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_dressing_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_dressing_assistance_chk` BOOLEAN DEFAULT FALSE, `goal_a_bathing_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_bathing_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_bathing_assistance_chk` BOOLEAN DEFAULT FALSE, `goal_a_bathing_type_tub_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_bathing_type_shower_chk` BOOLEAN DEFAULT FALSE, `goal_a_bathing_assistance_body_washing_chk` BOOLEAN DEFAULT FALSE, `goal_a_bathing_assistance_transfer_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_housework_meal_chk` BOOLEAN DEFAULT FALSE, `goal_a_housework_meal_all_chk` BOOLEAN DEFAULT FALSE, `goal_a_housework_meal_not_performed_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_housework_meal_partial_chk` BOOLEAN DEFAULT FALSE, `goal_a_housework_meal_partial_txt` TEXT NULL, `goal_a_writing_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_writing_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_writing_independent_after_hand_change_chk` BOOLEAN DEFAULT FALSE, `goal_a_writing_other_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_writing_other_txt` TEXT NULL, `goal_a_ict_chk` BOOLEAN DEFAULT FALSE, `goal_a_ict_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_ict_assistance_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_communication_chk` BOOLEAN DEFAULT FALSE, `goal_a_communication_independent_chk` BOOLEAN DEFAULT FALSE, `goal_a_communication_assistance_chk` BOOLEAN DEFAULT FALSE,
    `goal_a_communication_device_chk` BOOLEAN DEFAULT FALSE, `goal_a_communication_letter_board_chk` BOOLEAN DEFAULT FALSE, `goal_a_communication_cooperation_chk` BOOLEAN DEFAULT FALSE,

    -- 対応を要する項目
    `goal_s_psychological_support_chk` BOOLEAN DEFAULT FALSE, `goal_s_psychological_support_txt` TEXT NULL, `goal_s_disability_acceptance_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_disability_acceptance_txt` TEXT NULL, `goal_s_psychological_other_chk` BOOLEAN DEFAULT FALSE, `goal_s_psychological_other_txt` TEXT NULL,
    `goal_s_env_home_modification_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_home_modification_txt` TEXT NULL, `goal_s_env_assistive_device_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_assistive_device_txt` TEXT NULL, `goal_s_env_social_security_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_social_security_physical_disability_cert_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_social_security_disability_pension_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_social_security_intractable_disease_cert_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_social_security_other_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_social_security_other_txt` TEXT NULL, `goal_s_env_care_insurance_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_care_insurance_details_txt` TEXT NULL, `goal_s_env_care_insurance_outpatient_rehab_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_care_insurance_home_rehab_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_care_insurance_day_care_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_care_insurance_home_nursing_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_care_insurance_home_care_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_care_insurance_health_facility_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_care_insurance_nursing_home_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_care_insurance_care_hospital_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_care_insurance_other_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_care_insurance_other_txt` TEXT NULL, `goal_s_env_disability_welfare_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_disability_welfare_after_school_day_service_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_disability_welfare_child_development_support_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_disability_welfare_life_care_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_disability_welfare_other_chk` BOOLEAN DEFAULT FALSE, `goal_s_env_other_chk` BOOLEAN DEFAULT FALSE,
    `goal_s_env_other_txt` TEXT NULL, `goal_s_3rd_party_main_caregiver_chk` BOOLEAN DEFAULT FALSE, `goal_s_3rd_party_main_caregiver_txt` TEXT NULL,
    `goal_s_3rd_party_family_structure_change_chk` BOOLEAN DEFAULT FALSE, `goal_s_3rd_party_family_structure_change_txt` TEXT NULL,
    `goal_s_3rd_party_household_role_change_chk` BOOLEAN DEFAULT FALSE, `goal_s_3rd_party_household_role_change_txt` TEXT NULL,
    `goal_s_3rd_party_family_activity_change_chk` BOOLEAN DEFAULT FALSE, `goal_s_3rd_party_family_activity_change_txt` TEXT NULL,

    -- 具体的な対応方針
    `goal_p_action_plan_txt` TEXT NULL, `goal_a_action_plan_txt` TEXT NULL, `goal_s_psychological_action_plan_txt` TEXT NULL,
    `goal_s_env_action_plan_txt` TEXT NULL, `goal_s_3rd_party_action_plan_txt` TEXT NULL,

    -- 外部キー制約
    INDEX `idx_plan_patient_id` (`patient_id`),
    CONSTRAINT `fk_plan_patient_id` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_plan_staff_id` FOREIGN KEY (`created_by_staff_id`) REFERENCES `staff` (`id`) ON DELETE SET NULL
) ENGINE = InnoDB;


-- =================================================================
-- 6. AI提案 いいね評価テーブル (一時保存用)
-- =================================================================
-- ユーザーが計画書を確定するまでの間、「いいね」の評価状態を一時的に保存するテーブル。
CREATE TABLE IF NOT EXISTS suggestion_likes (
    `patient_id` INT NOT NULL COMMENT 'いいね評価の対象となる患者のID (patientsテーブル参照)',
    `item_key` VARCHAR(255) NOT NULL COMMENT 'いいねされた計画書項目のキー (例: main_risks_txt)',
    `liked_model` VARCHAR(50) NOT NULL COMMENT 'いいねされたAIモデルの種類 (general/specialized)',
    `staff_id` INT NOT NULL COMMENT 'いいね操作を行った職員のID (staffテーブル参照)',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'レコード更新日時',

    -- 複合主キー: 1人の患者の1項目に対して、各モデルごとに1つの評価しかできないように制約
    PRIMARY KEY (`patient_id`, `item_key`, `liked_model`),

    -- 検索パフォーマンス向上のためのインデックス
    INDEX `idx_suggestion_like_staff_id` (`staff_id`),

    -- 外部キー制約: 関連する患者や職員が削除された場合に、このテーブルのデータも自動的に削除(CASCADE)される
    CONSTRAINT `fk_suggestion_like_patient_id` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_suggestion_like_staff_id` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = 'AI提案への「いいね」評価を一時的に保存するテーブル';


-- =================================================================
-- 6. いいね詳細情報テーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS liked_item_details (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'レコードを一意に識別するID',
    `rehabilitation_plan_id` INT NOT NULL COMMENT '関連する計画書のID',
    `staff_id` INT NOT NULL COMMENT 'いいねをした職員のID',
    `item_key` VARCHAR(255) NOT NULL COMMENT 'いいねされた項目キー',
    `liked_model` TEXT NULL COMMENT 'いいねされたモデル (カンマ区切り)',
    `general_suggestion_text` TEXT NULL COMMENT '通常モデルの提案内容',
    `specialized_suggestion_text` TEXT NULL COMMENT '特化モデルの提案内容',
    `therapist_notes_at_creation` TEXT NULL COMMENT '計画書作成時の所感',
    `patient_info_snapshot_json` JSON NULL COMMENT '計画書作成時の患者情報スナップショット',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時',
    INDEX `idx_liked_plan_id` (`rehabilitation_plan_id`),
    INDEX `idx_liked_staff_id` (`staff_id`),
    CONSTRAINT `fk_liked_plan_id` FOREIGN KEY (`rehabilitation_plan_id`) REFERENCES `rehabilitation_plans` (`plan_id`) ON DELETE CASCADE,
    CONSTRAINT `fk_liked_staff_id` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = 'いいね評価の詳細情報を格納するテーブル';

-- =================================================================
-- 再生成履歴テーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS regeneration_history (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'レコードを一意に識別するID',
    `rehabilitation_plan_id` INT NOT NULL COMMENT '関連する計画書のID',
    `item_key` VARCHAR(255) NOT NULL COMMENT '再生成された項目キー',
    `model_type` VARCHAR(50) NOT NULL COMMENT '再生成に使用されたモデル (general/specialized)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時',

    INDEX `idx_regen_plan_id` (`rehabilitation_plan_id`),
    CONSTRAINT `fk_regen_plan_id` FOREIGN KEY (`rehabilitation_plan_id`) REFERENCES `rehabilitation_plans` (`plan_id`) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = 'AI提案の再生成履歴を格納するテーブル';


-- -- =================================================================
-- -- 7. サンプルデータの挿入 本番環境でのデータベース作成では使わないでください。
-- -- =================================================================

-- 職員1: yamada さん (管理者 / パスワード: adminpass)
INSERT INTO staff (`id`, `username`, `password`, `occupation`, `role`)
VALUES (
        1,
        'yamada',
        'scrypt:32768:8:1$JlKJ01aekkBsObaa$73e73e06efc0f9722f78fb12ef78114b54062b48d754750a685681577bb44a6ef06d534c7d32717a1da496ba60b982cb87455c6a060e469b76506a1091435131',
        '理学療法士',
        'admin'
    ) ON DUPLICATE KEY
UPDATE `username` = `username`,
    `occupation` = '理学療法士',
    `role` = 'admin';
-- 職員2: sato さん (一般 / パスワード: password123)
INSERT INTO staff (`id`, `username`, `password`, `occupation`, `role`)
VALUES (
        2,
        'sato',
        'scrypt:32768:8:1$rcfwDMziQwokAhOv$c34b18e7582b6d004091f3bd4c647d98469959ccd1919f3d76b6020065d5205b3171f324641c0629b6b0931ea239215bb457bf2eed028431427d30749ca67972',
        '作業療法士',
        'general'
    ) ON DUPLICATE KEY
UPDATE `username` = `username`,
    `occupation` = '作業療法士',
    `role` = 'general';



-- =================================================================
-- 1人目の患者: 田中 翔 (19歳 男性)
-- 疾患: 右膝前十字靭帯(ACL)損傷および内側半月板損傷術後
-- 背景: 大学のサッカー部活動中に受傷。競技復帰を強く希望している。
-- =================================================================
-- 1. 患者情報の登録
INSERT INTO patients (
        `patient_id`,
        `name`,
        `date_of_birth`,
        `gender`
    )
VALUES (
        1,
        '田中 翔',
        '2006-04-10',
        '男'
    );
-- 2. 担当職員の関連付け (山田さんと佐藤さんが担当)
INSERT INTO staff_patients (`staff_id`, `patient_id`)
VALUES (1, 1),
    (2, 1);
-- 3. リハビリテーション計画書の登録
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `created_by_staff_id`,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        `header_evaluation_date`,
        `header_disease_name_txt`,
        `header_onset_date`,
        `header_rehab_start_date`,
        `header_therapy_pt_chk`,
        `header_therapy_ot_chk`,
        `header_therapy_st_chk`,
        -- 併存疾患・リスク・特記事項
        `main_risks_txt`,
        `main_contraindications_txt`,
        -- 心身機能・構造
        `func_pain_chk`,
        `func_pain_txt`,
        `func_rom_limitation_chk`,
        `func_rom_limitation_txt`,
        `func_muscle_weakness_chk`,
        `func_muscle_weakness_txt`,
        `func_nutritional_disorder_chk`,
        `func_nutritional_disorder_txt`,
        -- ADL (FIM/BI) - 術後早期のため移動・セルフケア能力が低下
        `adl_eating_fim_start_val`,
        `adl_eating_fim_current_val`,
        `adl_grooming_fim_start_val`,
        `adl_grooming_fim_current_val`,
        `adl_bathing_fim_start_val`,
        `adl_bathing_fim_current_val`,
        `adl_dressing_upper_fim_start_val`,
        `adl_dressing_upper_fim_current_val`,
        `adl_dressing_lower_fim_start_val`,
        `adl_dressing_lower_fim_current_val`,
        `adl_toileting_fim_start_val`,
        `adl_toileting_fim_current_val`,
        `adl_bladder_management_fim_start_val`,
        `adl_bladder_management_fim_current_val`,
        `adl_bowel_management_fim_start_val`,
        `adl_bowel_management_fim_current_val`,
        `adl_transfer_bed_chair_wc_fim_start_val`,
        `adl_transfer_bed_chair_wc_fim_current_val`,
        `adl_transfer_toilet_fim_start_val`,
        `adl_transfer_toilet_fim_current_val`,
        `adl_transfer_tub_shower_fim_start_val`,
        `adl_transfer_tub_shower_fim_current_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_start_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_current_val`,
        `adl_locomotion_stairs_fim_start_val`,
        `adl_locomotion_stairs_fim_current_val`,
        `adl_comprehension_fim_start_val`,
        `adl_comprehension_fim_current_val`,
        `adl_expression_fim_start_val`,
        `adl_expression_fim_current_val`,
        `adl_social_interaction_fim_start_val`,
        `adl_social_interaction_fim_current_val`,
        `adl_problem_solving_fim_start_val`,
        `adl_problem_solving_fim_current_val`,
        `adl_memory_fim_start_val`,
        `adl_memory_fim_current_val`,
        `adl_equipment_and_assistance_details_txt`,
        -- 栄養
        `nutrition_height_chk`,
        `nutrition_height_val`,
        `nutrition_weight_chk`,
        `nutrition_weight_val`,
        `nutrition_bmi_chk`,
        `nutrition_bmi_val`,
        `nutrition_method_oral_chk`,
        `nutrition_method_oral_meal_chk`,
        -- 目標・方針・署名
        `goals_1_month_txt`,
        `goals_at_discharge_txt`,
        `goals_discharge_destination_chk`,
        `goals_discharge_destination_txt`,
        `policy_treatment_txt`,
        `policy_content_txt`,
        `signature_rehab_doctor_txt`,
        `signature_pt_txt`,
        `signature_ot_txt`,
        `signature_explanation_date`,
        `signature_explainer_txt`,
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        `goal_p_residence_chk`,
        `goal_p_residence_slct`,
        `goal_p_schooling_chk`,
        `goal_p_schooling_status_needs_consideration_chk`,
        `goal_p_hobby_chk`,
        `goal_p_hobby_txt`,
        -- 目標(活動)
        `goal_a_indoor_mobility_chk`,
        `goal_a_indoor_mobility_assistance_chk`,
        `goal_a_indoor_mobility_equipment_chk`,
        `goal_a_indoor_mobility_equipment_txt`,
        `goal_a_outdoor_mobility_chk`,
        `goal_a_outdoor_mobility_assistance_chk`,
        `goal_a_bathing_chk`,
        `goal_a_bathing_assistance_chk`,
        `goal_a_bathing_type_shower_chk`,
        `goal_a_bathing_assistance_transfer_chk`,
        `goal_a_public_transport_chk`,
        `goal_a_public_transport_assistance_chk`,
        -- 具体的な対応方針
        `goal_p_action_plan_txt`,
        `goal_a_action_plan_txt`,
        `goal_s_env_action_plan_txt`
    )
VALUES (
        1,
        1,
        1,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        '2025-10-04',
        '右膝前十字靭帯(ACL)損傷、内側半月板損傷術後',
        '2025-09-15',
        '2025-09-22',
        TRUE,
        TRUE,
        FALSE,
        -- 併存疾患・リスク・特記事項
        '術後創部の感染リスク。体重免荷制限の遵守が必要。無理な可動域訓練による再断裂リスク。',
        '術後6週までは医師の指示なく右下肢への荷重は禁忌。',
        -- 心身機能・構造
        TRUE,
        '右膝の術後痛および運動時痛あり。NRS 4/10。鎮痛薬でコントロール中。',
        TRUE,
        '右膝関節の可動域制限あり。評価時屈曲100度、伸展-5度。',
        TRUE,
        '右大腿四頭筋を中心に右下肢全体の筋力低下が著明 (MMT 3レベル)。',
        TRUE,
        '軽度の鉄欠乏性貧血の既往あり。食事指導にて経過観察中。',
        -- ADL (FIM/BI)
        7,
        7,
        -- 整容
        7,
        7,
        -- 清拭
        4,
        5,
        -- 更衣(上半身)
        7,
        7,
        -- 更衣(下半身)
        4,
        5,
        -- トイレ動作
        5,
        6,
        -- 排尿管理
        7,
        7,
        -- 排便管理
        7,
        7,
        -- 移乗(ベッド・椅子・車椅子)
        5,
        6,
        -- 移乗(トイレ)
        5,
        6,
        -- 移乗(風呂)
        3,
        4,
        -- 移動(歩行・車椅子)
        2,
        3,
        -- 階段
        1,
        1,
        -- 理解
        7,
        7,
        -- 表出
        7,
        7,
        -- 社会的交流
        7,
        7,
        -- 問題解決
        7,
        7,
        -- 記憶
        7,
        7,
        '移動は松葉杖を使用し右下肢完全免荷。入浴にはシャワーチェア、滑り止めマットを使用。',
        -- 栄養
        TRUE,
        175.0,
        TRUE,
        65.0,
        TRUE,
        21.2,
        TRUE,
        TRUE,
        -- 目標・方針・署名
        '松葉杖を用いた監視下での病棟内移動が自立する。右膝関節可動域が屈曲120度、伸展0度まで改善する。',
        '杖なしでの屋外歩行が自立し、ジョギングが可能なレベルまで筋力・機能が回復する。大学への復学とサッカー部への段階的復帰。',
        TRUE,
        '自宅（一人暮らしのアパート）',
        '医師の術後リハビリテーションプロトコルを遵守し、段階的に関節可動域、筋力、荷重の負荷を高めていく。物理療法（アイシング、電気刺激）を併用し、疼痛管理と機能回復を促進する。',
        '【理学療法】: 関節可動域訓練(他動・自動)、大腿四頭筋セッティング、SLR、下肢筋力強化訓練(非荷重下)。\n【作業療法】: 松葉杖でのADL（入浴、更衣、トイレ）動作指導、家屋環境を想定した動作練習。',
        '鈴木 一郎',
        '山田 太郎',
        '佐藤 花子',
        '2025-10-04',
        '山田 太郎',
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        TRUE,
        '自宅',
        TRUE,
        TRUE,
        TRUE,
        '大学のサッカー部活動への完全復帰。レギュラーとして試合に出場する。',
        -- 目標(活動)
        TRUE,
        TRUE,
        TRUE,
        '松葉杖',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        -- 具体的な対応方針
        '退院後の通学方法（公共交通機関の利用）やオンライン授業の活用についてソーシャルワーカーと連携し検討する。競技復帰に向けた心理的サポートも考慮する。',
        '段階的な荷重練習（部分荷重→全荷重）と歩行訓練（平行棒内→松葉杖→独歩）を実施。自主トレーニングメニューを指導し、病棟での実践を促す。',
        '退院後の生活（特に家事動作）を想定し、自助具の検討や動作方法の工夫を指導する。'
    );


-- =================================================================
-- 2人目の患者: 鈴木 美咲 (35歳 女性)
-- 疾患: 頚椎症性脊髄症術後
-- 背景: Webデザイナー。長年のデスクワークが影響。両手の痺れと歩行障害で手術。
--       合併症として2型糖尿病があり、食事・運動療法も並行している。
-- =================================================================
-- 1. 患者情報の登録
INSERT INTO patients (
        `patient_id`,
        `name`,
        `date_of_birth`,
        `gender`
    )
VALUES (
        2,
        '鈴木 美咲',
        '1990-07-20',
        '女'
    );
-- 2. 担当職員の関連付け (山田さんと佐藤さんが担当)
INSERT INTO staff_patients (`staff_id`, `patient_id`)
VALUES (1, 2),
    (2, 2);
-- 3. リハビリテーション計画書の登録
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `created_by_staff_id`,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        `header_evaluation_date`,
        `header_disease_name_txt`,
        `header_onset_date`,
        `header_rehab_start_date`,
        `header_therapy_pt_chk`,
        `header_therapy_ot_chk`,
        `header_therapy_st_chk`,
        -- 併存疾患・リスク・特記事項
        `main_comorbidities_txt`,
        `main_risks_txt`,
        `main_contraindications_txt`,
        -- 心身機能・構造
        `func_risk_factors_chk`,
        `func_risk_diabetes_chk`,
        `func_pain_chk`,
        `func_pain_txt`,
        `func_muscle_weakness_chk`,
        `func_muscle_weakness_txt`,
        `func_motor_dysfunction_chk`,
        `func_motor_paralysis_chk`,
        `func_motor_ataxia_chk`,
        `func_sensory_dysfunction_chk`,
        `func_sensory_superficial_chk`,
        `func_sensory_deep_chk`,
        `func_basic_standing_balance_chk`,
        `func_basic_standing_balance_partial_assistance_chk`,
        -- ADL (FIM/BI) - 手指の巧緻性低下と歩行の不安定性により全体的に低下
        `adl_eating_fim_start_val`,
        `adl_eating_fim_current_val`,
        `adl_grooming_fim_start_val`,
        `adl_grooming_fim_current_val`,
        `adl_bathing_fim_start_val`,
        `adl_bathing_fim_current_val`,
        `adl_dressing_upper_fim_start_val`,
        `adl_dressing_upper_fim_current_val`,
        `adl_dressing_lower_fim_start_val`,
        `adl_dressing_lower_fim_current_val`,
        `adl_toileting_fim_start_val`,
        `adl_toileting_fim_current_val`,
        `adl_bladder_management_fim_start_val`,
        `adl_bladder_management_fim_current_val`,
        `adl_bowel_management_fim_start_val`,
        `adl_bowel_management_fim_current_val`,
        `adl_transfer_bed_chair_wc_fim_start_val`,
        `adl_transfer_bed_chair_wc_fim_current_val`,
        `adl_transfer_toilet_fim_start_val`,
        `adl_transfer_toilet_fim_current_val`,
        `adl_transfer_tub_shower_fim_start_val`,
        `adl_transfer_tub_shower_fim_current_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_start_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_current_val`,
        `adl_locomotion_stairs_fim_start_val`,
        `adl_locomotion_stairs_fim_current_val`,
        `adl_comprehension_fim_start_val`,
        `adl_comprehension_fim_current_val`,
        `adl_expression_fim_start_val`,
        `adl_expression_fim_current_val`,
        `adl_equipment_and_assistance_details_txt`,
        -- 栄養
        `nutrition_height_chk`,
        `nutrition_height_val`,
        `nutrition_weight_chk`,
        `nutrition_weight_val`,
        `nutrition_bmi_chk`,
        `nutrition_bmi_val`,
        `nutrition_method_oral_chk`,
        `nutrition_method_oral_meal_chk`,
        `nutrition_required_energy_val`,
        `nutrition_required_protein_val`,
        -- 目標・方針・署名
        `goals_1_month_txt`,
        `goals_at_discharge_txt`,
        `goals_discharge_destination_chk`,
        `goals_discharge_destination_txt`,
        `policy_treatment_txt`,
        `policy_content_txt`,
        `signature_rehab_doctor_txt`,
        `signature_pt_txt`,
        `signature_ot_txt`,
        `signature_explanation_date`,
        `signature_explainer_txt`,
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        `goal_p_residence_chk`,
        `goal_p_residence_slct`,
        `goal_p_return_to_work_chk`,
        `goal_p_return_to_work_status_slct`,
        `goal_p_hobby_chk`,
        `goal_p_hobby_txt`,
        -- 目標(活動)
        `goal_a_writing_chk`,
        `goal_a_writing_other_chk`,
        `goal_a_writing_other_txt`,
        `goal_a_ict_chk`,
        `goal_a_ict_assistance_chk`,
        `goal_a_housework_meal_chk`,
        `goal_a_housework_meal_partial_chk`,
        `goal_a_housework_meal_partial_txt`,
        -- 対応を要する項目
        `goal_s_env_assistive_device_chk`,
        `goal_s_env_assistive_device_txt`,
        -- 具体的な対応方針
        `goal_p_action_plan_txt`,
        `goal_a_action_plan_txt`,
        `goal_s_env_action_plan_txt`
    )
VALUES (
        2,
        2,
        2,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        '2025-10-04',
        '頚椎症性脊髄症術後',
        '2025-09-20',
        '2025-09-25',
        TRUE,
        TRUE,
        FALSE,
        -- 併存疾患・リスク・特記事項
        '2型糖尿病（血糖コントロールは経口薬で良好）、片頭痛',
        '術後合併症（深部静脈血栓症）。血糖値の変動に注意。頚部の過度な伸展・屈曲は避ける。',
        '頚椎カラーを常時装着。医師の許可なく外さないこと。',
        -- 心身機能・構造
        TRUE,
        TRUE,
        TRUE,
        '頚部痛および両上肢のしびれ感。特に右手指先に強い。NRS 5/10。',
        TRUE,
        '両上肢、特に手指の巧緻運動に関わる内在筋の筋力低下あり (MMT 4-レベル)。',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        -- ADL (FIM/BI)
        5,
        6,
        -- 整容
        5,
        5,
        -- 清拭
        5,
        5,
        -- 更衣(上半身)
        4,
        5,
        -- 更衣(下半身)
        5,
        6,
        -- トイレ動作
        5,
        6,
        -- 排尿管理
        7,
        7,
        -- 排便管理
        7,
        7,
        -- 移乗(ベッド・椅子・車椅子)
        6,
        6,
        -- 移乗(トイレ)
        6,
        6,
        -- 移乗(風呂)
        5,
        5,
        -- 移動(歩行・車椅子)
        4,
        5,
        -- 階段
        2,
        3,
        -- 理解
        7,
        7,
        -- 表出
        7,
        7,
        '歩行は監視下で自立も、ふらつきあり。食事は柄付きのスプーン・フォークを使用。更衣はボタンエイド等の自助具を検討中。',
        -- 栄養
        TRUE,
        160.0,
        TRUE,
        58.0,
        TRUE,
        22.7,
        TRUE,
        TRUE,
        1600,
        60,
        -- 目標・方針・署名
        '屋内でのT字杖歩行が安定する。手指巧緻性の改善（ペグボードで30秒→45秒）。簡単な調理（野菜を切るなど）が監視下で可能となる。',
        '杖なしでの屋外歩行が安定し、公共交通機関を利用して安全に通勤できる。PCのキーボード・マウス操作が実用レベルまで回復し、デスクワークへ復帰する。',
        TRUE,
        '自宅（夫と二人暮らし）',
        '頚椎への負担を避けた体幹・四肢の機能訓練を中心に進める。糖尿病内科と連携し、運動療法中の血糖管理に注意する。職場復帰に向け、産業医や会社担当者との連携も視野に入れる。',
        '【理学療法】: バランス訓練、歩行訓練（姿勢矯正、不整地歩行）、下肢筋力強化、全身持久力訓練。\n【作業療法】: 手指巧緻動作訓練（ペグ、粘土、書字）、ADL指導（自助具の選定・使用訓練）、PC操作の再獲得訓練。',
        '鈴木 一郎',
        '山田 太郎',
        '佐藤 花子',
        '2025-10-04',
        '佐藤 花子',
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        TRUE,
        '自宅',
        TRUE,
        '休職中',
        TRUE,
        'お菓子作り、観葉植物の世話',
        -- 目標(活動)
        TRUE,
        TRUE,
        '手指の痺れにより文字が乱れるため、改善が必要。',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        '包丁操作など、細かい作業に一部介助・監視を要する。',
        -- 対応を要する項目
        TRUE,
        'PC作業用のリストレスト、キーボードの種類変更、太柄の調理器具などを検討。',
        -- 具体的な対応方針
        '復職に向け、仕事内容（作業時間、休憩の取り方）について会社側と調整が必要。そのための情報提供や面談設定をMSWと連携して行う。',
        '手指巧緻性改善のため、趣味のお菓子作りや植物の世話を課題として取り入れ、意欲の向上を図る。調理やPC操作など具体的な場面を想定した訓練を強化する。',
        '身体機能の回復に合わせて、職場環境（机、椅子、PC周辺）の調整を提案する。'
    );


-- =================================================================
-- 3人目の患者: 佐藤 健一 (68歳 男性)
-- 疾患: 左変形性股関節症による人工股関節全置換術後
-- 背景: 趣味のゴルフと旅行に意欲的。骨粗鬆症と高血圧の既往あり。
-- =================================================================
-- 1. 患者情報の登録
INSERT INTO patients (
        `patient_id`,
        `name`,
        `date_of_birth`,
        `gender`
    )
VALUES (
        3,
        '佐藤 健一',
        '1957-11-05',
        '男'
    );
-- 2. 担当職員の関連付け (山田さんと佐藤さんが担当)
INSERT INTO staff_patients (`staff_id`, `patient_id`)
VALUES (1, 3),
    (2, 3);
-- 3. リハビリテーション計画書の登録
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `created_by_staff_id`,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        `header_evaluation_date`,
        `header_disease_name_txt`,
        `header_onset_date`,
        `header_rehab_start_date`,
        `header_therapy_pt_chk`,
        `header_therapy_ot_chk`,
        `header_therapy_st_chk`,
        -- 併存疾患・リスク・特記事項
        `main_comorbidities_txt`,
        `main_risks_txt`,
        `main_contraindications_txt`,
        -- 心身機能・構造
        `func_risk_factors_chk`,
        `func_risk_hypertension_chk`,
        `func_risk_ckd_chk`,
        `func_pain_chk`,
        `func_pain_txt`,
        `func_rom_limitation_chk`,
        `func_rom_limitation_txt`,
        `func_muscle_weakness_chk`,
        `func_muscle_weakness_txt`,
        `func_basic_standing_balance_chk`,
        `func_basic_standing_balance_partial_assistance_chk`,
        `func_basic_standing_balance_assistance_chk`,
        -- ADL (FIM/BI) - 術後の可動域制限と荷重制限により低下
        `adl_eating_fim_start_val`,
        `adl_eating_fim_current_val`,
        `adl_grooming_fim_start_val`,
        `adl_grooming_fim_current_val`,
        `adl_bathing_fim_start_val`,
        `adl_bathing_fim_current_val`,
        `adl_dressing_upper_fim_start_val`,
        `adl_dressing_upper_fim_current_val`,
        `adl_dressing_lower_fim_start_val`,
        `adl_dressing_lower_fim_current_val`,
        `adl_toileting_fim_start_val`,
        `adl_toileting_fim_current_val`,
        `adl_bladder_management_fim_start_val`,
        `adl_bladder_management_fim_current_val`,
        `adl_bowel_management_fim_start_val`,
        `adl_bowel_management_fim_current_val`,
        `adl_transfer_bed_chair_wc_fim_start_val`,
        `adl_transfer_bed_chair_wc_fim_current_val`,
        `adl_transfer_toilet_fim_start_val`,
        `adl_transfer_toilet_fim_current_val`,
        `adl_transfer_tub_shower_fim_start_val`,
        `adl_transfer_tub_shower_fim_current_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_start_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_current_val`,
        `adl_locomotion_stairs_fim_start_val`,
        `adl_locomotion_stairs_fim_current_val`,
        `adl_comprehension_fim_start_val`,
        `adl_comprehension_fim_current_val`,
        `adl_expression_fim_start_val`,
        `adl_expression_fim_current_val`,
        `adl_equipment_and_assistance_details_txt`,
        -- 栄養
        `nutrition_height_chk`,
        `nutrition_height_val`,
        `nutrition_weight_chk`,
        `nutrition_weight_val`,
        `nutrition_bmi_chk`,
        `nutrition_bmi_val`,
        `nutrition_method_oral_chk`,
        `nutrition_method_oral_meal_chk`,
        -- 社会保障サービス
        `social_care_level_status_chk`,
        `social_care_level_care_slct`,
        `social_care_level_care_num1_slct`,
        -- 目標・方針・署名
        `goals_1_month_txt`,
        `goals_at_discharge_txt`,
        `goals_discharge_destination_chk`,
        `goals_discharge_destination_txt`,
        `policy_treatment_txt`,
        `policy_content_txt`,
        `signature_rehab_doctor_txt`,
        `signature_pt_txt`,
        `signature_ot_txt`,
        `signature_explanation_date`,
        `signature_explainer_txt`,
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        `goal_p_residence_chk`,
        `goal_p_residence_slct`,
        `goal_p_social_activity_chk`,
        `goal_p_social_activity_txt`,
        `goal_p_hobby_chk`,
        `goal_p_hobby_txt`,
        -- 目標(活動)
        `goal_a_indoor_mobility_chk`,
        `goal_a_indoor_mobility_assistance_chk`,
        `goal_a_indoor_mobility_equipment_chk`,
        `goal_a_indoor_mobility_equipment_txt`,
        `goal_a_outdoor_mobility_chk`,
        `goal_a_outdoor_mobility_assistance_chk`,
        `goal_a_outdoor_mobility_equipment_chk`,
        `goal_a_outdoor_mobility_equipment_txt`,
        `goal_a_bathing_chk`,
        `goal_a_bathing_independent_chk`,
        `goal_a_bathing_type_tub_chk`,
        `goal_a_housework_meal_chk`,
        `goal_a_housework_meal_partial_chk`,
        `goal_a_housework_meal_partial_txt`,
        -- 対応を要する項目
        `goal_s_env_home_modification_chk`,
        `goal_s_env_home_modification_txt`,
        `goal_s_env_assistive_device_chk`,
        `goal_s_env_assistive_device_txt`,
        `goal_s_env_care_insurance_chk`,
        `goal_s_env_care_insurance_details_txt`,
        `goal_s_3rd_party_main_caregiver_chk`,
        `goal_s_3rd_party_main_caregiver_txt`,
        -- 具体的な対応方針
        `goal_p_action_plan_txt`,
        `goal_a_action_plan_txt`,
        `goal_s_env_action_plan_txt`,
        `goal_s_3rd_party_action_plan_txt`
    )
VALUES (
        3,
        3,
        1,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        '2025-10-04',
        '左変形性股関節症による人工股関節全置換術後',
        '2025-09-10',
        '2025-09-17',
        TRUE,
        TRUE,
        FALSE,
        -- 併存疾患・リスク・特記事項
        '骨粗鬆症、高血圧症（内服治療中、血圧コントロール良好）',
        NULL,
        NULL,
        -- 心身機能・構造
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        NULL,
        TRUE,
        NULL,
        TRUE,
        NULL,
        TRUE,
        TRUE,
        TRUE,
        -- ADL (FIM/BI)
        7,
        7,
        -- 整容
        6,
        6,
        -- 清拭
        4,
        5,
        -- 更衣(上半身)
        7,
        7,
        -- 更衣(下半身)
        3,
        4,
        -- トイレ動作
        5,
        6,
        -- 排尿管理
        7,
        7,
        -- 排便管理
        7,
        7,
        -- 移乗(ベッド・椅子・車椅子)
        4,
        5,
        -- 移乗(トイレ)
        4,
        5,
        -- 移乗(風呂)
        3,
        4,
        -- 移動(歩行・車椅子)
        3,
        4,
        -- 階段
        1,
        1,
        -- 理解
        7,
        7,
        -- 表出
        7,
        7,
        NULL,
        -- 栄養
        TRUE,
        168.0,
        TRUE,
        63.0,
        TRUE,
        22.3,
        TRUE,
        TRUE,
        -- 社会保障サービス
        TRUE,
        TRUE,
        TRUE,
        -- 目標・方針・署名
        NULL,
        NULL,
        TRUE,
        '自宅（妻と二人暮らし）',
        NULL,
        '【理学療法】: 股関節周囲筋力強化、バランス訓練、歩行訓練（歩行器→T字杖）、階段昇降訓練。\n【作業療法】: ADL指導（更衣、入浴、トイレ動作の工夫、自助具の活用）、家事動作訓練（調理、洗濯）、高所作業やかがむ動作の練習。',
        '田中 次郎',
        '山田 太郎',
        '佐藤 花子',
        '2025-10-04',
        '山田 太郎',
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        TRUE,
        '自宅',
        TRUE,
        '地域でのゴルフサークル活動への復帰。夫婦での旅行（国内）の再開。',
        TRUE,
        'ゴルフ、旅行、園芸（ベランダでの鉢植え程度）',
        -- 目標(活動)
        TRUE,
        TRUE,
        TRUE,
        '歩行器',
        TRUE,
        TRUE,
        TRUE,
        'T字杖',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        'かがむ動作や重いものを持つ際に介助が必要。',
        -- 対応を要する項目
        TRUE,
        '自宅内の段差解消、手すりの設置、浴槽への踏み台設置などを検討。',
        TRUE,
        '股関節屈曲制限対応の自助具（ソックスエイド、リーチャー、股関節用の長い靴べら）。',
        TRUE,
        '介護保険申請を検討。訪問リハビリテーション、デイサービス等の利用可能性を調査。',
        TRUE,
        '妻（介助負担の軽減、介護指導）',
        -- 具体的な対応方針
        NULL,
        NULL,
        NULL,
        NULL
    );


-- =================================================================
-- 4人目の患者: 高橋 芳子 (75歳 女性)
-- 疾患: 腰部脊柱管狭窄症（L4/5）術後
-- 背景: 術前の間欠性跛行、両下肢の痺れが改善。しかし、下肢筋力低下と
--       バランス能力低下が残存し、転倒への恐怖心がある。
--       高血圧、脂質異常症で内服治療中。物忘れを自覚している。
-- =================================================================
-- 1. 患者情報の登録
INSERT INTO patients (
        `patient_id`,
        `name`,
        `date_of_birth`,
        `gender`
    )
VALUES (
        4,
        '高橋 芳子',
        '1950-02-15',
        '女'
    );
-- 2. 担当職員の関連付け (山田さんと佐藤さんが担当)
INSERT INTO staff_patients (`staff_id`, `patient_id`)
VALUES (1, 4),
    (2, 4);
-- 3. リハビリテーション計画書の登録
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `created_by_staff_id`,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        `header_evaluation_date`,
        `header_disease_name_txt`,
        `header_onset_date`,
        `header_rehab_start_date`,
        `header_therapy_pt_chk`,
        `header_therapy_ot_chk`,
        `header_therapy_st_chk`,
        -- 併存疾患・リスク・特記事項
        `main_comorbidities_txt`,
        `main_risks_txt`,
        `main_contraindications_txt`,
        -- 心身機能・構造
        `func_risk_factors_chk`,
        `func_risk_hypertension_chk`,
        `func_risk_dyslipidemia_chk`,
        `func_pain_chk`,
        `func_pain_txt`,
        `func_muscle_weakness_chk`,
        `func_muscle_weakness_txt`,
        `func_motor_dysfunction_chk`,
        `func_motor_ataxia_chk`,
        `func_sensory_dysfunction_chk`,
        `func_sensory_superficial_chk`,
        `func_behavioral_psychiatric_disorder_chk`,
        `func_behavioral_psychiatric_disorder_txt`,
        `func_basic_standing_balance_chk`,
        `func_basic_standing_balance_assistance_chk`,
        -- ADL (FIM/BI) - 歩行能力とバランス低下により移動、入浴、更衣で介助を要する
        `adl_eating_fim_start_val`,
        `adl_eating_fim_current_val`,
        `adl_grooming_fim_start_val`,
        `adl_grooming_fim_current_val`,
        `adl_bathing_fim_start_val`,
        `adl_bathing_fim_current_val`,
        `adl_dressing_upper_fim_start_val`,
        `adl_dressing_upper_fim_current_val`,
        `adl_dressing_lower_fim_start_val`,
        `adl_dressing_lower_fim_current_val`,
        `adl_toileting_fim_start_val`,
        `adl_toileting_fim_current_val`,
        `adl_bladder_management_fim_start_val`,
        `adl_bladder_management_fim_current_val`,
        `adl_bowel_management_fim_start_val`,
        `adl_bowel_management_fim_current_val`,
        `adl_transfer_bed_chair_wc_fim_start_val`,
        `adl_transfer_bed_chair_wc_fim_current_val`,
        `adl_transfer_toilet_fim_start_val`,
        `adl_transfer_toilet_fim_current_val`,
        `adl_transfer_tub_shower_fim_start_val`,
        `adl_transfer_tub_shower_fim_current_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_start_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_current_val`,
        `adl_locomotion_stairs_fim_start_val`,
        `adl_locomotion_stairs_fim_current_val`,
        `adl_memory_fim_start_val`,
        `adl_memory_fim_current_val`,
        `adl_equipment_and_assistance_details_txt`,
        -- 栄養
        `nutrition_height_chk`,
        `nutrition_height_val`,
        `nutrition_weight_chk`,
        `nutrition_weight_val`,
        `nutrition_bmi_chk`,
        `nutrition_bmi_val`,
        `nutrition_method_oral_chk`,
        `nutrition_method_oral_meal_chk`,
        -- 社会保障サービス
        `social_care_level_status_chk`,
        `social_care_level_applying_chk`,
        -- 目標・方針・署名
        `goals_1_month_txt`,
        `goals_at_discharge_txt`,
        `goals_discharge_destination_chk`,
        `goals_discharge_destination_txt`,
        `policy_treatment_txt`,
        `policy_content_txt`,
        `signature_rehab_doctor_txt`,
        `signature_pt_txt`,
        `signature_ot_txt`,
        `signature_explanation_date`,
        `signature_explainer_txt`,
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        `goal_p_residence_chk`,
        `goal_p_residence_slct`,
        `goal_p_social_activity_chk`,
        `goal_p_social_activity_txt`,
        `goal_p_hobby_chk`,
        `goal_p_hobby_txt`,
        -- 目標(活動)
        `goal_a_outdoor_mobility_chk`,
        `goal_a_outdoor_mobility_assistance_chk`,
        `goal_a_outdoor_mobility_equipment_chk`,
        `goal_a_outdoor_mobility_equipment_txt`,
        `goal_a_bathing_chk`,
        `goal_a_bathing_assistance_chk`,
        `goal_a_bathing_assistance_transfer_chk`,
        `goal_a_housework_meal_chk`,
        `goal_a_housework_meal_partial_chk`,
        `goal_a_housework_meal_partial_txt`,
        -- 対応を要する項目
        `goal_s_psychological_support_chk`,
        `goal_s_psychological_support_txt`,
        `goal_s_env_home_modification_chk`,
        `goal_s_env_home_modification_txt`,
        `goal_s_env_care_insurance_chk`,
        `goal_s_env_care_insurance_details_txt`,
        `goal_s_3rd_party_main_caregiver_chk`,
        `goal_s_3rd_party_main_caregiver_txt`,
        -- 具体的な対応方針
        `goal_p_action_plan_txt`,
        `goal_a_action_plan_txt`,
        `goal_s_psychological_action_plan_txt`,
        `goal_s_env_action_plan_txt`
    )
VALUES (
        4,
        4,
        1,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        '2025-10-04',
        '腰部脊柱管狭窄症術後',
        '2025-09-18',
        '2025-09-21',
        TRUE,
        TRUE,
        FALSE,
        -- 併存疾患・リスク・特記事項
        '高血圧症、脂質異常症、骨粗鬆症、軽度認知障害（MCI）の疑い',
        '転倒・転落リスク高。術後せん妄のリスクあり。環境変化による混乱に注意。',
        '腰椎コルセットを日中装着。長時間の座位は避け、30分に一度は立ち上がるように指導。',
        -- 心身機能・構造
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        '術後創部痛は軽快。両下肢に痺れ（しびれ）感が残存。',
        TRUE,
        '両下肢、特に足関節背屈筋力の低下あり（MMT 3+）。体幹筋力も低下。',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        '転倒への恐怖心、活動への意欲低下が見られる。',
        TRUE,
        TRUE,
        -- ADL (FIM/BI)
        7,
        7,
        -- 整容
        6,
        6,
        -- 清拭
        3,
        4,
        -- 更衣(上半身)
        7,
        7,
        -- 更衣(下半身)
        4,
        5,
        -- トイレ動作
        5,
        6,
        -- 排尿管理
        7,
        7,
        -- 排便管理
        7,
        7,
        -- 移乗(ベッド・椅子・車椅子)
        5,
        6,
        -- 移乗(トイレ)
        5,
        6,
        -- 移乗(風呂)
        2,
        3,
        -- 移動(歩行・車椅子)
        3,
        4,
        -- 階段
        1,
        1,
        -- 記憶
        6,
        6,
        '歩行はシルバーカーを使用。入浴はシャワーチェアと手すりを使用し、一部介助が必要。靴下の着脱にリーチャーを使用。',
        -- 栄養
        TRUE,
        152.0,
        TRUE,
        48.0,
        TRUE,
        20.7,
        TRUE,
        TRUE,
        -- 社会保障サービス
        TRUE,
        TRUE,
        -- 目標・方針・署名
        'シルバーカーを使用して、病棟内トイレまで安全に往復できる。下肢筋力が向上し、椅子からの立ち上がりが安定する。',
        'T字杖歩行にて、自宅から近所の公民館（約300m）まで安全に移動できる。自宅での入浴動作が手すり使用にて自立する。',
        TRUE,
        '自宅（独居、近隣に長女在住）',
        '転倒予防を最優先とし、安全な移動方法の習得を目指す。成功体験を積み重ねることで、転倒への恐怖心を軽減し、活動性を高めるアプローチを行う。',
        '【理学療法】: 下肢・体幹筋力強化、バランス訓練、歩行訓練（シルバーカー→T字杖）。\n【作業療法】: ADL訓練（特に入浴、更衣）、福祉用具（シルバーカー、T字杖）の選定と使用訓練、家事動作訓練、認知課題（カレンダーの使用、服薬管理など）。',
        '田中 次郎',
        '山田 太郎',
        '佐藤 花子',
        '2025-10-04',
        '山田 太郎',
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        TRUE,
        '自宅',
        TRUE,
        '公民館での友人との茶話会への参加。',
        TRUE,
        'ベランダでのガーデニング、編み物。',
        -- 目標(活動)
        TRUE,
        TRUE,
        TRUE,
        'T字杖',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        '調理時の長時間の立位保持が困難。',
        -- 対応を要する項目
        TRUE,
        '転倒への不安が強く、日中の活動量が低下しがち。自信を持たせるような声かけと、具体的な成功体験のフィードバックが必要。',
        TRUE,
        '玄関、廊下、トイレ、浴室への手すり設置。玄関の上がり框に式台の設置を検討。',
        TRUE,
        '要介護認定を申請中。結果に基づき、訪問リハビリ、デイケア、福祉用具貸与の利用を計画。',
        TRUE,
        '長女（身体的介助、精神的サポート、各種手続きの支援）',
        -- 具体的な対応方針
        '退院前にケアマネージャー、福祉用具専門相談員と連携し、住宅改修と福祉用具の導入を完了させる。デイケアの見学・体験利用を調整する。',
        '屋外歩行訓練では、実際の公民館までの道のりを歩き、休憩場所の確認や危険箇所のチェックを行う。',
        '成功体験（「今日はここまで歩けましたね」等）を具体的に伝え、本人の自信回復を促す。また、不安が強い場合は臨床心理士への相談も検討する。',
        '住宅改修や介護保険サービスについて、本人と長女を交えてカンファレンスを実施し、退院後の生活について具体的な計画を共有する。'
    );


-- =_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=
-- 5人目の患者: 伊藤 久美子 (58歳 女性)
-- 疾患: 右肩腱板広範囲断裂術後
-- 背景: 趣味の裁縫や孫の世話に支障をきたし手術。関節リウマチの既往があり、
--       疼痛コントロールと関節保護が重要。パート（清掃業）への復帰を希望。
-- =_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=
-- 1. 患者情報の登録
INSERT INTO patients (
        `patient_id`,
        `name`,
        `date_of_birth`,
        `gender`
    )
VALUES (
        5,
        '伊藤 久美子',
        '1967-08-25',
        '女'
    );
-- 2. 担当職員の関連付け (山田さんと佐藤さんが担当)
INSERT INTO staff_patients (`staff_id`, `patient_id`)
VALUES (1, 5),
    (2, 5);
-- 3. リハビリテーション計画書の登録
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `created_by_staff_id`,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        `header_evaluation_date`,
        `header_disease_name_txt`,
        `header_onset_date`,
        `header_rehab_start_date`,
        `header_therapy_pt_chk`,
        `header_therapy_ot_chk`,
        `header_therapy_st_chk`,
        -- 併存疾患・リスク・特記事項
        `main_comorbidities_txt`,
        `main_risks_txt`,
        `main_contraindications_txt`,
        -- 心身機能・構造
        `func_risk_factors_chk`,
        `func_risk_omi_chk`,
        `func_pain_chk`,
        `func_pain_txt`,
        `func_rom_limitation_chk`,
        `func_rom_limitation_txt`,
        `func_muscle_weakness_chk`,
        `func_muscle_weakness_txt`,
        `func_basic_rolling_chk`,
        `func_basic_rolling_independent_chk`,
        -- ADL (FIM/BI) - 右上肢の不動により、更衣・清拭・食事などで一部介助が必要
        `adl_eating_fim_start_val`,
        `adl_eating_fim_current_val`,
        `adl_grooming_fim_start_val`,
        `adl_grooming_fim_current_val`,
        `adl_bathing_fim_start_val`,
        `adl_bathing_fim_current_val`,
        `adl_dressing_upper_fim_start_val`,
        `adl_dressing_upper_fim_current_val`,
        `adl_dressing_lower_fim_start_val`,
        `adl_dressing_lower_fim_current_val`,
        `adl_toileting_fim_start_val`,
        `adl_toileting_fim_current_val`,
        `adl_bladder_management_fim_start_val`,
        `adl_bladder_management_fim_current_val`,
        `adl_bowel_management_fim_start_val`,
        `adl_bowel_management_fim_current_val`,
        `adl_transfer_bed_chair_wc_fim_start_val`,
        `adl_transfer_bed_chair_wc_fim_current_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_start_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_current_val`,
        `adl_equipment_and_assistance_details_txt`,
        -- 栄養
        `nutrition_height_chk`,
        `nutrition_height_val`,
        `nutrition_weight_chk`,
        `nutrition_weight_val`,
        `nutrition_bmi_chk`,
        `nutrition_bmi_val`,
        `nutrition_method_oral_chk`,
        `nutrition_method_oral_meal_chk`,
        -- 目標・方針・署名
        `goals_1_month_txt`,
        `goals_at_discharge_txt`,
        `goals_discharge_destination_chk`,
        `goals_discharge_destination_txt`,
        `policy_treatment_txt`,
        `policy_content_txt`,
        `signature_rehab_doctor_txt`,
        `signature_pt_txt`,
        `signature_ot_txt`,
        `signature_explanation_date`,
        `signature_explainer_txt`,
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        `goal_p_residence_chk`,
        `goal_p_residence_slct`,
        `goal_p_return_to_work_chk`,
        `goal_p_return_to_work_status_slct`,
        `goal_p_household_role_chk`,
        `goal_p_household_role_txt`,
        `goal_p_hobby_chk`,
        `goal_p_hobby_txt`,
        -- 目標(活動)
        `goal_a_dressing_chk`,
        `goal_a_dressing_assistance_chk`,
        `goal_a_bathing_chk`,
        `goal_a_bathing_assistance_chk`,
        `goal_a_bathing_assistance_body_washing_chk`,
        `goal_a_housework_meal_chk`,
        `goal_a_housework_meal_partial_chk`,
        `goal_a_housework_meal_partial_txt`,
        -- 対応を要する項目
        `goal_s_env_assistive_device_chk`,
        `goal_s_env_assistive_device_txt`,
        `goal_s_3rd_party_main_caregiver_chk`,
        `goal_s_3rd_party_main_caregiver_txt`,
        -- 具体的な対応方針
        `goal_p_action_plan_txt`,
        `goal_a_action_plan_txt`,
        `goal_s_3rd_party_action_plan_txt`
    )
VALUES (
        5,
        5,
        2,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        '2025-10-04',
        '右肩腱板広範囲断裂術後、関節リウマチ',
        '2025-09-25',
        '2025-09-26',
        TRUE,
        TRUE,
        FALSE,
        -- 併存疾患・リスク・特記事項
        '関節リウマチ（メトトレキサート内服中）、シェーグレン症候群',
        '再断裂リスク、術後拘縮。リウマチによる他関節への炎症波及。',
        '術後装具（ウルトラスリング）を常時装着。医師の許可なく自動運動は禁忌。',
        -- 心身機能・構造
        TRUE,
        TRUE,
        TRUE,
        '右肩の術後痛（NRS 6/10）。リウマチによる手指の朝のこわばり。',
        TRUE,
        '右肩関節の他動可動域制限あり（前方挙上90度、外転60度）。',
        TRUE,
        '右肩関節周囲筋、特に棘上筋・棘下筋の筋力低下が著明。',
        TRUE,
        TRUE,
        -- ADL (FIM/BI)
        4,
        5,
        -- 整容
        3,
        4,
        -- 清拭
        2,
        3,
        -- 更衣(上半身)
        3,
        4,
        -- 更衣(下半身)
        7,
        7,
        -- トイレ動作
        6,
        6,
        -- 排尿管理
        7,
        7,
        -- 排便管理
        7,
        7,
        -- 移乗(ベッド・椅子・車椅子)
        7,
        7,
        -- 移動(歩行・車椅子)
        7,
        7,
        '食事は左手で摂取。更衣は前開きの服を着用し、一部介助が必要。洗髪、背中の清拭は全面介助。',
        -- 栄養
        TRUE,
        155.0,
        TRUE,
        52.0,
        TRUE,
        21.6,
        TRUE,
        TRUE,
        -- 目標・方針・署名
        '右肩の他動可動域が前方挙上120度、外転90度まで改善する。装具装着下で、更衣、食事動作が自立する。',
        '日常生活（調理、洗濯、掃除）が自助具などを活用し、ほぼ自立する。パートタイムでの仕事に復帰する。孫を（短時間なら）抱っこできる。',
        TRUE,
        '自宅（夫と二人暮らし）',
        'リウマチ内科医と連携し、関節リウマチの活動性をコントロールしながら、腱板の修復を妨げないよう慎重にリハビリを進める。関節保護の指導を徹底する。',
        '【理学療法】: 他動関節可動域訓練、振り子運動、肩甲骨周囲筋のトレーニング。\n【作業療法】: ADL指導（利き手交換、自助具の活用）、関節保護指導、趣味（裁縫）や仕事（清掃）を想定した動作練習。',
        '鈴木 一郎',
        '山田 太郎',
        '佐藤 花子',
        '2025-10-04',
        '佐藤 花子',
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        TRUE,
        '自宅',
        TRUE,
        '休職中',
        TRUE,
        '孫の世話（3歳）、調理、洗濯',
        TRUE,
        '裁縫（小物作り）、友人とのお茶',
        -- 目標(活動)
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        '包丁での硬い野菜の切断や、鍋の持ち運びが困難。',
        -- 対応を要する項目
        TRUE,
        '調理用の万能カフ、リーチャー、ボタンエイド、長柄ブラシなど。',
        TRUE,
        '夫（家事の協力、精神的サポート）',
        -- 具体的な対応方針
        '職場（清掃パート）の上司と連携し、復帰後の業務内容（右肩への負担が少ない作業への変更など）について相談・調整を行う。',
        '関節保護の観点から、日常生活での工夫（重いものを持たない、長時間の同一姿勢を避けるなど）を具体的に指導し、習慣化を図る。趣味の裁縫も、短時間から再開し、負担の少ない方法を一緒に考える。',
        '夫に対し、妻の病状と術後の注意点（特に禁忌事項）を説明し、家事分担や介助方法について協力を依頼する。'
    );


-- =================================================================
-- 6人目の患者: 渡辺 茂 (82歳 男性)
-- 疾患: 第12胸椎圧迫骨折 (骨粗鬆症性)
-- 背景: 介護老人保健施設に入所中。ベッドからのずり落ちで受傷。
--       軽度のアルツハイマー型認知症と難聴を合併しており、
--       コミュニケーションや指示の理解に時間を要することがある。
-- =================================================================
-- 1. 患者情報の登録
INSERT INTO patients (
        `patient_id`,
        `name`,
        `date_of_birth`,
        `gender`
    )
VALUES (
        6,
        '渡辺 茂',
        '1943-05-30',
        '男'
    );
-- 2. 担当職員の関連付け (山田さんと佐藤さんが担当)
INSERT INTO staff_patients (`staff_id`, `patient_id`)
VALUES (1, 6),
    (2, 6);
-- 3. リハビリテーション計画書の登録
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `created_by_staff_id`,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        `header_evaluation_date`,
        `header_disease_name_txt`,
        `header_onset_date`,
        `header_rehab_start_date`,
        `header_therapy_pt_chk`,
        `header_therapy_ot_chk`,
        `header_therapy_st_chk`,
        -- 併存疾患・リスク・特記事項
        `main_comorbidities_txt`,
        `main_risks_txt`,
        `main_contraindications_txt`,
        -- 心身機能・構造
        `func_pain_chk`,
        `func_pain_txt`,
        `func_muscle_weakness_chk`,
        `func_muscle_weakness_txt`,
        `func_sensory_dysfunction_chk`,
        `func_sensory_hearing_chk`,
        `func_higher_brain_dysfunction_chk`,
        `func_higher_brain_memory_chk`,
        `func_higher_brain_attention_chk`,
        `func_disorientation_chk`,
        `func_disorientation_txt`,
        `func_basic_getting_up_chk`,
        `func_basic_getting_up_assistance_chk`,
        `func_basic_standing_balance_chk`,
        `func_basic_standing_balance_assistance_chk`,
        -- ADL (FIM/BI) - 疼痛と廃用、認知機能低下により全般的に介助を要する
        `adl_eating_fim_start_val`,
        `adl_eating_fim_current_val`,
        `adl_grooming_fim_start_val`,
        `adl_grooming_fim_current_val`,
        `adl_bathing_fim_start_val`,
        `adl_bathing_fim_current_val`,
        `adl_dressing_upper_fim_start_val`,
        `adl_dressing_upper_fim_current_val`,
        `adl_dressing_lower_fim_start_val`,
        `adl_dressing_lower_fim_current_val`,
        `adl_toileting_fim_start_val`,
        `adl_toileting_fim_current_val`,
        `adl_bladder_management_fim_start_val`,
        `adl_bladder_management_fim_current_val`,
        `adl_bowel_management_fim_start_val`,
        `adl_bowel_management_fim_current_val`,
        `adl_transfer_bed_chair_wc_fim_start_val`,
        `adl_transfer_bed_chair_wc_fim_current_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_start_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_current_val`,
        `adl_comprehension_fim_start_val`,
        `adl_comprehension_fim_current_val`,
        `adl_expression_fim_start_val`,
        `adl_expression_fim_current_val`,
        `adl_memory_fim_start_val`,
        `adl_memory_fim_current_val`,
        `adl_equipment_and_assistance_details_txt`,
        -- 栄養
        `nutrition_height_chk`,
        `nutrition_height_val`,
        `nutrition_weight_chk`,
        `nutrition_weight_val`,
        `nutrition_bmi_chk`,
        `nutrition_bmi_val`,
        `nutrition_method_oral_chk`,
        `nutrition_method_oral_meal_chk`,
        -- 社会保障サービス
        `social_care_level_status_chk`,
        `social_care_level_care_slct`,
        `social_care_level_care_num3_slct`,
        -- 目標・方針・署名
        `goals_1_month_txt`,
        `goals_at_discharge_txt`,
        `goals_discharge_destination_chk`,
        `goals_discharge_destination_txt`,
        `policy_treatment_txt`,
        `policy_content_txt`,
        `signature_rehab_doctor_txt`,
        `signature_pt_txt`,
        `signature_ot_txt`,
        `signature_explanation_date`,
        `signature_explainer_txt`,
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        `goal_p_residence_chk`,
        `goal_p_residence_slct`,
        `goal_p_social_activity_chk`,
        `goal_p_social_activity_txt`,
        `goal_p_hobby_chk`,
        `goal_p_hobby_txt`,
        -- 目標(活動)
        `goal_a_indoor_mobility_chk`,
        `goal_a_indoor_mobility_assistance_chk`,
        `goal_a_indoor_mobility_equipment_chk`,
        `goal_a_indoor_mobility_equipment_txt`,
        `goal_a_toileting_chk`,
        `goal_a_toileting_assistance_chk`,
        `goal_a_eating_chk`,
        `goal_a_eating_independent_chk`,
        -- 対応を要する項目
        `goal_s_psychological_support_chk`,
        `goal_s_psychological_support_txt`,
        `goal_s_env_care_insurance_chk`,
        `goal_s_env_care_insurance_health_facility_chk`,
        `goal_s_3rd_party_main_caregiver_chk`,
        `goal_s_3rd_party_main_caregiver_txt`,
        -- 具体的な対応方針
        `goal_p_action_plan_txt`,
        `goal_a_action_plan_txt`,
        `goal_s_psychological_action_plan_txt`,
        `goal_s_3rd_party_action_plan_txt`
    )
VALUES (
        6,
        6,
        1,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        '2025-10-04',
        '第12胸椎圧迫骨折（骨粗鬆症性）、アルツハイマー型認知症',
        '2025-09-12',
        '2025-09-19',
        TRUE,
        TRUE,
        FALSE,
        -- 併存疾患・リスク・特記事項
        'アルツハイマー型認知症（軽度）、両側感音性難聴、便秘症',
        '転倒リスク（極めて高い）。認知機能低下による指示理解の困難さ。再骨折のリスク。',
        '体幹装具（硬性コルセット）を常時装着。離床・移乗時は必ずナースコール。急な体幹の屈曲・回旋は禁忌。',
        -- 心身機能・構造
        TRUE,
        '体動時・座位保持時の背部痛（NRS 5/10）。安静臥床で軽快。',
        TRUE,
        '長期臥床による全身の筋力低下（廃用症候群）。特に体幹・下肢筋が顕著。',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        '時間や場所の見当識が不確かになることがある。',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        -- ADL (FIM/BI)
        5,
        6,
        -- 整容
        2,
        3,
        -- 清拭
        1,
        2,
        -- 更衣(上半身)
        2,
        3,
        -- 更衣(下半身)
        1,
        2,
        -- トイレ動作
        1,
        2,
        -- 排尿管理
        4,
        4,
        -- 排便管理
        4,
        4,
        -- 移乗(ベッド・椅子・車椅子)
        2,
        3,
        -- 移動(歩行・車椅子)
        1,
        2,
        -- 理解
        5,
        5,
        -- 表出
        6,
        6,
        -- 記憶
        4,
        5,
        '移動は車椅子（全介助）。ポータブルトイレ使用。食事は刻み食・トロミ付き。',
        -- 栄養
        TRUE,
        160.0,
        TRUE,
        50.0,
        TRUE,
        19.5,
        TRUE,
        TRUE,
        -- 社会保障サービス
        TRUE,
        TRUE,
        TRUE,
        -- 目標・方針・署名
        'コルセット装着下で、端座位が30分安定して可能となる。車椅子への移乗が軽介助で可能となる。',
        '歩行器を用いて、居室から食堂まで見守り歩行が可能となる。施設でのレクリエーション（書道、カラオケ）に車椅子で参加できる。',
        TRUE,
        '入所中の介護老人保健施設へ退所',
        '疼痛管理を最優先とし、二次骨折を予防する。認知症の特性を理解し、簡潔で分かりやすい言葉で、繰り返し指示を伝える。本人のペースに合わせたリハビリを提供する。',
        '【理学療法】: 疼痛のない範囲での体幹・下肢筋力強化、基本動作訓練（寝返り、起き上がり）、移乗訓練、歩行訓練。\n【作業療法】: ADL訓練、認知機能低下の進行予防（現実見当識訓練、回想法）、レクリエーション活動への参加支援。',
        '田中 次郎',
        '山田 太郎',
        '佐藤 花子',
        '2025-10-04',
        '山田 太郎',
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        TRUE,
        '介護老人保健施設',
        TRUE,
        '施設内のレクリエーション（書道、カラオケ）への参加。',
        TRUE,
        '書道、テレビ鑑賞（特に時代劇）',
        -- 目標(活動)
        TRUE,
        TRUE,
        TRUE,
        '歩行器',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        -- 対応を要する項目
        TRUE,
        '疼痛や認知機能低下により、リハビリへの拒否が見られることがある。安心できる環境作りと、本人の好きな活動（時代劇の話など）を導入し、意欲を引き出す工夫が必要。',
        TRUE,
        TRUE,
        TRUE,
        '施設職員（介護士、看護師、ケアマネージャー）、長男（キーパーソン）',
        -- 具体的な対応方針
        '退院前に施設職員とカンファレンスを実施し、リハビリの進行状況、介助方法、再骨折予防の注意点を共有する。施設の環境（ベッドの高さ、手すりの位置など）を再評価する。',
        '本人の得意な書道や好きな時代劇の話題をリハビリに取り入れ、楽しみながら機能訓練ができるように工夫する。短い時間で集中して行い、成功体験を積ませる。',
        '認知症の症状や対応について、長男へ改めて説明し、今後の施設での生活や医療に関する意思決定のサポートを依頼する。',
        '施設職員と密に連携し、日中の活動性を高めるためのアプローチ（離床時間の延長、レクリエーションへの誘導など）を統一して行う。'
    );


-- =================================================================
-- 7人目の患者: 中村 千代 (92歳 女性)
-- 疾患: 右大腿骨頸部骨折術後
-- 背景: 自宅で転倒し受傷。手術は成功したが、術後のせん妄を発症。
--       中等度のアルツハイマー型認知症があり、リハビリへの協力が
--       得られにくいことがある。うっ血性心不全の既往あり。
-- =================================================================
-- 1. 患者情報の登録
INSERT INTO patients (
        `patient_id`,
        `name`,
        `date_of_birth`,
        `gender`
    )
VALUES (
        7,
        '中村 千代',
        '1933-01-20',
        '女'
    );
-- 2. 担当職員の関連付け (山田さんと佐藤さんが担当)
INSERT INTO staff_patients (`staff_id`, `patient_id`)
VALUES (1, 7),
    (2, 7);
-- 3. リハビリテーション計画書の登録
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `created_by_staff_id`,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        `header_evaluation_date`,
        `header_disease_name_txt`,
        `header_onset_date`,
        `header_rehab_start_date`,
        `header_therapy_pt_chk`,
        `header_therapy_ot_chk`,
        `header_therapy_st_chk`,
        -- 併存疾患・リスク・特記事項
        `main_comorbidities_txt`,
        `main_risks_txt`,
        `main_contraindications_txt`,
        -- 心身機能・構造
        `func_circulatory_disorder_chk`,
        `func_circulatory_ef_chk`,
        `func_circulatory_ef_val`,
        `func_pressure_ulcer_chk`,
        `func_pressure_ulcer_txt`,
        `func_pain_chk`,
        `func_pain_txt`,
        `func_rom_limitation_chk`,
        `func_rom_limitation_txt`,
        `func_muscle_weakness_chk`,
        `func_muscle_weakness_txt`,
        `func_higher_brain_dysfunction_chk`,
        `func_higher_brain_memory_chk`,
        `func_disorientation_chk`,
        `func_disorientation_txt`,
        `func_basic_rolling_chk`,
        `func_basic_rolling_assistance_chk`,
        -- ADL (FIM/BI) - ほぼ全項目で全介助レベル
        `adl_eating_fim_start_val`,
        `adl_eating_fim_current_val`,
        `adl_grooming_fim_start_val`,
        `adl_grooming_fim_current_val`,
        `adl_bathing_fim_start_val`,
        `adl_bathing_fim_current_val`,
        `adl_dressing_upper_fim_start_val`,
        `adl_dressing_upper_fim_current_val`,
        `adl_dressing_lower_fim_start_val`,
        `adl_dressing_lower_fim_current_val`,
        `adl_toileting_fim_start_val`,
        `adl_toileting_fim_current_val`,
        `adl_bladder_management_fim_start_val`,
        `adl_bladder_management_fim_current_val`,
        `adl_bowel_management_fim_start_val`,
        `adl_bowel_management_fim_current_val`,
        `adl_transfer_bed_chair_wc_fim_start_val`,
        `adl_transfer_bed_chair_wc_fim_current_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_start_val`,
        `adl_locomotion_walk_walkingAids_wc_fim_current_val`,
        `adl_comprehension_fim_start_val`,
        `adl_comprehension_fim_current_val`,
        `adl_equipment_and_assistance_details_txt`,
        -- 栄養
        `nutrition_height_chk`,
        `nutrition_height_val`,
        `nutrition_weight_chk`,
        `nutrition_weight_val`,
        `nutrition_bmi_chk`,
        `nutrition_bmi_val`,
        `nutrition_method_oral_chk`,
        `nutrition_method_oral_meal_chk`,
        `nutrition_swallowing_diet_slct`,
        `nutrition_swallowing_diet_code_txt`,
        -- 社会保障サービス
        `social_care_level_status_chk`,
        `social_care_level_care_slct`,
        `social_care_level_care_num5_slct`,
        -- 目標・方針・署名
        `goals_1_month_txt`,
        `goals_at_discharge_txt`,
        `goals_discharge_destination_chk`,
        `goals_discharge_destination_txt`,
        `policy_treatment_txt`,
        `policy_content_txt`,
        `signature_rehab_doctor_txt`,
        `signature_pt_txt`,
        `signature_ot_txt`,
        `signature_explanation_date`,
        `signature_explainer_txt`,
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        `goal_p_residence_chk`,
        `goal_p_residence_slct`,
        `goal_p_social_activity_chk`,
        `goal_p_social_activity_txt`,
        `goal_p_hobby_chk`,
        `goal_p_hobby_txt`,
        -- 目標(活動)
        `goal_a_bed_mobility_chk`,
        `goal_a_bed_mobility_assistance_chk`,
        `goal_a_eating_chk`,
        `goal_a_eating_assistance_chk`,
        -- 対応を要する項目
        `goal_s_psychological_support_chk`,
        `goal_s_psychological_support_txt`,
        `goal_s_env_care_insurance_chk`,
        `goal_s_env_care_insurance_nursing_home_chk`,
        `goal_s_3rd_party_main_caregiver_chk`,
        `goal_s_3rd_party_main_caregiver_txt`,
        -- 具体的な対応方針
        `goal_a_action_plan_txt`,
        `goal_s_psychological_action_plan_txt`,
        `goal_s_3rd_party_action_plan_txt`
    )
VALUES (
        7,
        7,
        1,
        -- 【1枚目】----------------------------------------------------
        -- ヘッダー・基本情報
        '2025-10-04',
        '右大腿骨頸部骨折術後、アルツハイマー型認知症',
        '2025-09-15',
        '2025-09-20',
        TRUE,
        TRUE,
        FALSE,
        -- 併存疾患・リスク・特記事項
        'うっ血性心不全(CHF)、高度骨粗鬆症、高血圧症、中等度アルツハイマー型認知症',
        '転倒・再骨折リスク（極めて高い）。心不全増悪。認知症によるリハビリへの不参加・混乱。褥瘡発生リスク。',
        '医師の指示に基づく荷重制限の厳守。心機能の指標（血圧、SpO2）を常にモニタリングし、増悪の兆候があれば即時中止する。',
        -- 心身機能・構造
        TRUE,
        TRUE,
        45,
        TRUE,
        '仙骨部に発赤あり（d1）。',
        TRUE,
        '右股関節の術後痛。体動時に表情をしかめることがある。非言語的な疼痛サインに注意。',
        TRUE,
        '両下肢に関節拘縮あり。特に膝伸展制限（-20度）。',
        TRUE,
        '全身の廃用性筋力低下が著明 (MMT 2レベル)。',
        TRUE,
        TRUE,
        TRUE,
        '時間、場所の見当識障害が常時あり。人物誤認も時折みられる。',
        TRUE,
        TRUE,
        -- ADL (FIM/BI)
        1,
        2,
        -- 整容
        1,
        1,
        -- 清拭
        1,
        1,
        -- 更衣(上半身)
        1,
        1,
        -- 更衣(下半身)
        1,
        1,
        -- トイレ動作
        1,
        1,
        -- 排尿管理
        1,
        1,
        -- 排便管理
        1,
        1,
        -- 移乗(ベッド・椅子・車椅子)
        1,
        1,
        -- 移動(歩行・車椅子)
        1,
        1,
        -- 理解
        3,
        4,
        '全介助。食事は一部介助で経口摂取。移動はリクライニング式車椅子。排泄はオムツ使用。',
        -- 栄養
        TRUE,
        145.0,
        TRUE,
        38.0,
        TRUE,
        18.1,
        TRUE,
        TRUE,
        '嚥下調整食3',
        '3-1',
        -- 社会保障サービス
        TRUE,
        TRUE,
        TRUE,
        -- 目標・方針・署名
        'ベッド上での安楽な座位（ギャッジアップ60度）が30分以上可能となる。褥瘡の増悪がない。',
        '苦痛なく日中をリクライニング車椅子で過ごせる。家族との面会時に、穏やかな表情でコミュニケーションが図れる。',
        TRUE,
        '介護老人保健施設または特別養護老人ホームへの入所を検討中',
        'QOL（生活の質）の維持・向上を主目的とする。疼痛管理と褥瘡予防を徹底し、本人が穏やかに過ごせる環境を提供する。家族の意向を尊重し、今後の療養先についてMSWと連携して支援する。',
        '【理学療法/作業療法共通】: 拘縮予防のための他動関節可動域訓練、褥瘡予防のための体位変換、安楽なシーティング（座位姿勢）の調整。',
        '田中 次郎',
        '山田 太郎',
        '佐藤 花子',
        '2025-10-04',
        '山田 太郎',
        -- 【2枚目】----------------------------------------------------
        -- 目標(参加)
        TRUE,
        '介護老人保健施設',
        TRUE,
        '施設のデイルームで過ごす時間を設ける。',
        TRUE,
        '音楽鑑賞（昔の歌謡曲）、家族の写真を見ること。',
        -- 目標(活動)
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        -- 対応を要する項目
        TRUE,
        '認知症の周辺症状（BPSD）として、夕方になると不安が強くなる（夕暮れ症候群）。リハビリへの拒否が強いことがある。',
        TRUE,
        TRUE,
        TRUE,
        '長男夫婦（キーパーソン、意思決定者）',
        -- 具体的な対応方針
        'スライディングボードやリフトなどの福祉用具を活用した移乗練習。ベッド上でのポジショニングと体位変換の徹底。',
        '本人の好きな音楽を聴きながら、穏やかな雰囲気の中でリハビリを行う。非薬物療法（バリデーション療法など）を用いて、不安の軽減を図る。',
        '長男夫婦と定期的に面談し、病状と今後の見通しを共有する。施設入所に関する情報提供と手続きをMSWが中心となって進める。'
    );








-- 完了メッセージ
SELECT 'データベースとテーブルの作成、サンプルデータの挿入が完了しました。' AS 'Status';
