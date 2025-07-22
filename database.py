import os
import mysql.connector
from mysql.connector import Error
from datetime import date
from dotenv import load_dotenv

# --- データベース接続設定 ---

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からデータベース接続情報を取得
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# 必須の環境変数が設定されているか確認
if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("データベース接続情報が.envファイルに正しく設定されていません。DB_HOST, DB_USER, DB_PASSWORD, DB_NAME を確認してください。")

# 取得した情報から接続設定辞書を作成
DB_CONFIG = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME
}


def get_db_connection():
    """データベースへの接続を確立し、コネクションオブジェクトを返す"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"データベース接続エラー: {e}")
        # アプリケーション全体でエラーを処理できるよう、例外を再送出する
        raise e

def get_patient_list():
    """
    WebUIの選択肢に表示するための、全患者のIDと氏名のリストを取得する。
    """
    patient_list = []
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT patient_id AS id, name FROM patients ORDER BY patient_id;"
        cursor.execute(query)
        patient_list = cursor.fetchall()
    except Error as e:
        print(f"患者リストの取得中にエラーが発生しました: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return patient_list

def get_patient_data_for_plan(patient_id):
    """
    指定された一人の患者に関する、計画書作成に必要な全ての情報を取得する。
    """
    patient_data = None
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 患者の基本情報を取得
        query_patient = "SELECT * FROM patients WHERE patient_id = %s;"
        cursor.execute(query_patient, (patient_id,))
        base_info = cursor.fetchone()

        if not base_info:
            return None

        # その患者の最新の計画書情報を取得
        query_latest_plan = """
            SELECT * FROM rehabilitation_plans 
            WHERE patient_id = %s 
            ORDER BY creation_date DESC 
            LIMIT 1;
        """
        cursor.execute(query_latest_plan, (patient_id,))
        latest_plan_info = cursor.fetchone()

        # 基本情報と最新計画情報をマージ
        patient_data = base_info
        if latest_plan_info:
            patient_data.update(latest_plan_info)
        
        # 年齢を計算
        if 'date_of_birth' in patient_data and patient_data['date_of_birth']:
            today = date.today()
            born = patient_data['date_of_birth']
            patient_data['age'] = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        else:
            patient_data['age'] = '不明'

    except Error as e:
        print(f"患者データ(ID: {patient_id})の取得中にエラーが発生しました: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            
    return patient_data

def save_new_plan(patient_id, patient_data, ai_plan):
    """
    AIによって生成された新しい計画書の内容をデータベースに保存する。
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        columns = [
            'patient_id', 'creation_date', 'main_disease', 'therapist_notes',
            'ai_risks', 'ai_contraindications', 'ai_policy', 'ai_content'
            # 他のFIMスコアやチェックボックス項目もここに追加
        ]
        
        values = [
            patient_id, date.today(),
            patient_data.get('main_disease'), patient_data.get('therapist_notes'),
            ai_plan.get('risks'), ai_plan.get('contraindications'),
            ai_plan.get('policy'), ai_plan.get('content')
            # 対応する値もここに追加
        ]
        
        query = f"INSERT INTO rehabilitation_plans ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))});"
        
        cursor.execute(query, tuple(values))
        conn.commit()
        print(f"患者ID: {patient_id} の新しい計画書 (ID: {cursor.lastrowid}) を保存しました。")
        return True
        
    except Error as e:
        print(f"計画書の保存中にエラーが発生しました: {e}")
        conn.rollback()
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# --- テスト用のコード ---
if __name__ == '__main__':
    print("--- データベースモジュール (.env対応版) のテスト実行 ---")
    
    print("\n1. データベース接続テスト:")
    try:
        conn_test = get_db_connection()
        if conn_test.is_connected():
            print(f" -> 接続に成功しました。(Host: {DB_CONFIG['host']}, DB: {DB_CONFIG['database']})")
            conn_test.close()
    except Exception as e:
        print(f" -> 接続テスト中にエラー: {e}")

    print("\n2. 患者リスト取得テスト:")
    test_patients = get_patient_list()
    if test_patients:
        print(f" -> {len(test_patients)}名の患者を取得しました。")
    else:
        print(" -> 患者リストを取得できませんでした。")