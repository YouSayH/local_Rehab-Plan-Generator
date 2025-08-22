import os
from datetime import date
from functools import wraps
from flask import (
    Flask,
    request,
    render_template,
    flash,
    redirect,
    url_for,
    send_from_directory,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from werkzeug.security import generate_password_hash, check_password_hash
from pymysql.err import IntegrityError

# 自作のPythonファイルをインポート
import database
import gemini_client
import excel_writer

app = Flask(__name__)
# ユーザーのセッション情報（例: ログイン状態）を暗号化するための秘密鍵。
# これがないとflashメッセージなどが使えない。
# TODO 本番環境では、config.pyファイルを作成or環境変数から読み込むのが一般的。
app.config["SECRET_KEY"] = "your-very-secret-key-for-session"


login_manager = LoginManager()
login_manager.init_app(app)
# 未ログインのユーザーがログイン必須ページにアクセスした際、
# どのページにリダイレクト（転送）するかを指定します。'login'は下の@app.route('/login')を持つ関数名を指します。
login_manager.login_view = "login"


# 管理者判別デコレータ
# @admin_required を付けたページにアクセスがあると、
# 本来の処理（ページの表示など）を実行する前に、判別する
def admin_required(f):
    # @wraps(f)は、デコレータを作る際のお作法のようなもので、
    # 元の関数(f)の名前などを引き継ぎ、デバッグしやすくするために付けます。
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("この操作には管理者権限が必要です。", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


# ・ログインユーザー情報を表現するためのクラス
# UserMixinは、Flask-Loginが必要とする基本的なメソッド（is_authenticatedなど）を
# 自動的に追加してくれる便利なクラスです。
class Staff(UserMixin):
    # コンストラクタ。ログイン時にデータベースから取得した職員情報をここに格納します。
    def __init__(self, staff_id, username, role):
        self.id = staff_id
        self.username = username
        self.role = role


# ・ユーザー情報をセッションから読み込むための関数
# Flask-Loginは、ページを移動するたびにこの関数を呼び出し、
# セッションに保存されたユーザーIDからユーザー情報を復元します。
@login_manager.user_loader
def load_user(staff_id):
    staff_info = database.get_staff_by_id(int(staff_id))
    if staff_info:
        # データベースから取得した情報を使ってStaffクラスのインスタンスを返す
        return Staff(
            staff_id=staff_info["id"],
            username=staff_info["username"],
            role=staff_info["role"],
        )
    return None


# ルーティング↓
# TODO Blueprints(関連機能ごとに分割)の利用を視野に入れる
# ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー


# 管理者権限　必須
@app.route("/signup", methods=["GET", "POST"])
@login_required
@admin_required
def signup():
    """アカウント登録ページ (管理者専用)"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # 同じユーザー名が既に存在しないかチェック
        if database.get_staff_by_username(username):
            flash("このユーザー名は既に使用されています。", "danger")
        else:
            # パスワードを安全なハッシュ値に変換
            hashed_password = generate_password_hash(password)
            # データベースに新しい職員を登録
            database.create_staff(username, hashed_password)
            flash(f"職員「{username}」さんのアカウントを作成しました。", "success")
            # 処理が終わったら、再度同じ登録ページを表示（続けて登録できるように）
        return redirect(url_for("signup"))

    # ページを初めて表示する場合 (GETリクエスト)
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """ログインページ"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        staff_info = database.get_staff_by_username(username)

        # ユーザーが存在し、かつパスワードが正しいかチェック
        # check_password_hashが、入力されたパスワードとDBのハッシュ値を比較してくれます。
        if staff_info and check_password_hash(staff_info["password"], password):
            # ログイン成功。ユーザー情報をStaffクラスに格納
            staff = Staff(
                staff_id=staff_info["id"],
                username=staff_info["username"],
                role=staff_info["role"],
            )
            # Flask-Loginのlogin_user関数で、ユーザーをログイン状態にする
            login_user(staff)
            # ログイン後のトップページにリダイレクト
            return redirect(url_for("index"))
        else:
            flash("ユーザー名またはパスワードが正しくありません。", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """ログアウト処理"""
    logout_user()
    flash("ログアウトしました。", "info")
    return redirect(url_for("login"))


@app.route("/edit_patient_info", methods=["GET"])
@login_required
def edit_patient_info():
    """患者の事実情報（マスターデータ）を追加・編集するページを表示"""
    # プルダウン用に全患者のリストを取得
    all_patients = database.get_all_patients()

    # URLクエリからpatient_idを取得 (例: /edit_patient_info?patient_id=1)
    patient_id_str = request.args.get("patient_id")
    patient_data = {}
    current_patient_id = None

    if patient_id_str:
        try:
            patient_id = int(patient_id_str)
            # 選択された患者の最新の事実データを取得
            patient_data = database.get_patient_data_for_plan(patient_id)
            if not patient_data:
                flash(f"ID:{patient_id}の患者データが見つかりません。", "warning")
                patient_data = {}
            else:
                current_patient_id = patient_id
        except (ValueError, TypeError):
            flash("無効な患者IDです。", "danger")

    return render_template(
        "edit_patient_info.html", all_patients=all_patients, patient_data=patient_data, current_patient_id=current_patient_id
    )


@app.route("/")
@login_required
def index():
    """トップページ。担当患者のみ表示"""
    try:
        assigned_patients = database.get_assigned_patients(current_user.id)
        return render_template("index.html", patients=assigned_patients)
    except Exception as e:
        flash(f"データベース接続エラー: {e}", "danger")
        return render_template("index.html", patients=[])


@app.route("/generate_plan", methods=["POST"])
@login_required
def generate_plan():
    """AIによる計画案の生成と確認ページへの遷移"""
    try:
        # Webフォームから送られてきたpatient_idは文字列なので、整数(int)に変換
        patient_id = int(request.form.get("patient_id"))
    except (ValueError, TypeError):
        flash("有効な患者が選択されていません。", "warning")
        return redirect(url_for("index"))

    # ・権限チェック
    # この職員が本当にこの患者の担当かを確認。なりすましや不正な操作を防ぎます。
    assigned_patients = database.get_assigned_patients(current_user.id)
    # assigned_patientsは辞書のリストなので、IDのリストに変換してチェック
    if patient_id not in [p["id"] for p in assigned_patients]:
        flash("権限がありません。担当の患者を選択してください。", "danger")
        return redirect(url_for("index"))

    try:
        # DBから患者の基本情報と「最新の」計画書データを取得
        latest_plan_data = database.get_patient_data_for_plan(patient_id)
        if not latest_plan_data:
            flash("患者データが見つかりません。", "danger")
            return redirect(url_for("index"))
        
        # 実施日を今日の日変更変更
        latest_plan_data["header_evaluation_date"] = date.today()

        # 担当者の所見を最新データに追加してAIに渡す
        latest_plan_data["therapist_notes"] = request.form.get("therapist_notes", "")

        # AIに新しい計画案を生成させる
        ai_generated_plan = gemini_client.generate_rehab_plan(latest_plan_data)

        if "error" in ai_generated_plan:
            flash(f"AIによる計画案の生成に失敗しました: {ai_generated_plan['error']}", "danger")
            return redirect(url_for("index"))

        # AIの生成結果を元のデータにマージする
        # これにより、元のデータ（FIM点数など）とAIの提案（テキスト項目）が
        # 一つの辞書にまとまり、テンプレートで扱いやすくなる。
        combined_plan_data = latest_plan_data.copy()
        combined_plan_data.update(ai_generated_plan)

        # マージした完全なデータをテンプレートに渡す
        return render_template(
            "confirm.html",
            patient_data=latest_plan_data,  # ページ上部の患者情報表示用
            plan=combined_plan_data,  # フォームの初期値・hidden値用
        )
    except Exception as e:
        flash(f"計画案の生成中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("index"))


@app.route("/save_plan", methods=["POST"])
@login_required
def save_plan():
    """計画の保存とダウンロードページへのリダイレクト"""
    patient_id = int(request.form.get("patient_id"))

    # こちらでも、保存直前に再度権限チェックを行うことで、より安全性を高める。
    assigned_patients = database.get_assigned_patients(current_user.id)
    if patient_id not in [p["id"] for p in assigned_patients]:
        flash("権限がありません。", "danger")
        return redirect(url_for("index"))

    try:
        # フォームから送信された全データを辞書として取得
        form_data = request.form.to_dict()
        print("--- /save_plan にフォームから送信されたデータ ---")
        import pprint

        pprint.pprint(form_data)
        print("-------------------------------------------------")

        # データベースに新しい計画として保存
        database.save_new_plan(patient_id, current_user.id, form_data)

        # Excel出力用に、DBに保存された「最新」の計画データを再取得する
        # これにより、DB保存時の型変換などが正しく反映されたデータを使用できる
        latest_plan_data_for_excel = database.get_patient_data_for_plan(patient_id)

        # Excelファイルを作成
        output_filepath = excel_writer.create_plan_sheet(latest_plan_data_for_excel)

        output_filename = os.path.basename(output_filepath)
        flash("リハビリテーション実施計画書が正常に作成・保存されました。", "success")

        # ファイルダウンロードとページ移動を同時に行うための中間ページを表示
        return render_template(
            "download_and_redirect.html",
            download_url=url_for("download_file", filename=output_filename),
            redirect_url=url_for("index"),
        )
    except Exception as e:
        flash(f"計画書の保存中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("index"))


@app.route("/save_patient_info", methods=["POST"])
@login_required
def save_patient_info():
    """患者の事実情報をデータベースに保存（新規作成または更新）"""
    try:
        form_data = request.form.to_dict()

        # データベースに保存処理を実行
        saved_patient_id = database.save_patient_master_data(form_data)

        flash("患者情報を正常に保存しました。", "success")
        # 保存後、今編集していた患者が選択された状態で同ページにリダイレクト
        return redirect(url_for("edit_patient_info", patient_id=saved_patient_id))

    except Exception as e:
        flash(f"情報の保存中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("edit_patient_info"))


@app.route("/download/<path:filename>")
@login_required
def download_file(filename):
    """ファイルを安全にダウンロードさせる"""
    directory = os.path.abspath(excel_writer.OUTPUT_DIR)
    try:
        # send_from_directoryは、指定されたディレクトリの外にあるファイルへの
        # アクセスを防いでくれるため、安全なファイル送信に使われます。
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        flash("ダウンロード対象のファイルが見つかりません。", "danger")
        return redirect(url_for("index"))


# 管理者専用ルート↓
# ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー


# 管理者権限　必須
@app.route("/manage_assignments", methods=["GET"])
@login_required
@admin_required
def manage_assignments():
    """担当割り当てと職員を管理するダッシュボード"""
    try:
        all_staff = database.get_all_staff()
        all_patients = database.get_all_patients()

        # 職員ごとの担当患者リストを格納するための辞書(dictionary)を作成
        assignments = {}
        for staff in all_staff:
            # 職員のIDをキーとして、その職員が担当する患者のリストを値として格納
            assignments[staff["id"]] = database.get_assigned_patients(staff["id"])

        return render_template(
            "manage_assignments.html",
            all_staff=all_staff,
            all_patients=all_patients,
            assignments=assignments,
        )
    except Exception as e:
        flash(f"管理ページの読み込み中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("index"))


# 管理者権限　必須
@app.route("/assign", methods=["POST"])
@login_required
@admin_required
def assign():
    """患者を担当に割り当てる"""
    staff_id = request.form.get("staff_id")
    patient_id = request.form.get("patient_id")
    if staff_id and patient_id:
        try:
            database.assign_patient_to_staff(staff_id, patient_id)
            flash("患者を割り当てました。", "success")
        except IntegrityError:
            # データベースの主キー制約（同じ組み合わせは登録できない）に違反した場合のエラー
            flash("その担当者は既にその患者に割り当てられています。", "warning")
        except Exception as e:
            flash(f"割り当て中にエラーが発生しました: {e}", "danger")
    return redirect(url_for("manage_assignments"))


# 管理者権限　必須
@app.route("/unassign/<int:staff_id>/<int:patient_id>")
@login_required
@admin_required
def unassign(staff_id, patient_id):
    """患者の担当を解除する"""
    try:
        database.unassign_patient_from_staff(staff_id, patient_id)
        flash("担当を解除しました。", "success")
    except Exception as e:
        flash(f"解除中にエラーが発生しました: {e}", "danger")
    return redirect(url_for("manage_assignments"))


# 管理者権限　必須
@app.route("/delete_staff/<int:staff_id>")
@login_required
@admin_required
def delete_staff(staff_id):
    """職員を削除する"""
    if staff_id == current_user.id:
        flash("自分自身のアカウントは削除できません。", "warning")
        return redirect(url_for("manage_assignments"))
    try:
        database.delete_staff_by_id(staff_id)
        flash("職員アカウントを削除しました。", "success")
    except Exception as e:
        flash(f"削除中にエラーが発生しました: {e}", "danger")
    return redirect(url_for("manage_assignments"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
