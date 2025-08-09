import os
import pymysql
import pymysql.cursors
from pymysql.err import Error
from datetime import date
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("データベース接続情報が.envファイルに正しく設定されていません。")

DB_CONFIG = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_db_connection():
    """データベースへの接続を確立し、コネクションオブジェクトを返すヘルパー関数。"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Error as e:
        # データベースサーバーが起動していない場合などにエラーが発生します。
        print(f"データベース接続エラー: {e}")
        raise


def get_patient_data_for_plan(patient_id):
    """一人の患者に関する、計画書作成に必要な情報を取得する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1. まず、patientsテーブルから患者の基本情報を取得
            query_patient = "SELECT * FROM patients WHERE patient_id = %s;"
            cursor.execute(query_patient, (patient_id,))
            base_info = cursor.fetchone()
            if not base_info:
                return None # 該当する患者が存在しない場合はNoneを返す

            # 2. 次に、rehabilitation_plansテーブルからその患者の最新の計画書を取得
            # ORDER BY creation_date DESCで作成日順に並べ替え、LIMIT 1で最新の1件のみ取得します。
            query_latest_plan = """
                SELECT * FROM rehabilitation_plans 
                WHERE patient_id = %s ORDER BY creation_date DESC LIMIT 1;
            """
            cursor.execute(query_latest_plan, (patient_id,))
            latest_plan_info = cursor.fetchone()

            # 3. 患者の基本情報と最新の計画書情報を一つの辞書にまとめる
            patient_data = base_info
            if latest_plan_info:
                # updateメソッドで、キーが重複するものは上書きし、存在しないキーは追加します。
                patient_data.update(latest_plan_info)

            # 生年月日から年齢を計算
            if "date_of_birth" in patient_data and patient_data["date_of_birth"]:
                today = date.today()
                born = patient_data["date_of_birth"]
                # 誕生日が来ていなければ1歳引く、という計算式
                patient_data["age"] = (
                    today.year
                    - born.year
                    - ((today.month, today.day) < (born.month, born.day))
                )
            else:
                patient_data["age"] = "不明"
        return patient_data
    finally:
        # tryブロックで何が起きても、最終的に必ずデータベース接続を閉じる
        conn.close()


def save_new_plan(patient_id, patient_data, final_plan):
    """新しい計画書の内容をデータベースに保存する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 保存するカラムのリスト
            columns = [
                "patient_id",
                "creation_date",
                "main_disease",
                "evaluation_date",
                "onset_date",
                "rehab_start_date",
                "is_physical_therapy",
                "is_occupational_therapy",
                "is_speech_therapy",
                "therapist_notes",
                "ai_risks",
                "ai_contraindications",
                "ai_policy",
                "ai_content",
                "has_consciousness_disorder",
                "has_respiratory_disorder",
                "has_swallowing_disorder",
                "has_joint_rom_limitation",
                "has_muscle_weakness",
                "has_paralysis",
                "fim_start_total",
                "fim_current_total",
            ]

            # 上記カラムに対応する値のリスト
            values = [
                patient_id,
                date.today(),
                patient_data.get("main_disease"),
                patient_data.get("evaluation_date"),
                patient_data.get("onset_date"),
                patient_data.get("rehab_start_date"),
                patient_data.get("is_physical_therapy", False),
                patient_data.get("is_occupational_therapy", False),
                patient_data.get("is_speech_therapy", False),
                patient_data.get("therapist_notes"),
                final_plan.get("risks"),
                final_plan.get("contraindications"),
                final_plan.get("policy"),
                final_plan.get("content"),
                patient_data.get("has_consciousness_disorder", False),
                patient_data.get("has_respiratory_disorder", False),
                patient_data.get("has_swallowing_disorder", False),
                patient_data.get("has_joint_rom_limitation", False),
                patient_data.get("has_muscle_weakness", False),
                patient_data.get("has_paralysis", False),
                patient_data.get("fim_start_total"),
                patient_data.get("fim_current_total"),
            ]

            # f文を使って動的にSQLクエリを組み立て TODO SQLAlchemyに書き換えを検討(MySQLで使えるかわかりませんが)→SQLインジェクション対策(一応現在のコードも対策しているが...)
            query = f"INSERT INTO rehabilitation_plans ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))});"
            # cursor.executeの第二引数に値のタプルを渡すことで、SQLインジェクション対策をしている。
            cursor.execute(query, tuple(values))
        # commit()を実行して、初めてデータベースへの変更を確定させる。
        conn.commit()
    finally:
        conn.close()


def get_staff_by_username(username):
    """ユーザー名から職員情報を取得する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM staff WHERE username = %s;"
            cursor.execute(query, (username,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_staff_by_id(staff_id):
    """IDから職員情報を取得する (Flask-Loginのuser_loader用)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM staff WHERE id = %s;"
            cursor.execute(query, (staff_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def create_staff(username, hashed_password, role="general"):
    """新しい職員を登録する (デフォルトは一般権限)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # roleにはデフォルト値'general'が設定されているため、
            # 呼び出し側で指定がなければ一般ユーザーとして登録されます。
            query = "INSERT INTO staff (username, password, role) VALUES (%s, %s, %s);"
            cursor.execute(query, (username, hashed_password, role))
        conn.commit()
    finally:
        conn.close()


def get_assigned_patients(staff_id):
    """職員IDから担当患者のリストを取得する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # INNER JOINを使って、2つのテーブルを結合します。
            # staff_patientsテーブルのpatient_idと、patientsテーブルのpatient_idが
            # 一致する行を結びつけ、患者名(p.name)などの詳細情報を取得します。
            query = """
                SELECT p.patient_id AS id, p.name 
                FROM patients p
                INNER JOIN staff_patients sp ON p.patient_id = sp.patient_id
                WHERE sp.staff_id = %s
                ORDER BY p.patient_id;
            """
            cursor.execute(query, (staff_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def get_all_staff():
    """全職員のリストを取得する（管理者画面用）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # パスワードは入れていない↓
            cursor.execute("SELECT id, username, role FROM staff ORDER BY id;")
            return cursor.fetchall()
    finally:
        conn.close()


def get_all_patients():
    """全患者のリストを取得する（管理者画面用）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT patient_id, name FROM patients ORDER BY patient_id;")
            return cursor.fetchall()
    finally:
        conn.close()


def assign_patient_to_staff(staff_id, patient_id):
    """職員に患者を割り当てる"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = "INSERT INTO staff_patients (staff_id, patient_id) VALUES (%s, %s);"
            cursor.execute(query, (staff_id, patient_id))
        conn.commit()
    finally:
        conn.close()


def unassign_patient_from_staff(staff_id, patient_id):
    """職員の担当から患者を解除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = (
                "DELETE FROM staff_patients WHERE staff_id = %s AND patient_id = %s;"
            )
            cursor.execute(query, (staff_id, patient_id))
        conn.commit()
    finally:
        conn.close()


def delete_staff_by_id(staff_id):
    """職員をIDで削除する"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = "DELETE FROM staff WHERE id = %s;"
            cursor.execute(query, (staff_id,))
        conn.commit()
    finally:
        conn.close()
