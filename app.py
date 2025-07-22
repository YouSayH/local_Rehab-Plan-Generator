import os
from flask import Flask, request, send_file, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename

# 他の自作モジュールをインポート
import database
import gemini_client
import excel_writer

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# Flashメッセージ（ユーザーへの通知機能）を使用するために秘密鍵を設定
# 本番環境では、より複雑なキーを環境変数などから読み込むことを推奨します
app.config['SECRET_KEY'] = 'your-very-secret-key'

# --- ルーティングとビュー関数 ---

@app.route('/', methods=['GET'])
def index():
    """
    トップページを表示します。
    データベースから患者リストを取得し、Webページのドロップダウンリストに表示します。
    """
    try:
        # データベースから患者のリストを取得
        patients = database.get_patient_list()
        # index.htmlをレンダリングして返す
        return render_template('index.html', patients=patients)
    except Exception as e:
        # データベース接続エラーなど、予期せぬエラーが発生した場合
        flash(f"エラーが発生しました: {e}", "danger")
        # エラーが発生しても最低限のページを表示
        return render_template('index.html', patients=[])

@app.route('/generate_plan', methods=['POST'])
def generate_plan():
    """
    WebフォームからのPOSTリクエストを受け取り、計画書を生成するメインの処理です。
    """
    # 1. Webフォームから送信されたデータを取得
    patient_id = request.form.get('patient_id')
    therapist_notes = request.form.get('therapist_notes', '') # 任意入力なので、なければ空文字

    # 患者IDが選択されているかチェック
    if not patient_id:
        flash("患者が選択されていません。", "warning")
        return redirect(url_for('index'))

    try:
        # 2. データベースから計画書作成に必要な患者データを取得
        print(f"データベースから患者ID: {patient_id} の情報を取得します。")
        patient_data = database.get_patient_data_for_plan(patient_id)
        if not patient_data:
            flash(f"指定された患者ID: {patient_id} のデータが見つかりませんでした。", "danger")
            return redirect(url_for('index'))
        
        # フォームから入力された担当者の所感をデータに追加
        patient_data['therapist_notes'] = therapist_notes

        # 3. Gemini APIにリクエストを送信し、AIによる計画案を取得
        print("Gemini APIにリクエストを送信し、計画案を生成します。")
        ai_generated_plan = gemini_client.generate_rehab_plan(patient_data)
        if not ai_generated_plan or 'policy' not in ai_generated_plan:
             flash("AIによる計画案の生成に失敗しました。AIの応答が不正です。", "danger")
             return redirect(url_for('index'))

        # 4. Excelテンプレートにデータベースの情報とAIの計画案を書き込む
        print("Excelファイルに書き込んでいます。")
        output_filepath = excel_writer.create_plan_sheet(patient_data, ai_generated_plan)
        
        # 5. 今回作成した計画書の内容をデータベースに保存
        print("生成した計画の内容をデータベースに保存します。")
        database.save_new_plan(patient_id, patient_data, ai_generated_plan)
        flash("リハビリテーション実施計画書が正常に作成されました。", "success")

        # 6. 生成したExcelファイルをユーザーにダウンロードさせる
        print(f"ファイル {os.path.basename(output_filepath)} をユーザーに送信します。")
        return send_file(
            output_filepath,
            as_attachment=True,
            download_name=os.path.basename(output_filepath) # ブラウザでのデフォルトファイル名
        )

    except Exception as e:
        # 処理中に何らかのエラーが発生した場合
        print(f"計画書作成中にエラーが発生しました: {e}")
        flash(f"計画書の作成中にエラーが発生しました: {e}", "danger")
        return redirect(url_for('index'))

# --- アプリケーションの実行 ---

if __name__ == '__main__':
    # Flaskの開発用サーバーを起動
    # debug=True にすると、コード変更時に自動でリロードされ、エラー詳細がブラウザに表示されます。
    # 本番環境では、GunicornやuWSGIなどのWSGIサーバーを使用してください。
    app.run(host='0.0.0.0', port=5000, debug=True)