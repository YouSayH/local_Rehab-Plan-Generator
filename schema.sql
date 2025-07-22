-- =================================================================
-- リハビリテーション実施計画書 自動作成システム用データベーススキーマ
-- =================================================================

-- 1. データベースの作成
-- データベース 'rehab_db' が存在しない場合のみ作成する
CREATE DATABASE IF NOT EXISTS rehab_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_general_ci;

-- 作成したデータベースを使用する
USE rehab_db;


-- 2. 患者マスターテーブルの作成
CREATE TABLE IF NOT EXISTS patients (
    `patient_id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '患者を一意に識別するID',
    `name` VARCHAR(255) NOT NULL COMMENT '患者氏名',
    `date_of_birth` DATE NULL COMMENT '生年月日',
    `gender` VARCHAR(10) NULL COMMENT '性別 (例: 男, 女)',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'レコード作成日時'
) ENGINE=InnoDB COMMENT='患者の基本情報を格納するマスターテーブル';


-- 3. リハビリテーション計画書テーブルの作成
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

    -- AI生成テキスト
    `ai_risks` TEXT NULL COMMENT '(AI生成) 安静度・リスク',
    `ai_contraindications` TEXT NULL COMMENT '(AI生成) 禁忌・特記事項',
    `ai_policy` TEXT NULL COMMENT '(AI生成) 治療方針',
    `ai_content` TEXT NULL COMMENT '(AI生成) 治療内容',
    
    -- 心身機能・構造 (チェックボックス)
    `has_consciousness_disorder` BOOLEAN DEFAULT FALSE COMMENT '意識障害',
    `has_respiratory_disorder` BOOLEAN DEFAULT FALSE COMMENT '呼吸機能障害',
    `has_swallowing_disorder` BOOLEAN DEFAULT FALSE COMMENT '嚥下機能障害',
    `has_joint_rom_limitation` BOOLEAN DEFAULT FALSE COMMENT '関節可動域制限',
    `has_muscle_weakness` BOOLEAN DEFAULT FALSE COMMENT '筋力低下',
    `has_paralysis` BOOLEAN DEFAULT FALSE COMMENT '麻痺',
    -- ... 他の全ての心身機能項目をBOOLEANで追加 ...

    -- FIMスコア (開始時)
    `fim_start_eating` INT NULL,
    `fim_start_grooming` INT NULL,
    `fim_start_total` INT NULL,
    -- ... 他の全てのFIM開始時項目を追加 ...

    -- FIMスコア (現在)
    `fim_current_eating` INT NULL,
    `fim_current_grooming` INT NULL,
    `fim_current_total` INT NULL,
    -- ... 他の全てのFIM現在項目を追加 ...

    -- 外部キー制約の設定
    INDEX `idx_patient_id` (`patient_id`),
    CONSTRAINT `fk_patient_id`
        FOREIGN KEY (`patient_id`)
        REFERENCES `patients` (`patient_id`)
        ON DELETE CASCADE -- 患者が削除されたら、関連する計画も全て削除する
) ENGINE=InnoDB COMMENT='作成されたリハビリテーション計画書の履歴';


-- =================================================================
-- 4. サンプルデータの挿入
-- =================================================================

-- 古いデータをクリア (テスト用に再実行する場合)
-- DELETE FROM patients;
-- DELETE FROM rehabilitation_plans;

-- 患者1: 田中 太郎さん
INSERT INTO patients (`patient_id`, `name`, `date_of_birth`, `gender`)
VALUES (1, '田中 太郎', '1955-04-10', '男')
ON DUPLICATE KEY UPDATE `name`=`name`; -- IDが既に存在すれば何もしない

-- 田中さんの古い計画書 (1ヶ月前)
INSERT INTO rehabilitation_plans (`plan_id`, `patient_id`, `creation_date`, `main_disease`, `is_physical_therapy`, `has_paralysis`, `fim_current_total`)
VALUES (101, 1, '2025-06-15', '脳梗塞右片麻痺', TRUE, TRUE, 85)
ON DUPLICATE KEY UPDATE `main_disease`=`main_disease`;

-- 田中さんの現在の計画書 (最新)
INSERT INTO rehabilitation_plans (`plan_id`, `patient_id`, `creation_date`, `main_disease`, `is_physical_therapy`, `is_occupational_therapy`, `has_paralysis`, `has_muscle_weakness`, `fim_current_total`)
VALUES (102, 1, '2025-07-15', '脳梗塞右片麻痺', TRUE, TRUE, TRUE, TRUE, 92)
ON DUPLICATE KEY UPDATE `main_disease`=`main_disease`;


-- 患者2: 鈴木 花子さん
INSERT INTO patients (`patient_id`, `name`, `date_of_birth`, `gender`)
VALUES (2, '鈴木 花子', '1960-08-20', '女')
ON DUPLICATE KEY UPDATE `name`=`name`;

-- 鈴木さんの計画書
INSERT INTO rehabilitation_plans (`plan_id`, `patient_id`, `creation_date`, `main_disease`, `is_physical_therapy`, `has_joint_rom_limitation`, `fim_current_total`)
VALUES (201, 2, '2025-07-10', '大腿骨頸部骨折（術後）', TRUE, TRUE, 78)
ON DUPLICATE KEY UPDATE `main_disease`=`main_disease`;


-- 完了メッセージ
SELECT 'データベースとテーブルの作成、サンプルデータの挿入が完了しました。' AS 'Status';