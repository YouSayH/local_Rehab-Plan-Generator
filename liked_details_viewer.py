from flask import Flask, render_template, jsonify, request
import database
import json
from collections import defaultdict

# app.pyから項目名のマッピングをインポート
from app import ITEM_KEY_TO_JAPANESE

app = Flask(__name__)


@app.route("/")
def index():
    """
    いいね詳細閲覧システムのトップページ。
    【修正】いいねの有無にかかわらず、すべての職員リストを表示する。
    """
    # いいねをしたことがある職員ではなく、全ての職員を取得するように変更
    # staff_list = database.get_staff_with_liked_items()
    staff_list = database.get_all_staff()
    return render_template("liked_details_viewer.html", staff_list=staff_list)


# --- 以下、JavaScriptからの動的なデータ取得リクエストに応答するAPI ---


@app.route("/api/get_patients_for_staff/<int:staff_id>")
def get_patients_for_staff(staff_id):
    """
    指定された職員がいいねをしたことがある患者のリストを返すAPI。
    """
    patients = database.get_patients_for_staff_with_liked_items(staff_id)
    return jsonify(patients)


@app.route("/api/get_plans_for_patient/<int:patient_id>")
def get_plans_for_patient(patient_id):
    """
    指定された患者の、いいねが含まれる計画書のリストを返すAPI。
    """
    # 【修正】新しいいいねテーブルを参照する関数を呼び出す
    plans = database.get_plans_with_liked_details_for_patient(patient_id)
    # 日付をフォーマットして返す
    formatted_plans = [
        {
            "plan_id": p["plan_id"],
            "created_at": p["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            if p["created_at"]
            else "N/A",
        }
        for p in plans
    ]
    return jsonify(formatted_plans)


@app.route("/regeneration_summary")
def regeneration_summary_page():
    """再生成回数の集計結果をグラフで表示するページ"""
    return render_template("regeneration_summary.html")


@app.route("/api/regeneration_summary")
def get_regeneration_summary():
    """【修正】再生成回数の集計結果をリスト形式のJSONで返すAPI"""
    try:
        # データベースから全ての再生成履歴を取得
        history = database.get_all_regeneration_history()

        # 項目ごと、モデルごとに回数を集計
        summary = defaultdict(lambda: {"general": 0, "specialized": 0})
        for record in history:
            item_key = record["item_key"]
            model_type = record["model_type"]
            if item_key in ITEM_KEY_TO_JAPANESE:
                if model_type in summary[item_key]:
                    summary[item_key][model_type] += 1

        # 【修正】confirm.htmlの表示順にソートするためのリストを作成
        summary_list = []
        # ITEM_KEY_TO_JAPANESE のキーの順序を基準にループする
        for item_key, japanese_name in ITEM_KEY_TO_JAPANESE.items():
            # 集計データが存在する項目のみをリストに追加
            if item_key in summary:
                counts = summary[item_key]
                total_count = counts.get("general", 0) + counts.get("specialized", 0)
                summary_list.append(
                    {
                        "item_key": item_key,
                        "japanese_name": japanese_name,
                        "general_count": counts.get("general", 0),
                        "specialized_count": counts.get("specialized", 0),
                        "total_count": total_count,
                    }
                )

        return jsonify(summary_list)
    except Exception as e:
        app.logger.error(f"Error getting regeneration summary: {e}")
        return jsonify({"error": "集計データの取得中にエラーが発生しました。"}), 500


@app.route("/view_liked_detail/<int:plan_id>")
def view_liked_detail(plan_id):
    """
    【ステップ3で実装】
    選択された計画書と、それに関連するいいね詳細情報を表示するページ。
    """
    # ステップ1で保存した計画書データを取得
    plan_data = database.get_plan_by_id(plan_id)
    if not plan_data:
        return "指定された計画書が見つかりません。", 404

    # ステップ1で保存した「いいね」の詳細情報を取得
    liked_details = database.get_liked_item_details_by_plan_id(plan_id)

    # テンプレートで扱いやすいように、item_keyをキーにした辞書に変換（各キーに1つの詳細情報）
    details_map = {detail["item_key"]: detail for detail in liked_details}
    # 最初のいいね情報から所感と患者情報を取得（これらは計画書単位で共通のはず）
    therapist_notes = (
        liked_details[0]["therapist_notes_at_creation"] if liked_details else ""
    )
    patient_info_snapshot = {}
    if liked_details and liked_details[0].get("patient_info_snapshot_json"):
        try:
            patient_info_snapshot = json.loads(
                liked_details[0]["patient_info_snapshot_json"]
            )
        except (json.JSONDecodeError, TypeError):
            patient_info_snapshot = {}  # パース失敗時は空の辞書

    # view_plan.html を流用した新しいテンプレートをレンダリング
    return render_template(
        "liked_item_detail_view.html",
        plan=plan_data,
        details_map=details_map,
        therapist_notes=therapist_notes,
        patient_info_snapshot=patient_info_snapshot,
    )


# このファイルが直接実行されたときのみ、以下のコードが実行される
if __name__ == "__main__":
    # この閲覧システムはデバッグモードで、app.pyとは別のポート(例: 5001)で実行する
    # use_reloader=False は、メインアプリと同様にデバッグ時の二重実行を防ぐために設定します。
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
