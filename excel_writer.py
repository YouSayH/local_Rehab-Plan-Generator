import os
from datetime import datetime
from openpyxl import load_workbook

# 定数設定
TEMPLATE_PATH = "template.xlsx"
OUTPUT_DIR = "output"


def create_plan_sheet(patient_data, ai_plan):
    """
    Excelテンプレートを基に、リハビリテーション実施計画書を作成する。
    """
    # 出力ディレクトリが存在しない場合は作成
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    try:
        # テンプレートファイルを読み込む
        wb = load_workbook(TEMPLATE_PATH)
        ws = wb.active
    except FileNotFoundError:
        print(f"エラー: テンプレートファイル '{TEMPLATE_PATH}' が見つかりません。")
        raise

    # ここから書き込み処理
    # TODO セル番号をハードコーディング→Excelの「名前の定義」機能（Named Ranges）で検知させる(例:F3セル→PatientName  ws["PatientName"] = ...)
    # openpyxlのルール：結合セルに書き込む際は、必ずその結合領域の「左上」のセルに書き込む必要があります。
    # TODO セル番号と内容の増設
    # 患者の基本情報
    ws["F3"] = patient_data.get("name", "")
    ws["B5"] = patient_data.get("main_disease", "")
    ws["R3"] = patient_data.get("gender", "")
    ws["AC3"] = patient_data.get("age", "")

    # 日付
    eval_date = patient_data.get("evaluation_date")
    onset_date = patient_data.get("onset_date")
    rehab_date = patient_data.get("rehab_start_date")
    ws["AN3"] = eval_date.strftime("%Y-%m-%d") if eval_date else ""
    ws["AN4"] = onset_date.strftime("%Y-%m-%d") if onset_date else ""
    ws["AN5"] = rehab_date.strftime("%Y-%m-%d") if rehab_date else ""

    # AIが生成した計画書の内容
    # 結合セルへの書き込み (左上のセルを明示的に指定)
    ws["B8"] = ai_plan.get("comorbidities", "")  # 併存疾患・合併症 (C8が左上)
    ws["R8"] = ai_plan.get("risks", "")  # 安静度・リスク (S8が左上)
    ws["AH8"] = ai_plan.get("contraindications", "")  # 禁忌・特記事項 (AH8が左上)
    ws["B79"] = ai_plan.get("policy", "")  # 治療方針 (B79が左上)
    ws["Z79"] = ai_plan.get("content", "")  # 治療内容 (Z79が左上)

    # TODO チェックボックスはOpenPyXLで使えない(消えてしまう)ため今後、チェックボックスを使わず、文字(☑☐)で表現するようにする
    # # チェックボックス用の制御セル (これらは結合されていない前提)
    # ws['XA6'].value = patient_data.get('is_physical_therapy', False)
    # ws['XB6'].value = patient_data.get('is_occupational_therapy', False)
    # ws['XC6'].value = patient_data.get('is_speech_therapy', False)

    # # FIMスコア (これらも結合されていない前提)
    # ws['I35'].value = patient_data.get('fim_start_eating')
    # ws['S35'].value = patient_data.get('fim_current_eating')
    # # (必要に応じて他のFIM項目も同様に追加)

    # ファイルを保存
    # タイムスタンプを使って、ファイル名が他のファイルと重複しないようにしている
    # TODO もっといい方法を考えたい: 担当者名+タイムスタンプとか
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_patient_name = "".join(c for c in patient_data.get("name", "NoName") if c.isalnum())
    output_filename = f"RehabPlan_{safe_patient_name}_{timestamp}.xlsx"
    output_filepath = os.path.join(OUTPUT_DIR, output_filename)

    # メモリ上で変更した内容を、新しいファイルとしてディスクに書き込みます。
    wb.save(output_filepath)
    print(f"計画書を {output_filepath} に保存しました。")

    # app.py側でダウンロードさせるファイルがどれか分かるように、ファイルパスを返す。
    return output_filepath
