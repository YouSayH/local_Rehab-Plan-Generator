import os
from datetime import datetime
from openpyxl import load_workbook

# --- 定数設定 ---
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

    # --- ここから書き込み処理 ---
    # openpyxlのルール：結合セルに書き込む際は、必ずその結合領域の「左上」のセルに書き込む必要があります。
    
    # --- 通常のセルへの書き込み ---
    ws['C4'] = patient_data.get('name', '')
    ws['C5'] = patient_data.get('main_disease', '')
    ws['S4'] = patient_data.get('gender', '')
    ws['AC4'] = patient_data.get('age', '')
    
    # 日付
    eval_date = patient_data.get('evaluation_date')
    onset_date = patient_data.get('onset_date')
    rehab_date = patient_data.get('rehab_start_date')
    ws['AJ4'] = eval_date.strftime('%Y-%m-%d') if eval_date else ''
    ws['AJ5'] = onset_date.strftime('%Y-%m-%d') if onset_date else ''
    ws['AJ6'] = rehab_date.strftime('%Y-%m-%d') if rehab_date else ''

    # --- 結合セルへの書き込み (左上のセルを明示的に指定) ---
    ws['C8'] = ai_plan.get('comorbidities', '') # 併存疾患・合併症 (C8が左上)
    ws['S8'] = ai_plan.get('risks', '')             # 安静度・リスク (S8が左上)
    ws['AH8'] = ai_plan.get('contraindications', '') # 禁忌・特記事項 (AH8が左上)
    ws['B78'] = ai_plan.get('policy', '')            # 治療方針 (B78が左上)
    ws['R78'] = ai_plan.get('content', '')           # 治療内容 (R78が左上)

    # --- チェックボックス用の制御セル (これらは結合されていない前提) ---
    ws['XA6'].value = patient_data.get('is_physical_therapy', False)
    ws['XB6'].value = patient_data.get('is_occupational_therapy', False)
    ws['XC6'].value = patient_data.get('is_speech_therapy', False)

    # --- FIMスコア (これらも結合されていない前提) ---
    ws['I35'].value = patient_data.get('fim_start_eating')
    ws['S35'].value = patient_data.get('fim_current_eating')
    # (必要に応じて他のFIM項目も同様に追加)

    # --- ファイルを保存 ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_patient_name = "".join(c for c in patient_data.get('name', 'NoName') if c.isalnum())
    output_filename = f"RehabPlan_{safe_patient_name}_{timestamp}.xlsx"
    output_filepath = os.path.join(OUTPUT_DIR, output_filename)
    
    wb.save(output_filepath)
    print(f"計画書を {output_filepath} に保存しました。")

    return output_filepath