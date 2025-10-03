-- =================================================================
-- リハビリテーション実施計画書 自動作成システム用データベーススキーマ
-- =================================================================
-- TODO あくまでもテスト用に作ったものなので、作り直す必要があります。


-- 1. データベースの作成
CREATE DATABASE IF NOT EXISTS rehab_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE rehab_db;


-- 既存のテーブルを削除して再作成（開発用）
-- 外部キー制約を考慮し、参照しているテーブルから先に削除する
DROP TABLE IF EXISTS `liked_item_details`, `suggestion_likes`, `staff_patients`, `rehabilitation_plans`;
-- 参照されているテーブルを後に削除する
DROP TABLE IF EXISTS `staff`, `patients`;



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
-- 4.5. いいね一時保存テーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS suggestion_likes (
    `patient_id` INT NOT NULL,
    `item_key` VARCHAR(255) NOT NULL,
    `liked_model` VARCHAR(50) NOT NULL,
    `staff_id` INT NOT NULL,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`patient_id`, `item_key`, `liked_model`),
    FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`) ON DELETE CASCADE,
    FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='AI提案への「いいね」を一時的に保存するテーブル';

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
-- 6. いいね詳細情報テーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS liked_item_details (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT 'レコードを一意に識別するID',
    `rehabilitation_plan_id` INT NOT NULL COMMENT '関連する計画書のID',
    `staff_id` INT NOT NULL COMMENT 'いいねをした職員のID',
    `item_key` VARCHAR(255) NOT NULL COMMENT 'いいねされた項目キー',
    `liked_model` VARCHAR(50) NOT NULL COMMENT 'いいねされたモデル (general/specialized)',
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


-- -- =================================================================
-- -- 6. サンプルデータの挿入 本番環境でのデータベース作成では使わないでください。
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



-- 患者
INSERT INTO patients (`patient_id`, `name`, `date_of_birth`, `gender`) VALUES
(1, '田中 太郎', '1955-04-10', '男'),
(2, '鈴木 花子', '1968-08-20', '女'),
(3, '佐藤 愛子', '1950-11-03', '女'),
(4, '高橋 健太', '1995-07-22', '男'),
(5, '伊藤 正', '1945-01-15', '男')
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

-- 担当割り当て
INSERT INTO staff_patients (`staff_id`, `patient_id`) VALUES
(1, 1), (1, 3), (1, 5),
(2, 2), (2, 4)
ON DUPLICATE KEY UPDATE `staff_id`=`staff_id`;

-- 各患者の最新情報（計画書作成の元データ）
-- No.1 田中 太郎 (脳卒中)
INSERT INTO rehabilitation_plans (`patient_id`, `created_by_staff_id`, `header_evaluation_date`, `header_disease_name_txt`, `header_onset_date`, `header_rehab_start_date`, `header_therapy_pt_chk`, `header_therapy_ot_chk`, `header_therapy_st_chk`, `func_risk_hypertension_chk`, `func_motor_paralysis_chk`, `func_speech_aphasia_chk`, `func_higher_brain_dysfunction_chk`, `adl_eating_fim_current_val`, `adl_transfer_bed_chair_wc_fim_current_val`, `adl_locomotion_walk_walkingAids_wc_fim_current_val`)
VALUES (1, 1, '2025-08-15', '脳梗塞による左片麻痺、失語症', '2025-06-20', '2025-06-22', TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, TRUE, 4, 3, 2)
ON DUPLICATE KEY UPDATE `header_disease_name_txt` = VALUES(`header_disease_name_txt`);

-- No.2 鈴木 花子 (肩関節)
INSERT INTO rehabilitation_plans (`patient_id`, `created_by_staff_id`, `header_evaluation_date`, `header_disease_name_txt`, `header_onset_date`, `header_rehab_start_date`, `header_therapy_pt_chk`, `header_therapy_ot_chk`, `func_pain_chk`, `func_pain_txt`, `func_rom_limitation_chk`, `func_rom_limitation_txt`, `func_muscle_weakness_chk`, `adl_grooming_fim_current_val`, `adl_dressing_upper_fim_current_val`, `adl_bathing_fim_current_val`)
VALUES (2, 2, '2025-08-12', '右肩腱板断裂術後', '2025-07-10', '2025-07-11', TRUE, TRUE, TRUE, '安静時痛は軽減したが、運動時に鋭い痛みが残存。', TRUE, '右肩関節 挙上100°、外旋20°', TRUE, 4, 3, 3)
ON DUPLICATE KEY UPDATE `header_disease_name_txt` = VALUES(`header_disease_name_txt`);

-- No.3 佐藤 愛子 (股関節)
INSERT INTO rehabilitation_plans (`patient_id`, `created_by_staff_id`, `header_evaluation_date`, `header_disease_name_txt`, `header_onset_date`, `header_rehab_start_date`, `header_therapy_pt_chk`, `func_risk_obesity_chk`, `func_pain_chk`, `func_pain_txt`, `func_muscle_weakness_chk`, `func_muscle_weakness_txt`, `adl_transfer_bed_chair_wc_fim_current_val`, `adl_locomotion_walk_walkingAids_wc_fim_current_val`, `adl_locomotion_stairs_fim_current_val`)
VALUES (3, 1, '2025-08-16', '左変形性股関節症（THA後）', '2025-07-25', '2025-07-26', TRUE, TRUE, TRUE, '長距離歩行後に左股関節の鈍痛あり。', TRUE, '左股関節外転筋力（MMT4レベル）', 5, 4, 2)
ON DUPLICATE KEY UPDATE `header_disease_name_txt` = VALUES(`header_disease_name_txt`);

-- No.4 高橋 健太 (膝関節)
INSERT INTO rehabilitation_plans (`patient_id`, `created_by_staff_id`, `header_evaluation_date`, `header_disease_name_txt`, `header_onset_date`, `header_rehab_start_date`, `header_therapy_pt_chk`, `func_muscle_weakness_chk`, `func_muscle_weakness_txt`, `adl_locomotion_walk_walkingAids_wc_fim_current_val`, `adl_locomotion_stairs_fim_current_val`, `goal_p_hobby_chk`, `goal_p_hobby_txt`)
VALUES (4, 2, '2025-08-14', '右膝前十字靭帯再建術後', '2025-07-01', '2025-07-02', TRUE, TRUE, '右大腿四頭筋に著明な筋力低下あり。', 6, 5, TRUE, 'バスケットボールへの競技復帰を強く希望。')
ON DUPLICATE KEY UPDATE `header_disease_name_txt` = VALUES(`header_disease_name_txt`);

-- No.5 伊藤 正 (股関節・膝関節)
INSERT INTO rehabilitation_plans (`patient_id`, `created_by_staff_id`, `header_evaluation_date`, `header_disease_name_txt`, `header_rehab_start_date`, `header_therapy_pt_chk`, `func_risk_hypertension_chk`, `func_pain_chk`, `func_pain_txt`, `func_contracture_deformity_chk`, `func_contracture_deformity_txt`, `adl_locomotion_walk_walkingAids_wc_fim_current_val`, `adl_locomotion_stairs_fim_current_val`)
VALUES (5, 1, '2025-08-10', '変形性股関節症、変形性膝関節症（両側）', '2025-08-01', TRUE, TRUE, TRUE, '歩行開始時、立ち上がり時に両股・膝関節に痛みあり。', TRUE, '両膝関節に軽度の屈曲拘縮あり。', 4, 1)
ON DUPLICATE KEY UPDATE `header_disease_name_txt` = VALUES(`header_disease_name_txt`);


-- 完了メッセージ
SELECT 'データベースとテーブルの作成、サンプルデータの挿入が完了しました。' AS 'Status';
