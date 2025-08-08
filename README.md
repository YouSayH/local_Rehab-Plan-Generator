# TODOリスト https://docs.google.com/spreadsheets/d/1LUPwF4_KGJmqr2arcKsvYtvXsHZAtH2LK5qUAqHK1d0/edit?gid=1386834576#gid=1386834576
終わったタスクはチェックボックスをtrueにし、実施者がだれか明記&コミット名を書いていただけると幸いです。 <br><br>

# リハビリテーション実施計画書 自動作成システム

## 1\. 概要 (Overview)

このアプリケーションは、リハビリテーション医療の現場における「リハビリテーション実施計画書」の作成を支援するためのWebシステムです。

データベースに登録された患者情報と、担当療法士が入力した所見を基に、Googleの生成AIであるGemini APIを利用して計画書の主要項目（方針、リスク、内容など）を自動生成します。最終的な成果物は、使い慣れたExcel形式の計画書としてダウンロードできます。

これにより、書類作成業務の効率化と、より質の高いリハビリテーション計画の立案をサポートします。

-----

## 2\. 主な機能 (Features)

  * **WebベースのシンプルなUI**: ブラウザから患者を選択し、数クリックで計画書を作成できます。
  * **データベース連携**: 患者の基本情報や過去の計画書データをMySQLデータベースで管理します。
  * **AIによる計画案の自動生成**: Gemini APIを活用し、個々の患者データに応じた専門的な計画案（安静度・リスク、治療方針、治療内容など）を生成します。
  * **担当者の所見を反映**: 担当療法士の専門的な視点（特記事項や目標など）をプロンプトに組み込み、AIの生成精度を高めます。
  * **Excelファイル出力**: 生成された計画書を、指定のExcelテンプレートに書き込み、ダウンロード可能なファイルとして提供します。
  * **履歴保存**: 作成した計画書のデータはデータベースに保存され、将来の参照や分析に活用できます。

-----

## 3\. システム構成図 (Architecture)

```mermaid
%%{init:{
  'securityLevel':'loose',
  'flowchart':{ 'htmlLabels':true },
  'theme':'default',
  'themeVariables':{ 'fontSize':'18px', 'actorFontSize':'18px', 'noteFontSize':'16px' }
}}%%

graph TD
    subgraph "UI層 (ブラウザ)"
        A["<b>index.html</b><br/><i>ユーザーインターフェース</i>"]
    end

    subgraph "アプリケーション層"
        B["<b>app.py</b><br/><i>リクエスト受付・処理統括</i>"]
    end

    subgraph "サービス層"
        C["<b>gemini_client.py</b><br/><i>AIによる計画案の生成</i>"]
        D["<b>excel_writer.py</b><br/><i>Excelファイルへの書き込み</i>"]
    end

    subgraph "データアクセス層"
        E["<b>database.py</b><br/><i>DBとの接続・操作</i>"]
    end

    subgraph "外部リソース"
        F["<b>MySQL Database</b><br/>(患者情報、計画履歴)"]
        G["<b>Google Gemini API</b><br/>(AIモデル)"]
        H["<b>template.xlsx</b><br/>(Excelテンプレート)"]
    end

    %% --- 処理フロー ---
    A -- "<b>1.</b> ユーザー操作<br/>(「計画書を作成」クリック)" --> B;

    B -- "<b>2.</b> 患者データの取得を指示" --> E;
    E -- "読み込み" --> F;
    E -- "患者データ(dict)" --> B;

    B -- "<b>3.</b> AIに計画案生成を依頼" --> C;
    C -- "API呼び出し" --> G;
    C -- "AI計画案(dict)" --> B;

    B -- "<b>4.</b> Excelファイル生成を指示<br/>(DBデータとAI計画を渡す)" --> D;
    D -- "テンプレート読み込み" --> H;
    D -- "生成したファイルパス" --> B;

    B -- "<b>5.</b> 生成した計画の保存を指示" --> E;
    E -- "書き込み" --> F;

    B -- "<b>6.</b> 結果をユーザーに返却<br/>(ファイル送信、メッセージ表示)" --> A;
    
    %% --- スタイルの定義 ---
    style A fill:#cde4ff,stroke:#333,stroke-width:2px
    style B fill:#fffde7,stroke:#333,stroke-width:2px
    style C fill:#d5e8d4,stroke:#333,stroke-width:2px
    style D fill:#d5e8d4,stroke:#333,stroke-width:2px
    style E fill:#ffe6cc,stroke:#333,stroke-width:2px
    style F fill:#f8cecc,stroke:#333,stroke-width:2px
    style G fill:#f8cecc,stroke:#333,stroke-width:2px
    style H fill:#f8cecc,stroke:#333,stroke-width:2px
```
-----

## 4\. 使用技術 (Technology Stack)

  * **バックエンド**: Python, Flask
  * **フロントエンド**: HTML, CSS, JavaScript
  * **データベース**: MySQL
  * **AIエンジン**: Google Gemini API
  * **Pythonライブラリ**: `flask`, `PyMySQL`, `cryptography`, `google-generativeai`, `openpyxl`, `python-dotenv`

-----

## 5\. セットアップと実行方法 (Getting Started)

