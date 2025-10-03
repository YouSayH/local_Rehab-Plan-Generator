# from collections import defaultdict
# from sqlalchemy import func

# # database.pyから必要なコンポーネントをインポート
# from database import SessionLocal, SuggestionLike

# # データベースのカラム名と日本語表示名の対応辞書
# ITEM_KEY_TO_JAPANESE = {
#     'main_risks_txt': '安静度・リスク',
#     'main_contraindications_txt': '禁忌・特記事項',
#     'adl_equipment_and_assistance_details_txt': '使用用具及び介助内容等',
#     'goals_1_month_txt': '目標（1ヶ月）',
#     'goals_at_discharge_txt': '目標（終了時）',
#     'policy_treatment_txt': '治療方針',
#     'policy_content_txt': '治療内容',
#     'func_pain_txt': '疼痛',
#     'func_rom_limitation_txt': '関節可動域制限',
#     'func_muscle_weakness_txt': '筋力低下',
#     'func_swallowing_disorder_txt': '摂食嚥下障害',
#     'func_behavioral_psychiatric_disorder_txt': '精神行動障害',
#     'func_nutritional_disorder_txt': '栄養障害',
#     'func_excretory_disorder_txt': '排泄機能障害',
#     'func_pressure_ulcer_txt': '褥瘡',
#     'func_contracture_deformity_txt': '拘縮・変形',
#     'func_motor_muscle_tone_abnormality_txt': '筋緊張異常',
#     'func_disorientation_txt': '見当識障害',
#     'func_memory_disorder_txt': '記憶障害',
#     'goal_p_action_plan_txt': '参加の具体的な対応方針',
#     'goal_a_action_plan_txt': '活動の具体的な対応方針',
#     'goal_s_psychological_action_plan_txt': '心理の具体的な対応方針',
#     'goal_s_env_action_plan_txt': '環境の具体的な対応方針',
#     'goal_s_3rd_party_action_plan_txt': '第三者の不利に関する具体的な対応方針'
# }


# def show_like_summary():
#     """
#     「いいね」の集計結果をターミナルに表示する。
#     """
#     db = SessionLocal()
#     try:
#         # item_key と liked_model でグループ化し、それぞれのカウントを集計
#         results = db.query(
#             SuggestionLike.item_key,
#             SuggestionLike.liked_model,
#             func.count(SuggestionLike.liked_model).label('like_count')
#         ).filter(
#             SuggestionLike.liked_model.isnot(None)  # いいねが解除された(null)データは除外
#         ).group_by(
#             SuggestionLike.item_key,
#             SuggestionLike.liked_model
#         ).all()

#         if not results:
#             print("いいねデータはまだありません。")
#             return

#         # item_key ごとに結果をまとめる
#         summary = defaultdict(lambda: defaultdict(int))
#         for item_key, liked_model, like_count in results:
#             summary[item_key][liked_model] = like_count

#         print("\n--- AI提案 いいね評価 集計結果 ---")
#         print("=" * 50)

#         # item_keyでソートして表示
#         for item_key, counts in sorted(summary.items()):
#             general_likes = counts.get('general', 0)
#             specialized_likes = counts.get('specialized', 0)
#             total_likes = general_likes + specialized_likes

#             # 日本語名を取得。もし辞書になければ元のキーをそのまま使う
#             japanese_name = ITEM_KEY_TO_JAPANESE.get(item_key, item_key)

#             general_rate = (general_likes / total_likes * 100) if total_likes > 0 else 0
#             specialized_rate = (specialized_likes / total_likes * 100) if total_likes > 0 else 0

#             print(f"\n■ {japanese_name}:")
#             print(f"  - 通常モデル:     {general_likes:3d} 件 ({general_rate:5.1f} %)")
#             print(f"  - 特化モデル(RAG): {specialized_likes:3d} 件 ({specialized_rate:5.1f} %)")
#             print(f"  ---------------------------------")
#             print(f"  合計:           {total_likes:3d} 件")

#         print("\n" + "=" * 50)
#     finally:
#         db.close()


# if __name__ == "__main__":
#     show_like_summary()