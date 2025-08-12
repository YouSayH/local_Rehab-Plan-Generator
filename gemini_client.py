import os
import json
# import google.generativeai as genai ←2025,9月までしかサポートなし
# https://ai.google.dev/gemini-api/docs/libraries?hl=ja  新ライブラリ
# https://ai.google.dev/gemini-api/docs/quickstart?hl=ja 使い方
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv



# 初期設定
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("APIキーが.envファイルに設定されていません。'GOOGLE_API_KEY=...' を追加してください。")

# genai.configure(api_key=API_KEY)
# ↓↓新しい書き方
client = genai.Client()# APIキーは環境変数 `GOOGLE_API_KEY` または `GEMINI_API_KEY` から自動で読み込まれる


# Pydanticを使用して、AIに生成してほしいJSONの構造を定義します。
class RehabPlanSchema(BaseModel):
    comorbidities: str
    risks: str
    contraindications: str
    policy: str
    content: str


# プロトタイプ開発用の設定
# Trueにすると、実際にAPIを呼び出さずにダミーデータを返します。
USE_DUMMY_DATA = False

def generate_rehab_plan(patient_data):
    """
    患者データを基にプロンプトを生成し、Gemini APIにリハビリ計画の作成を依頼する。
    """
    if USE_DUMMY_DATA:
        print("--- ダミーデータを使用しています ---")
        return get_dummy_plan()

    try:
        # 患者の特記事項（心身機能）を格納するための空のリストを用意
        features = []
        boolean_flags = {
            'has_consciousness_disorder': '意識障害', 'has_respiratory_disorder': '呼吸機能障害',
            'has_swallowing_disorder': '嚥下機能障害', 'has_joint_rom_limitation': '関節可動域制限',
            'has_muscle_weakness': '筋力低下', 'has_paralysis': '麻痺'
            # TODO schema.sqlで定義した他の全てのhas_...項目をここに追加 
            # または、データベースから動的に追加できるようにしたい。
        }

        # boolean_flagsの各項目をループでチェック
        for key, description in boolean_flags.items():
            # もし患者データの中にその項目があり、かつ値がTrueなら、featuresリストに追加
            if patient_data.get(key):
                features.append(description)
        
        # FIMスコアもAIに伝えるための情報として整形
        fim_info = f"FIM合計点(現在): {patient_data.get('fim_current_total', '不明')}点"

        prompt = f"""
あなたは、リハビリテーション科の指導医です。
提供された患者データを分析し、専門的かつ具体的なリハビリテーション実施計画書の重要項目を日本語で作成してください。

# 患者データ
{{
  "年代": "{patient_data.get('age', '不明')}歳代",
  "性別": "{patient_data.get('gender', '不明')}",
  "算定病名": "{patient_data.get('main_disease', '情報なし')}",
  "特記事項": {{
    "心身機能": {json.dumps(features, ensure_ascii=False) if features else "特記なし"},
    "ADL状況": "{fim_info}"
  }},
  "担当者からの所見": "{patient_data.get('therapist_notes', '特になし')}"
}}

# 作成指示
上記データを基に、以下の各項目について、日本の医療現場で通用する具体的で簡潔な計画を立案してください。
- 併存疾患・合併症 (comorbidities)
- 安静度・リスク (risks)
- 禁忌・特記事項 (contraindications)
- 治療方針 (policy)
- 治療内容 (箇条書き形式。改行は\\nを使用) (content)
"""
        print("--- 生成されたプロンプト ---")
        print(prompt)
        print("--------------------------")

# https://ai.google.dev/gemini-api/docs/structured-output?hl=ja  JSONのように構造化した出力を設定する方法

        # configでJSON形式とそのスキーマを指定することで、安定してJSONを出力させます。
        generation_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RehabPlanSchema,
        ) 
        # Gemini APIの呼び出し
        response = client.models.generate_content(
            model='gemini-2.5-flash', # 最新の推奨モデルを使用
            contents=prompt,
            config=generation_config
        )

        # 応答のパース処理を改善。パースした結果(.parsed)を使用します。
        if response.parsed:
            # Pydanticモデルを辞書に変換して返す
            ai_plan = response.parsed.model_dump()
            return ai_plan
        else:
            # SDKがJSONとしてパースできなかった場合のエラー処理
            print("JSONパースエラー: レスポンスをスキーマに沿ってパースできませんでした。")
            print(f"--- AIからの不正な応答 ---\n{response.text}\n--------------------")
            return {"error": "AIからの応答をJSONとして解析できませんでした。"}

    except Exception as e:
        print(f"Gemini API呼び出し中に予期せぬエラーが発生しました: {e}")
        return {"error": f"AIとの通信中にエラーが発生しました: {e}"}

def get_dummy_plan():
    """開発用のダミーの計画書データを返す（comorbiditiesを追加）"""
    dummy_response = {
      "comorbidities": "高血圧症、2型糖尿病",
      "risks": "高血圧症があり、訓練中の血圧変動に注意が必要。転倒リスクが高いため、移動・移乗時は必ず見守りを行う。",
      "contraindications": "右肩関節の可動域制限に対し、無理な他動運動は避けること。疼痛を誘発しない範囲で実施する。",
      "policy": "ADL（日常生活動作）の自立度向上を主目標とし、特にトイレ動作と屋内安全歩行の確立を目指す。本人の意欲を尊重し、成功体験を積めるような課題設定を行う。",
      "content": "1. 更衣動作訓練：ベッドサイドでの座位にて、麻痺側・非麻痺側双方からの着脱練習\\n2. トイレ動作訓練：手すりを使用したシミュレーションと実地訓練\\n3. 歩行訓練：T字杖を使用し、病棟内の直線歩行および方向転換練習"
    }
    return dummy_response

# このファイルが直接実行された場合のテストコード
if __name__ == '__main__':
    print("--- Geminiクライアントモジュールのテスト実行 ---")
    
    sample_patient_data = {
        "name": "テスト患者", "age": 75, "gender": "男性",
        "main_disease": "脳梗塞右片麻痺", "fim_current_total": 88,
        "has_paralysis": True, "has_muscle_weakness": True,
        "therapist_notes": "本人の退院意欲は高いが、自宅の段差に対して不安を感じている。"
    }
    
    USE_DUMMY_DATA = False
    
    generated_plan = generate_rehab_plan(sample_patient_data)
    
    print("\\n--- 生成された計画 (結果) ---")
    import pprint
    # pprintを使うと、辞書を人間が読みやすい形に整形して表示してくれます。
    pprint.pprint(generated_plan)
    print("--------------------------")

    if 'error' in generated_plan:
        print("\\nテスト実行中にエラーが検出されました。")
    else:
        print("\\nテストが正常に完了しました。")