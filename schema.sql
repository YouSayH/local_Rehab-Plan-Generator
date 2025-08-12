-- =================================================================
-- リハビリテーション実施計画書 自動作成システム用データベーススキーマ
-- =================================================================
--- TODO あくまでもテスト用に作ったものなので、作り直す必要があります。

-- 1. データベースの作成
CREATE DATABASE IF NOT EXISTS rehab_db CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE rehab_db;


-- =================================================================
-- 2. 患者マスターテーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS patients (
    `patient_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '患者を一意に識別するID',
    `name` VARCHAR(255) NOT NULL COMMENT '患者氏名',
    `date_of_birth` DATE NULL COMMENT '生年月日',
    `gender` VARCHAR(10) NULL COMMENT '性別 (例: 男, 女)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時'
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '患者の基本情報を格納するマスターテーブル';


-- =================================================================
-- 3. リハビリテーション計画書テーブル
-- =================================================================
CREATE TABLE IF NOT EXISTS rehabilitation_plans (
    `plan_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '計画書を一意に識別するID',
    `patient_id` INT NOT NULL COMMENT '外部キー (patientsテーブルを参照)',
    -- ヘッダー情報
    `creation_date` DATE NOT NULL COMMENT '計画書の作成日',
    `main_disease` VARCHAR(255) NULL COMMENT '算定病名',
    `evaluation_date` DATE NULL COMMENT '計画評価実施日',
    `onset_date` DATE NULL COMMENT '発症日・手術日',
    `rehab_start_date` DATE NULL COMMENT 'リハビリ開始日',
    -- 実施リハ (チェックボックス)
    `is_physical_therapy` BOOLEAN DEFAULT FALSE COMMENT '理学療法',
    `is_occupational_therapy` BOOLEAN DEFAULT FALSE COMMENT '作業療法',
    `is_speech_therapy` BOOLEAN DEFAULT FALSE COMMENT '言語聴覚療法',
    -- 担当者所感 (Webフォームからの入力)
    `therapist_notes` TEXT NULL COMMENT '担当者の所感',
    -- AI生成・担当者編集後のテキスト
    `ai_risks` TEXT NULL COMMENT '安静度・リスク',
    `ai_contraindications` TEXT NULL COMMENT '禁忌・特記事項',
    `ai_policy` TEXT NULL COMMENT '治療方針',
    `ai_content` TEXT NULL COMMENT '治療内容',
    -- 心身機能・構造 (チェックボックス)
    `has_consciousness_disorder` BOOLEAN DEFAULT FALSE COMMENT '意識障害',
    `has_respiratory_disorder` BOOLEAN DEFAULT FALSE COMMENT '呼吸機能障害',
    `has_swallowing_disorder` BOOLEAN DEFAULT FALSE COMMENT '嚥下機能障害',
    `has_joint_rom_limitation` BOOLEAN DEFAULT FALSE COMMENT '関節可動域制限',
    `has_muscle_weakness` BOOLEAN DEFAULT FALSE COMMENT '筋力低下',
    `has_paralysis` BOOLEAN DEFAULT FALSE COMMENT '麻痺',

    -- TODO (ここに他の心身機能項目をBOOLEANで追加...)
    -- FIMスコア (開始時)
    `fim_start_eating` INT NULL,
    `fim_start_grooming` INT NULL,
    `fim_start_total` INT NULL,
    -- TODO (ここに他の全てのFIM開始時項目を追加...)
    -- FIMスコア (現在)
    `fim_current_eating` INT NULL,
    `fim_current_grooming` INT NULL,
    `fim_current_total` INT NULL,
    -- TODO (ここに他の全てのFIM現在項目を追加...)
    -- 外部キー制約
    INDEX `idx_patient_id` (`patient_id`),
    CONSTRAINT `fk_patient_id` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '作成されたリハビリテーション計画書の履歴';


-- =================================================================
-- 4. 職員マスターテーブル (管理者機能のため追加)
-- =================================================================
CREATE TABLE IF NOT EXISTS staff (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '職員を一意に識別するID',
    `username` VARCHAR(255) NOT NULL UNIQUE COMMENT 'ログイン用のユーザー名',
    `password` VARCHAR(255) NOT NULL COMMENT 'ハッシュ化されたパスワード',
    `role` VARCHAR(50) NOT NULL DEFAULT 'general' COMMENT '役割 (admin, generalなど)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時'
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '職員（アプリのユーザー）情報を格納するテーブル';


-- =================================================================
-- 5. 職員と患者の関連テーブル (担当者機能のため追加)
-- =================================================================
CREATE TABLE IF NOT EXISTS staff_patients (
    `staff_id` INT NOT NULL COMMENT '外部キー (staffテーブルを参照)',
    `patient_id` INT NOT NULL COMMENT '外部キー (patientsテーブルを参照)',
    PRIMARY KEY (`staff_id`, `patient_id`),
    CONSTRAINT `fk_staff_id` FOREIGN KEY (`staff_id`) REFERENCES `staff` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_staff_patient_id` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`patient_id`) ON DELETE CASCADE
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_general_ci COMMENT = '職員と担当患者の関連を管理する中間テーブル';


-- =================================================================
-- 6. サンプルデータの挿入 (元の状態に復元 + 職員情報を追加)　本番環境でのデータベース作成では使わないでください。
-- =================================================================
-- 患者1: 田中 太郎さん
INSERT INTO patients (`patient_id`, `name`, `date_of_birth`, `gender`)
VALUES (1, '田中 太郎', '1955-04-10', '男') ON DUPLICATE KEY
UPDATE `name` = `name`;
-- 田中さんの計画書 (過去と現在)
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `creation_date`,
        `main_disease`,
        `is_physical_therapy`,
        `has_paralysis`,
        `fim_current_total`
    )
VALUES (101, 1, '2025-06-15', '脳梗塞右片麻痺', TRUE, TRUE, 85) ON DUPLICATE KEY
UPDATE `main_disease` = `main_disease`;
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `creation_date`,
        `main_disease`,
        `is_physical_therapy`,
        `is_occupational_therapy`,
        `has_paralysis`,
        `has_muscle_weakness`,
        `fim_current_total`
    )
VALUES (
        102,
        1,
        '2025-07-15',
        '脳梗塞右片麻痺',
        TRUE,
        TRUE,
        TRUE,
        TRUE,
        92
    ) ON DUPLICATE KEY
UPDATE `main_disease` = `main_disease`;


-- 患者2: 鈴木 花子さん
INSERT INTO patients (`patient_id`, `name`, `date_of_birth`, `gender`)
VALUES (2, '鈴木 花子', '1960-08-20', '女') ON DUPLICATE KEY
UPDATE `name` = `name`;
-- 鈴木さんの計画書
INSERT INTO rehabilitation_plans (
        `plan_id`,
        `patient_id`,
        `creation_date`,
        `main_disease`,
        `is_physical_therapy`,
        `has_joint_rom_limitation`,
        `fim_current_total`
    )
VALUES (
        201,
        2,
        '2025-07-10',
        '大腿骨頸部骨折（術後）',
        TRUE,
        TRUE,
        78
    ) ON DUPLICATE KEY
UPDATE `main_disease` = `main_disease`;


-- 職員1: yamada さん (管理者 / パスワード: adminpass)
INSERT INTO staff (`id`, `username`, `password`, `role`)
VALUES (
        1,
        'yamada',
        'scrypt:32768:8:1$JlKJ01aekkBsObaa$73e73e06efc0f9722f78fb12ef78114b54062b48d754750a685681577bb44a6ef06d534c7d32717a1da496ba60b982cb87455c6a060e469b76506a1091435131',
        'admin'
    ) ON DUPLICATE KEY
UPDATE `username` = `username`,
    `role` = 'admin';
-- 職員2: sato さん (一般 / パスワード: password123)
INSERT INTO staff (`id`, `username`, `password`, `role`)
VALUES (
        2,
        'sato',
        'scrypt:32768:8:1$rcfwDMziQwokAhOv$c34b18e7582b6d004091f3bd4c647d98469959ccd1919f3d76b6020065d5205b3171f324641c0629b6b0931ea239215bb457bf2eed028431427d30749ca67972',
        'general'
    ) ON DUPLICATE KEY
UPDATE `username` = `username`,
    `role` = 'general';
    
-- 担当の割り当て
INSERT INTO staff_patients (`staff_id`, `patient_id`) VALUES (1, 1) ON DUPLICATE KEY UPDATE `staff_id`=`staff_id`; -- yamadaは田中さんを担当
INSERT INTO staff_patients (`staff_id`, `patient_id`) VALUES (2, 2) ON DUPLICATE KEY UPDATE `staff_id`=`staff_id`; -- satoは鈴木さんを担当

-- 完了メッセージ
SELECT 'データベースとテーブルの作成、サンプルデータの挿入が完了しました。' AS 'Status';