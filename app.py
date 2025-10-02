import os
import json
from datetime import date
import threading
from functools import wraps
from flask import (
    Flask,
    request,
    render_template,
    flash,
    Response,
    redirect,
    url_for,
    send_from_directory,
    jsonify,
    session,
    make_response
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
from rag_executor import RAGExecutor
from patient_info_parser import PatientInfoParser # 新しく追加

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

# pipeline_nameをキー、RAGExecutorインスタンスを値とする辞書（キャッシュ）
rag_executors = {}
# 複数ユーザーからの同時アクセスで問題が起きないようにするためのロック機構
rag_executor_lock = threading.Lock()

def get_rag_executor(pipeline_name: str) -> RAGExecutor:
    """
    RAGExecutorのインスタンスをキャッシュから取得または新規作成する関数。
    """
    # キャッシュに存在すれば、それを返す（高速）
    if pipeline_name in rag_executors:
        print(f"'{pipeline_name}' のExecutorをキャッシュから再利用します。")
        return rag_executors[pipeline_name]

    # キャッシュになければ、ロックをかけて新規作成
    with rag_executor_lock:
        # ダブルチェックロッキング
        if pipeline_name in rag_executors:
            return rag_executors[pipeline_name]

        print(f"'{pipeline_name}' のExecutorを新規に初期化します...")
        try:
            executor = RAGExecutor(pipeline_name=pipeline_name)
            rag_executors[pipeline_name] = executor # キャッシュに保存
            print(f"'{pipeline_name}' の初期化が完了し、キャッシュに保存しました。")
            return executor
        except Exception as e:
            print(f"FATAL: RAG Executor ('{pipeline_name}') の初期化に失敗しました: {e}")
            raise e

# 患者情報解析パーサーを初期化
print("Initializing Patient Info Parser...")
try:
    patient_info_parser = PatientInfoParser()
    print("Patient Info Parser initialized successfully.")
except Exception as e:
    print(f"FATAL: Failed to initialize Patient Info Parser: {e}")

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
    def __init__(self, staff_id, username, role, occupation):
        self.id = staff_id
        self.username = username
        self.role = role
        self.occupation = occupation


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
            occupation=staff_info["occupation"],
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
        occupation = request.form.get("occupation")

        # 同じユーザー名が既に存在しないかチェック
        if database.get_staff_by_username(username):
            flash("このユーザー名は既に使用されています。", "danger")
        else:
            # パスワードを安全なハッシュ値に変換
            hashed_password = generate_password_hash(password)
            # データベースに新しい職員を登録
            database.create_staff(username, hashed_password, occupation)
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
                occupation=staff_info["occupation"],
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
    plan_history = [] # 履歴を格納する空のリストを初期化
    current_patient_id = None

    if patient_id_str:
        try:
            patient_id = int(patient_id_str)
            # 選択された患者の最新のデータを取得
            patient_data = database.get_patient_data_for_plan(patient_id)
            # 患者の計画書履歴を取得
            raw_plan_history = database.get_plan_history_for_patient(patient_id)
            # created_atがNoneでない履歴のみをフィルタリング
            plan_history = [plan for plan in raw_plan_history if plan.get('created_at') is not None]

            if not patient_data:
                flash(f"ID:{patient_id}の患者データが見つかりません。", "warning")
                patient_data = {}
            else:
                current_patient_id = patient_id
        except (ValueError, TypeError):
            flash("無効な患者IDです。", "danger")

    return render_template(
        "edit_patient_info.html", 
        all_patients=all_patients, 
        patient_data=patient_data, 
        plan_history=plan_history, # 履歴をテンプレートに渡す
        current_patient_id=current_patient_id
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
    """AI生成の準備をし、確認・修正ページを直接表示する"""
    try:
        patient_id = int(request.form.get("patient_id"))
        therapist_notes = request.form.get("therapist_notes", "")
        print(f"こっちはジェネレートプラン無印　DEBUG [app.py]: therapist_notes from URL = '{therapist_notes[:100]}...'")

        # 権限チェック
        assigned_patients = database.get_assigned_patients(current_user.id)
        if patient_id not in [p["id"] for p in assigned_patients]:
            flash("権限がありません。", "danger")
            return redirect(url_for("index"))

        # 患者の基本情報と「最新の」計画書データを取得
        patient_data = database.get_patient_data_for_plan(patient_id)
        if not patient_data:
            flash(f"ID:{patient_id}の患者データが見つかりません。", "warning")
            return redirect(url_for("index"))

        # AI生成前のplanオブジェクトを作成 (AI生成項目は空にしておく)
        general_plan = patient_data.copy()
        specialized_plan = {} # RAG実装までの仮対応

        editable_keys = [
            'main_risks_txt', 'main_contraindications_txt', 'func_pain_txt',
            'func_rom_limitation_txt', 'func_muscle_weakness_txt', 'func_swallowing_disorder_txt',
            'func_behavioral_psychiatric_disorder_txt', 'cs_motor_details', 'func_nutritional_disorder_txt',
            'func_excretory_disorder_txt', 'func_pressure_ulcer_txt', 'func_contracture_deformity_txt',
            'func_motor_muscle_tone_abnormality_txt', 'func_disorientation_txt', 'func_memory_disorder_txt',
            'adl_equipment_and_assistance_details_txt', 'goals_1_month_txt', 'goals_at_discharge_txt',
            'policy_treatment_txt', 'policy_content_txt', 'goal_p_action_plan_txt', 'goal_a_action_plan_txt',
            'goal_s_psychological_action_plan_txt', 'goal_s_env_action_plan_txt', 'goal_s_3rd_party_action_plan_txt'
        ]
        for key in editable_keys:
            # general_plan と specialized_plan の両方に空文字を設定
            general_plan[key] = ""
            specialized_plan[key] = "" # 仮テキストを削除

        return render_template(
            "confirm.html",
            patient_data=patient_data,
            general_plan=general_plan,
            specialized_plan=specialized_plan,
            therapist_notes=therapist_notes, # 独立して渡す
            is_generating=True  # JavaScriptで生成処理をキックするためのフラグ
        )

    except (ValueError, TypeError):
        flash("有効な患者が選択されていません。", "warning")
        return redirect(url_for("index"))
    except Exception as e:
        app.logger.error(f"Error during generate_plan: {e}")
        flash(f"ページの表示中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("index"))


@app.route("/api/generate/general")
@login_required
def generate_general_stream():
    """Gemini単体モデルによる計画案をストリーミングで生成するAPI"""
    try:
        # URLのクエリパラメータから患者IDと所見を取得
        patient_id = int(request.args.get("patient_id"))
        therapist_notes = request.args.get("therapist_notes", "")

        # 権限チェック：ログイン中のユーザーが担当する患者か確認
        assigned_patients = database.get_assigned_patients(current_user.id)
        if patient_id not in [p["id"] for p in assigned_patients]:
            return Response("権限がありません。", status=403)

        # データベースから患者データを取得
        patient_data = database.get_patient_data_for_plan(patient_id)
        if not patient_data:
            return Response("患者データが見つかりません。", status=404)
            
        # 担当者の所見を患者データに含める
        patient_data["therapist_notes"] = therapist_notes
        
        # gemini_clientに新設する、Gemini単体生成用のストリーミング関数を呼び出す
        stream_generator = gemini_client.generate_general_plan_stream(patient_data)
        
        # 結果をストリーミングでフロントエンドに返す
        return Response(stream_generator, mimetype="text/event-stream")

    except ValueError:
        error_message = "無効な患者IDが指定されました。"
        error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
        return Response(error_event, mimetype="text/event-stream")
    except Exception as e:
        app.logger.error(f"汎用モデルのストリーム処理中にエラーが発生しました: {e}")
        error_message = f"サーバーエラーが発生しました。詳細は管理者にお問い合わせください。"
        error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
        return Response(error_event, mimetype="text/event-stream")


@app.route("/api/generate/rag/<pipeline_name>")
@login_required
def generate_rag_stream(pipeline_name):
    """指定されたRAGパイプラインによる計画案をストリーミングで生成するAPI"""
    try:
        # URLのクエリパラメータから患者IDと所見を取得
        patient_id = int(request.args.get("patient_id"))
        therapist_notes = request.args.get("therapist_notes", "")

        # 権限チェック
        assigned_patients = database.get_assigned_patients(current_user.id)
        if patient_id not in [p["id"] for p in assigned_patients]:
            return Response("権限がありません。", status=403)

        # データベースから患者データを取得
        patient_data = database.get_patient_data_for_plan(patient_id)
        if not patient_data:
            return Response("患者データが見つかりません。", status=404)

        # 担当者の所見を患者データに含める
        patient_data["therapist_notes"] = therapist_notes
        
        # キャッシュ管理関数を使って、指定されたパイプラインのExecutorを取得
        rag_executor = get_rag_executor(pipeline_name)
        if not rag_executor:
            raise Exception(f"パイプライン '{pipeline_name}' の Executorを取得できませんでした。")
        
        # gemini_clientに新設する、RAG実行用のストリーミング関数を呼び出す
        stream_generator = gemini_client.generate_rag_plan_stream(patient_data, rag_executor)
        
        # 結果をストリーミングでフロントエンドに返す
        return Response(stream_generator, mimetype="text/event-stream")

    except ValueError:
        error_message = "無効な患者IDが指定されました。"
        error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
        return Response(error_event, mimetype="text/event-stream")
    except Exception as e:
        app.logger.error(f"RAGモデル({pipeline_name})のストリーム処理中にエラーが発生しました: {e}")
        error_message = f"サーバーエラーが発生しました。詳細は管理者にお問い合わせください。"
        error_event = f"event: error\ndata: {json.dumps({'error': error_message})}\n\n"
        return Response(error_event, mimetype="text/event-stream")


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

        # データベースに新しい計画として保存し、そのIDを取得
        new_plan_id = database.save_new_plan(patient_id, current_user.id, form_data)

        # Excel出力用に、DBに保存されたばかりの計画データをIDで再取得
        plan_data_for_excel = database.get_plan_by_id(new_plan_id)
        if not plan_data_for_excel:
            # このエラーは通常発生しないはず
            flash("保存した計画データの再取得に失敗しました。", "danger")
            return redirect(url_for("index"))

        # Excelファイルを作成
        output_filepath = excel_writer.create_plan_sheet(plan_data_for_excel)
        output_filename = os.path.basename(output_filepath)
        
        flash("リハビリテーション実施計画書が正常に作成・保存されました。", "success")

        # ファイルダウンロードとページ移動を同時に行うための中間ページを表示
        return render_template(
            "download_and_redirect.html",
            download_url=url_for("download_file", filename=output_filename),
            redirect_url=url_for("index"),
        )
    except Exception as e:
        flash(f"計画書の保存・Excel作成中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("index"))


@app.route("/save_patient_info", methods=["POST"])
@login_required
def save_patient_info():
    """患者の事実情報をデータベースに保存（新規作成または更新）"""
    try:
        form_data = request.form.to_dict()

        # nameとvalueのプレフィックスから、対応するチェックボックス名を生成する辞書
        RADIO_GROUP_MAP = {
            "func_basic_rolling_level": "func_basic_rolling_",
            "func_basic_sitting_balance_level": "func_basic_sitting_balance_",
            "func_basic_getting_up_level": "func_basic_getting_up_",
            "func_basic_standing_balance_level": "func_basic_standing_balance_",
            "func_basic_standing_up_level": "func_basic_standing_up_",
            "social_care_level_support_num_slct": "social_care_level_support_num",
            "social_care_level_care_num_slct": "social_care_level_care_num",
            "goal_p_schooling_status_slct": "goal_p_schooling_status_",
            "goal_a_bed_mobility_level": "goal_a_bed_mobility_",
            "goal_a_indoor_mobility_level": "goal_a_indoor_mobility_",
            "goal_a_outdoor_mobility_level": "goal_a_outdoor_mobility_",
            "goal_a_driving_level": "goal_a_driving_",
            "goal_a_transport_level": "goal_a_public_transport_",
            "goal_a_toileting_level": "goal_a_toileting_",
            "goal_a_eating_level": "goal_a_eating_",
            "goal_a_grooming_level": "goal_a_grooming_",
            "goal_a_dressing_level": "goal_a_dressing_",
            "goal_a_bathing_level": "goal_a_bathing_",
            "goal_a_housework_level": "goal_a_housework_meal_",
            "goal_a_writing_level": "goal_a_writing_",
            "goal_a_ict_level": "goal_a_ict_",
            "goal_a_communication_level": "goal_a_communication_",
            "goal_p_return_to_work_status_slct": "goal_p_return_to_work_status_",
            "func_circulatory_arrhythmia_status_slct": "func_circulatory_arrhythmia_status_",
        }

        # 変換後のデータを保持する新しい辞書
        processed_form_data = form_data.copy()

        for group_name, prefix in RADIO_GROUP_MAP.items():
            if group_name in form_data:
                value = form_data[group_name]
                
                # 例: social_care_level_support_num_slct の値が '1' の場合
                if group_name in ["social_care_level_support_num_slct", "social_care_level_care_num_slct"]:
                    # social_care_level_support_num1_slct = 'on' を生成
                    target_key = f"{prefix}{value}_slct"
                # 例: goal_a_writing_level の値が 'independent_after_hand_change' の場合
                elif value == "independent_after_hand_change":
                    # goal_a_writing_independent_after_hand_change_chk = 'on' を生成
                    target_key = f"{prefix}independent_after_hand_change_chk"
                # 例: func_basic_rolling_level の値が 'partial_assist' の場合
                elif value == "partial_assist":
                    # func_basic_rolling_partial_assistance_chk = 'on' を生成
                    target_key = f"{prefix}partial_assistance_chk"
                # 例: goal_a_toileting_level の値が 'assist' の場合
                elif value == "assist":
                     # goal_a_toileting_assistance_chk = 'on' を生成
                    target_key = f"{prefix}assistance_chk"
                # その他の一般的な値 (independent, not_performed など)
                else:
                    # func_basic_rolling_independent_chk = 'on' などを生成
                    target_key = f"{prefix}{value}_chk"
                
                processed_form_data[target_key] = 'on'
                # 元のキーは不要なので削除
                del processed_form_data[group_name]

        # データベースに保存処理を実行 (変換後のデータを使用)
        saved_patient_id = database.save_patient_master_data(processed_form_data)

        flash("患者情報を正常に保存しました。", "success")
        # 保存後、今編集していた患者が選択された状態で同ページにリダイレクト
        return redirect(url_for("edit_patient_info", patient_id=saved_patient_id))

    except Exception as e:
        flash(f"情報の保存中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("edit_patient_info"))


@app.route('/like_suggestion', methods=['POST'])
@login_required
def like_suggestion():
    """AI提案の「いいね」評価を保存するAPIエンドポイント"""
    data = request.get_json()
    patient_id = data.get('patient_id')
    item_key = data.get('item_key')
    liked_model = data.get('liked_model')  # 'general', 'specialized', または null

    if not all([patient_id, item_key]):
        return jsonify({'status': 'error', 'message': '必須フィールドが不足しています。'}), 400

    try:
        # この関数を database.py に作成する必要があります
        # どのユーザーが評価したかを記録するために current_user.id も渡します
        database.save_suggestion_like(
            patient_id=patient_id,
            item_key=item_key,
            liked_model=liked_model,
            staff_id=current_user.id
        )
        return jsonify({'status': 'success', 'message': f'項目「{item_key}」の評価を保存しました。'})
    except Exception as e:
        app.logger.error(f"Error saving suggestion like: {e}")
        return jsonify({'status': 'error', 'message': 'データベース処理中にエラーが発生しました。'}), 500


@app.route("/api/plan_history/<int:patient_id>")
@login_required
def get_plan_history(patient_id):
    """【新規】指定された患者の計画書履歴をJSONで返すAPI"""
    # 権限チェック: ログイン中のユーザーがその患者の担当か、あるいは管理者か
    assigned_patients = database.get_assigned_patients(current_user.id)
    is_admin = current_user.role == "admin"
    
    # 管理者でない、かつ担当患者リストにいない場合はエラー
    if not is_admin and patient_id not in [p["id"] for p in assigned_patients]:
        return jsonify({"error": "権限がありません。"}), 403

    try:
        history = database.get_plan_history_for_patient(patient_id)
        # 日付を読みやすいフォーマットに変換
        for item in history:
            item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/view_plan/<int:plan_id>")
@login_required
def view_plan(plan_id):
    """【新規】特定の計画書を閲覧するページ"""
    try:
        plan_data = database.get_plan_by_id(plan_id)
        if not plan_data:
            flash("指定された計画書が見つかりません。", "danger")
            return redirect(url_for("index"))

        # 権限チェック
        patient_id = plan_data["patient_id"]
        assigned_patients = database.get_assigned_patients(current_user.id)
        is_admin = current_user.role == "admin"
        if not is_admin and patient_id not in [p["id"] for p in assigned_patients]:
            flash("この計画書を閲覧する権限がありません。", "danger")
            return redirect(url_for("index"))

        return render_template("view_plan.html", plan=plan_data)
    except Exception as e:
        flash(f"計画書の読み込み中にエラーが発生しました: {e}", "danger")
        return redirect(url_for("index"))


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


@app.route("/api/parse-patient-info", methods=["POST"])
@login_required
def api_parse_patient_info():
    """【新規】カルテテキストを解析して構造化された患者情報を返すAPI"""
    if not patient_info_parser:
        return jsonify({"error": "サーバー側でパーサーが初期化されていません。"}), 500

    data = request.get_json()
    if not data or "text" not in data or not data["text"].strip():
        return jsonify({"error": "解析対象のテキストがありません。"}), 400

    try:
        text_to_parse = data["text"]
        parsed_data = patient_info_parser.parse_text(text_to_parse)
        return jsonify(parsed_data)
    except Exception as e:
        app.logger.error(f"Error during parsing patient info: {e}")
        return jsonify({"error": "解析中にサーバーでエラーが発生しました。", "details": str(e)}), 500


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
    # app.run(host="0.0.0.0", port=5000, debug=False) # 最初にRAGインスタンスを作る場合に邪魔

    # debug=True のままだとリローダーが有効になるため、use_reloader=False を明示的に指定します。
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)