### 5.1. 前提条件

  * Python 3.8 以降がインストールされていること。
  * MySQL Serverがインストールされ、起動していること。
  * Google Cloud Platform (Google AI Stadio https://aistudio.google.com/apikey )でAPIキーを取得済みであること。

### 5.2. セットアップ手順

**1. リポジトリのクローン**

```bash
git clone https://github.com/YouSayH/kcr_Rehab-Plan-Generator.git
cd kcr_Rehab-Plan-Generator
```

**2. Python仮想環境の作成と有効化**

```bash
# Windows
python -m venv venv_rehab
.\venv_rehab\Scripts\activate

# macOS / Linux
python3 -m venv venv_rehab
source venv_rehab/bin/activate
```

**3. 依存ライブラリのインストール**

```bash
pip install -r requirements.txt
```

**4. `.env`ファイルの作成と設定**
APIキーなどの機密情報を格納するため、手動で`.env`ファイルを作成し、以下の内容を記述します。値はご自身の環境に合わせて設定してください。

```
# --- データベース接続情報 ---
DB_HOST="localhost"
DB_USER="your_db_user"
DB_PASSWORD="your_db_password"
DB_NAME="rehab_db"

# --- Google APIキー ---
GOOGLE_API_KEY="your_google_api_key_here"
```

> `your_db_user`にはMySQLのユーザー名（例: `root`）を、`your_db_password`にはそのパスワードを入力します。

**5. データベースのセットアップ** ⚙️
本システムは、データベースやファイルが **UTF-8** 文字コードで扱われることを前提としています。

**(Windows利用者向け) 文字コードの設定**
まず、ターミナル（コマンドプロンプトやPowerShell）で以下のコマンドを実行し、文字コードをUTF-8に設定してください。この設定は、MySQLコマンドを実行する前に行います。

```bash
chcp 65001
```

次に、以下のいずれかの方法で `schema.sql` ファイルを実行し、データベースとテーブルを構築します。

-----

#### **方法A：コマンドから直接実行する（推奨）**

ターミナルから直接SQLファイルを読み込ませて実行する、最も簡単な方法です。

```bash
mysql -u your_user -p < schema.sql
```

  * コマンド実行後、パスワードを入力すると、データベースの構築が自動的に完了します。

-----

#### **方法B：MySQLにログインしてから実行する**

対話的に操作したい場合や、方法Aでうまくいかない場合の方法です。

1.  **MySQLにログイン:**
    ```bash
    mysql -u your_user -p
    ```
2.  **`source`コマンドで実行:**
    `mysql>` プロンプトが表示されたら、`source`コマンドで `schema.sql` のあるファイルパスを指定して実行します。
    ```sql
    mysql> source /path/to/your/project/kcr_Rehab-Plan-Generator/schema.sql;
    ```
3.  **MySQLからログアウト:**
    ```sql
    mysql> exit;
    ```

-----

**6. アプリケーションの起動**

```bash
python app.py
```

起動後、Webブラウザで `http://127.0.0.1:5000` にアクセスしてください。

-----

## 6\. ファイル構成 (File Structure)

```
C:.
│  .env                   # 【要手動作成】環境変数ファイル (Git管理外)
│  .gitignore             # Gitの無視設定ファイル
│  app.py                 # Flaskアプリケーションのメインファイル
│  database.py            # DBとの接続・操作モジュール
│  excel_writer.py        # Excelファイル生成モジュール
│  gemini_client.py       # Gemini APIとの通信モジュール
│  README.md              # このファイル
│  requirements.txt       # Pythonの依存ライブラリリスト
│  schema.sql             # DBスキーマ定義とサンプルデータ
│  template.xlsx          # 計画書のExcelテンプレート
│
├─output/                 # 【自動生成】生成されたExcelファイルの保存先 (Git管理外)
│      ...
│
└─templates/
      index.html          # フロントエンドのHTMLテンプレート
```

-----

## 7\. トラブルシューティング (Troubleshooting) 🛠️

  * **エラー: `(1049, "Unknown database 'rehab_db'")`**

      * **原因**: データベースが作成されていません。
      * **解決策**: 上記「5. データベースのセットアップ」の手順を実行してください。

  * **エラー: `ERROR 1406 (Data too long)` や `ERROR 1366 (Incorrect string value)`**

      * **原因**: データベースまたはターミナルの文字コードが日本語に対応していません。
      * **解決策**: 上記「5. データベースのセットアップ」の手順、特にWindows向けの文字コード設定(`chcp 65001`)を見直してください。

  * **エラー: `'cryptography' package is required...`**

      * **原因**: `PyMySQL` がMySQL 8.0以降の認証方式で利用する `cryptography` ライブラリがインストールされていません。
      * **解決策**: `pip install cryptography` を実行し、`requirements.txt` にも `cryptography` を追記してください。

-----

## 8\. 注意事項 (Notes)

  * このシステムはプロトタイプです。`app.py` 内の `SECRET_KEY` は、本番環境で運用する際には必ず複雑で安全なものに変更してください。
  * `app.py` はFlaskの開発用サーバーで動作します。本番環境では、GunicornやuWSGIなどのWSGIサーバーを使用することを強く推奨します。

  * `gemini_client.py` の `USE_DUMMY_DATA` フラグを `True` にすると、APIを呼び出さずにテスト用のダミーデータを使用できます。
