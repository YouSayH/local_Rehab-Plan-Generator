import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# --- 初期設定 ---

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
API_KEY = os.getenv("GOOGLE_API_KEY")

# APIキーが設定されているか確認
if not API_KEY:
    raise ValueError("APIキーが.envファイルに設定されていません。'GOOGLE_API_KEY=...' を追加してください。")

# APIキーを使ってGeminiを初期化
genai.configure(api_key=API_KEY)

# --- プロトタイプ開発用の設定 ---
# Trueにすると、実際にAPIを呼び出さずにダミーデータを返すため、テストや開発が容易になります。
# APIを実際に使用する場合は False に設定してください。
USE_DUMMY_DATA = False

def generate_rehab_plan(patient_data):
    """
    患者データを基にプロンプトを生成し、Gemini APIにリハビリ計画の作成を依頼する。

    Args:
        patient_data (dict): 計画書作成の元となる患者データ。

    Returns:
        dict: AIが生成した計画内容の辞書。失敗した場合はエラー情報を含む辞書。
    """
    if USE_DUMMY_DATA:
        print("--- ダミーデータを使用しています ---")
        return get_dummy_plan()

    # --- プロンプトの生成 ---
    # データベースからの情報を基に、AIへの指示を具体的に組み立てる
    try:
        # 心身機能の特記事項をリストとして組み立てる
        features = []
        if patient_data.get('has_consciousness_disorder'): features.append("意識障害")
        if patient_data.get('has_dysphasia'): features.append("失語症")
        if patient_data.get('has_hemiplegia'): features.append("片麻痺")
        if patient_data.get('has_muscular_dystrophy'): features.append("筋力低下")
        # ... 設計したデータベースの項目に応じて追加 ...
        
        prompt = f"""
あなたは、リハビリテーション科の指導医です。
提供された患者データを分析し、専門的かつ具体的なリハビリテーション実施計画書の重要項目を日本語で作成してください。

# 患者データ
{{
  "年代": "{patient_data.get('age', '不明')}歳代",
  "性別": "{patient_data.get('gender', '不明')}",
  "算定病名": "{patient_data.get('main_disease', '情報なし')}",
  "特記事項": {{
    "心身機能": {json.dumps(features, ensure_ascii=False)},
    "FIM合計点": "{patient_data.get('fim_total_current', '不明')}点",
    "ADL状況": "（※この部分はDB設計に応じて追記）"
  }},
  "担当者からの所見": "{patient_data.get('therapist_notes', '特になし')}"
}}

# 作成指示
上記データを基に、以下の項目を立案してください。
各項目は、日本の医療現場で通用する、具体的で簡潔な表現を用いてください。
回答は必ずJSON形式のみで出力してください。

{{
  "risks": "（ここに安静度・リスクを記述）",
  "contraindications": "（ここに禁忌・特記事項を記述）",
  "policy": "（ここに治療方針を記述）",
  "content": "（ここに治療内容を箇条書きで記述。改行は\\nを使用）"
}}
"""
        print("--- 生成されたプロンプト ---")
        print(prompt)
        print("--------------------------")

        # --- Gemini APIの呼び出し ---
        # 使用するモデルを選択 (gemini-1.5-flashは高速・低コストです)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        # AIからの応答テキストをJSONとしてパースする
        # 不要なマークダウン(` ```json `など)をAIが含める場合があるため、除去を試みる
        cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
        ai_plan = json.loads(cleaned_text)
        return ai_plan

    except json.JSONDecodeError as e:
        print(f"JSONパースエラー: {e}")
        print(f"--- AIからの不正な応答 ---\n{response.text}\n--------------------")
        return {"error": "AIからの応答をJSONとして解析できませんでした。"}
    except Exception as e:
        print(f"Gemini API呼び出し中に予期せぬエラーが発生しました: {e}")
        return {"error": f"AIとの通信中にエラーが発生しました: {e}"}

def get_dummy_plan():
    """開発用のダミーの計画書データを返す"""
    dummy_response = {
      "risks": "高血圧症があり、訓練中の血圧変動に注意が必要。転倒リスクが高いため、移動・移乗時は必ず見守りを行う。",
      "contraindications": "右肩関節の可動域制限に対し、無理な他動運動は避けること。疼痛を誘発しない範囲で実施する。",
      "policy": "ADL（日常生活動作）の自立度向上を主目標とし、特にトイレ動作と屋内安全歩行の確立を目指す。本人の意欲を尊重し、成功体験を積めるような課題設定を行う。",
      "content": "1. 更衣動作訓練：ベッドサイドでの座位にて、麻痺側・非麻痺側双方からの着脱練習\n2. トイレ動作訓練：手すりを使用したシミュレーションと実地訓練\n3. 歩行訓練：T字杖を使用し、病棟内の直線歩行および方向転換練習"
    }
    return dummy_response

# --- このファイルが直接実行された場合のテストコード ---
if __name__ == '__main__':
    print("--- Geminiクライアントモジュールのテスト実行 ---")
    
    # テスト用の患者データを作成
    sample_patient_data = {
        "name": "テスト患者",
        "age": 75,
        "gender": "男性",
        "main_disease": "脳梗塞右片麻痺",
        "fim_total_current": 88,
        "has_dysphasia": True,
        "has_hemiplegia": True,
        "therapist_notes": "本人の退院意欲は高いが、自宅の段差に対して不安を感じている。"
    }
    
    # USE_DUMMY_DATA を False にして、実際にAPIを呼び出す
    USE_DUMMY_DATA = False
    
    # 計画生成関数を実行
    generated_plan = generate_rehab_plan(sample_patient_data)
    
    # 結果をきれいに表示
    print("\n--- 生成された計画 (結果) ---")
    import pprint
    pprint.pprint(generated_plan)
    print("--------------------------")

    if 'error' in generated_plan:
        print("\nテスト実行中にエラーが検出されました。")
    else:
        print("\nテストが正常に完了しました。")