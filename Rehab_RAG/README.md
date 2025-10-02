# Rehab\_RAG: 理学療法ガイドラインのためのRAG手法評価・検証リポジトリ

[![Project Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](https://github.com/YouSayH/Rehab_RAG)


## 概要 (Overview)

このリポジトリは、理学療法（リハビリテーション）領域の臨床ガイドラインなどの専門文書に対し、**最適なRAG (Retrieval-Augmented Generation) パイプラインを体系的に探求・評価する**ための実験フレームワークです。

最終的な目標は、臨床現場の専門家が持つ疑問に対し、膨大なガイドラインの中から、迅速かつ正確に、そして根拠を持って回答を提示できるAIアシスタントを構築することです。

### 🎯 このプロジェクトの特徴

  * **🧪 コンポーネント化された設計**: RAGの各プロセス（DB構築、検索、判断等）を独立した部品（コンポーネント）として管理。
  * **⚙️ 柔軟な実験設定**:  ルートディレクトリの`rag_config.yaml`を編集するだけで、様々なRAGパイプラインの切り替えが可能です。また、`config.yaml`ファイルを編集するだけで、様々なコンポーネントの組み合わせを簡単に試し、手法のON/OFFを切り替えられます。
  * **📊 定量的な評価**: `Ragas`フレームワークを導入し、「回答の忠実性」や「文脈の再現率」といった客観的な指標で各パイプラインの性能を評価します。

-----

## 📂 ディレクトリ構成

このプロジェクトは、RAGの各コンポーネントをモジュールとして管理し、それらを柔軟に組み合わせて実験・評価できるよう設計されています。

```
Rehab_RAG/
│
├── 📁 source_documents/
│   └── 📄 ...
│
├── 📁 rag_components/
│   ├── 📁 builders/
│   ├── 📁 chunkers/
│   │   ... (各種コンポーネント)
│   └── 📁 retrievers/
│
├── 📁 experiments/
│   └── 📁 <実験名>/
│       ├── 📜 config.yaml         # 個別の実験設定
│       ├── 🐍 build_database.py
│       ├── 🐍 query_rag.py (廃止)
│       └── 🗃️ db/
│
├── 📁 evaluation/
│   ├── 🐍 evaluate_rag.py
│   ├── 📄 test_dataset.jsonl
│   └── 📁 logs/
│
├── 🐍 query_rag.py
├── 🐍 schemas.py
├── 📜 rag_config.yaml              # パイプライン切り替え用設定
├── 🔑 .env
└── 📋 requirements.txt
```

### 各要素の詳細

#### `📁 source_documents/`

**RAGシステムの知識源となるMarkdownファイル**を格納します。ここに置かれた文書がチャンキング（分割）され、ベクトルデータベースに登録されます。

#### `📁 rag_components/`

RAGパイプラインを構成する各機能が、**再利用可能なPythonクラスとしてモジュール化**されています。新しい手法を試す際は、このディレクトリに新しいコンポーネントを追加します。

  * `builders/`: DB構築の戦略全体（RAPTORなど）を定義するコンポーネント。
  * `chunkers/`: テキストを意味のある塊（チャンク）に分割するロジック。
  * `embedders/`: テキストをベクトルに変換するモデルのラッパー。
  * `filters/`: 検索結果からノイズや矛盾する情報を除去する処理。
  * `judges/`: パイプラインの動作を動的に判断・制御する処理（Self-RAG）。
  * `llms/`: 回答生成モデル（Geminiなど）とのAPI通信を管理するラッパー。
  * `query_enhancers/`: ユーザーの質問を検索用に拡張・変換する処理。
  * `rerankers/`: 検索結果をより精度の高いモデルで並べ替える処理。
  * `retrievers/`: ベクトルDBとのやり取り（保存・検索）を担当。

#### `📁 experiments/`

様々なRAGコンポーネントの組み合わせ（＝パイプライン）を試すための**実験室**です。各サブディレクトリが、それぞれ独立した一つの実験設定に対応します。

  * `📁 <実験名>/`: ディレクトリ名は、その実験で採用している手法の組み合わせを表します。
      * `📜 config.yaml`: その実験で使用する**コンポーネントやモデルを指定する、最も重要な設定ファイル**です。
      * `🐍 build_database.py`: `config.yaml`に従い、ベクトルDBを構築するスクリプト。
      * `🗃️ db/`: `build_database.py`によって構築されたChromaDBのデータが保存される場所。

#### `📁 evaluation/`

構築したRAGパイプラインの性能を**定量的に評価するための専用ディレクトリ**です。

  * `🐍 evaluate_rag.py`: 指定した実験設定（パイプライン）を、テストデータセットを用いて自動評価するスクリプト。
  * `📄 test_dataset.jsonl`: 評価に使用する「質問」と「理想的な回答（正解データ）」のペアを格納したファイル。
  * `📁 logs/`: `evaluate_rag.py`を実行した際の評価スコア（CSV形式）と詳細な実行ログが保存されます。


#### `📁 ルートディレクトリ`

  * `🐍 query_rag.py`: **全てのRAGパイプラインを実行するための統一されたスクリプト**です。`rag_config.yaml`の設定を読み込み、指定されたパイプラインを動的にロードして実行します。
  * `🐍 schemas.py`: LLMに**構造化されたJSON形式で回答を生成させる**ための、Pydanticによるデータスキーマを定義しています。これにより、回答の形式を安定させ、アプリケーションのバックエンドで扱いやすい出力を得ることができます。
  * `📜 rag_config.yaml`: **どの実験パイプラインを有効にするかを指定するマスターコントロールファイル**です。このファイルの`active_pipeline`の値を変更するだけで、実行するRAGの構成を簡単に切り替えられます。



-----

## セットアップ (Setup)

1.  **リポジトリのクローン**

    ```bash
    git clone https://github.com/YouSayH/Rehab_RAG.git
    cd Rehab_RAG
    ```

2.  **仮想環境の作成と有効化**

    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **必要なライブラリのインストール**

    ```bash
    pip install -r requirements.txt
    ```


4.  **APIキーとデータベース情報の設定**
    プロジェクトのルートディレクトリに `.env` という名前のファイルを作成し、お使いのAPIキーやデータベース接続情報を記述します。

    ```.env
    GEMINI_API_KEY="ここにあなたのAPIキーを貼り付けてください"

    # Graph RAG (Neo4j) 利用時に必要(後述)
    NEO4J_URI="neo4j://127.0.0.1:7687"
    NEO4J_USERNAME="neo4j"
    NEO4J_PASSWORD="your_neo4j_password"
    ```

5.  **（ハイブリッド検索利用時）MeCabのインストール**
    ハイブリッド検索機能 (`HybridRetriever`) を使用するには、形態素解析エンジンMeCabのインストールが別途必要です。

    a. **MeCab本体のインストール**

      * **Windows**: [こちらのリリース](https://github.com/ikegami-yukino/mecab/releases/tag/v0.996.2)から `mecab-0.996-64.exe` 等のインストーラーをダウンロードして実行します。**必ず辞書は `UTF-8` を選択してください。**
      * **Mac**: `brew install mecab mecab-ipadic`
      * **Linux**: `sudo apt-get install mecab libmecab-dev mecab-ipadic-utf8`

    b. **環境変数の設定 (Windowsのみ)**

    Windowsでは、`mecab-python3`がMeCab本体を見つけられるように、システム環境変数を設定する必要があります。

      * **変数名**: `MECABRC`
      * **変数値**: `C:\Program Files\MeCab\etc\mecabrc` （※インストール先のパスに合わせて変更してください）

6.  **（オプション）Neo4j Desktopのセットアップ**
    知識グラフを活用する`GraphBuilder`および`GraphRetriever`を使用するには、Neo4jデータベースのセットアップが必要です。

    **1. Neo4j Desktopのインストール**

      * \*\*[Neo4j Desktop公式サイト](https://neo4j.com/download/)\*\*からご使用のOSに合ったインストーラーをダウンロードし、インストールします。
      * 初回起動時にアクティベーションキーを入力し、利用登録を完了させてください。


    **2. データベース(DBMS)の作成と起動**

      1.  Neo4j Desktopの`Local instances`画面で、右上の`Create instance`を選択します。
      2.  `Instance Name`（例: `Rehab_test`）と`Password`を入力し、`Create`ボタンを押します。
            * **重要**: ここで設定したパスワードは後ほど`.env`ファイルで使用しますので、忘れないようにしてください。
      3.  APOCプラグインの有効化(詳細は後述)
      4.  作成されたインスタンスの「Start instance」ボタン◯▶️を押し、ステータスが「RUNNING」（緑色のランプ）になるのを待ちます。


    **3. APOCプラグインの有効化**

      これは、LangChainがグラフ構造を読み取るために**必須の拡張機能**です。

      1.  対象のDBMSインスタンスが**停止**していることを確認します。
      2.  インスタンスカード右上の「...」メニューから「Plugins」を選択します。
      3.  リスト内の「APOC」を探し、「Install」ボタンをクリックします。
      4.  再度「...」メニューから「Open neo4j.conf」を選択し、設定ファイルをテキストエディタで開きます。
      5.  ファイルの末尾に以下の1行を**追記**します。
            * **注意**: 近年のバージョンではAPOCインストール時に自動で追記されることがあります。その場合は重複して記述する必要はありません。
          ```
          dbms.security.procedures.unrestricted=apoc.*
          ```
      6.  ファイルを上書き保存し、インスタンスを再度起動します。エラーが出なければセットアップ成功です。


    **4. Pythonライブラリの更新**

      Graph RAG関連のライブラリを最新の安定版にアップグレードします。

      1.  プロジェクトの仮想環境を有効化します。
      2.  ターミナルで以下のコマンドを実行してください。
          ```bash
          pip install --upgrade langchain langchain-neo4j langchain-core langchain-google-genai pydantic
          ```


    **5. `.env`ファイルへの追記**

      プロジェクトのルートディレクトリにある`.env`ファイルに、Neo4jデータベースへの接続情報を追記します。

        ```.env
        GEMINI_API_KEY="ここにあなたのAPIキーを貼り付けてください"

        # Graph RAG (Neo4j) 利用時に必要
        NEO4J_URI="neo4j://127.0.0.1:7687"
        NEO4J_USERNAME="neo4j"
        NEO4J_PASSWORD="your_neo4j_password"
        ```


## 使い方 (Usage)


RAGパイプラインの実験と評価は、以下の4ステップで行います。

### ステップ1: 実行するパイプラインの選択 (`rag_config.yaml`)

プロジェクトルートにある **`rag_config.yaml`** を開き、`active_pipeline`に使用したい実験ディレクトリ名を指定します。

```yaml
# ここで実行したいRAGパイプラインの名前を指定するだけ
active_pipeline: "graph_rag_experiment"
# active_pipeline: "hybrid_search_experiment"
# ...
```

### ステップ2: 実験内容の定義 (`config.yaml`)

`experiments/<実験名>/config.yaml` を開き、使用したいコンポーネントを定義します。

**手法のON/OFFは、該当セクションをコメントアウトするだけ**で簡単に行えます。

```yaml
query_components:
  # ... (llm, embedder, retrieverは必須)

  # [クエリ拡張] HyDEを無効にする場合は、以下の3行をコメントアウト
  query_enhancer:
    module: rag_components.query_enhancers.hyde_generator
    class: HydeQueryEnhancer

  # [リランキング] Rerankerを無効にする場合は、以下の4行をコメントアウト
  reranker:
    module: rag_components.rerankers.cross_encoder_reranker
    class: CrossEncoderReranker
    params:
      model_name: "BAAI/bge-reranker-v2-m3"

  # [フィルタリング] NLI Filterを無効にする場合は、以下の4行をコメントアウト
  filter:
    module: rag_components.filters.nli_filter
    class: NLIFilter
    params:
      model_name: "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
```


### ステップ3: データベースの構築 (`build_database.py`)

`active_pipeline`で指定した実験の`config.yaml`に従い、知識源からDBを構築します(.\experiments\<実験名>\上にdbフォルダーができます。)。

```bash
# プロジェクトのルートディレクトリから、対象の実験フォルダ内にあるbuild_database.pyを実行
python .\experiments\<実験名>\build_database.py
```

**注意**: `graph_rag_experiment`のようにGraph RAGを使用する場合、このステップでNeo4jデータベースにナレッジグラフが構築されます。

### ステップ3: パイプラインの動作確認 (`query_rag.py`)

**プロジェクトのルートディレクトリにある`query_rag.py`** を実行します。`rag_config.yaml`で指定されたパイプラインが自動で読み込まれ、対話形式で動作確認ができます。

```bash
# プロジェクトのルートディレクトリから実行
python query_rag.py
```

### ステップ4: 定量的評価の実行 (`evaluate_rag.py`)

テストデータセットを使い、RAGパイプラインの性能を客観的なスコアで評価します。

```bash
# プロジェクトのルートディレクトリから実行
python evaluation/evaluate_rag.py experiments/<実験名>

# (オプション) 最初の3件だけを評価する場合
python evaluation/evaluate_rag.py experiments/<実験名> --limit 3
```

実行後、`evaluation/logs/`に`scores_...csv`と`log_...log`が生成されます。



-----

## 評価指標 (Evaluation with Ragas)

このプロジェクトでは、`Ragas`フレームワークを用いてRAGパイプラインの性能を多角的に評価します。主な指標は以下の通りです。

| 指標 | 評価する内容 |
| :--- | :--- |
| **Faithfulness** | 生成された回答が、検索された文脈（参考情報）にどれだけ忠実か。ハルシネーション（幻覚）の度合いを測る。 |
| **Answer Relevancy** | 生成された回答が、元の質問にどれだけ的確か。質問の意図を汲み取れているかを測る。 |
| **Context Precision** | 検索された文脈の中で、実際に回答生成に必要だった情報の割合。検索結果のノイズの少なさを測る。 |
| **Context Recall** | 正解データと比較して、検索された文脈が回答に必要な情報をどれだけ網羅できているか。検索の再現率を測る。 |

これらのスコアを比較することで、どのコンポーネントの組み合わせが最も優れたパイプラインを構築できるかを判断します。

-----

## RAGコンポーネント解説

本フレームワークは、責務が明確に分離された複数のコンポーネントで構成されています。各コンポーネントを入れ替えることで、RAGパイプラインの性能を体系的に評価することが可能です。

### データベース構築フェーズ (`build_database.py`)

知識源となるドキュメント群を、検索および生成に適した形式のベクトルデータベースへと変換する事前処理フェーズです。

| コンポーネントの種類 | 責務・役割 | 詳細解説 |
| :--- | :--- | :--- |
| **`Builder`** | **DB構築戦略の定義** | データベースを構築するための全体的なワークフローを定義・実行します。 <br> ・**`DefaultBuilder`**: `Chunker`→`Embedder`→`Retriever`という直線的なプロセスで、標準的なベクトルデータベースを構築します。 <br> ・**`RAPTORBuilder`**: 文書群を再帰的にクラスタリングし、要約を生成するプロセスを通じて、情報の階層構造を持つベクトルデータベースを構築します。これにより、質問の抽象度に応じた多角的な情報検索が可能になります。 <br>・**`GraphBuilder`**: **(New\!)** テキストからエンティティと関係性を抽出し、Neo4jにナレッジグラフを構築します。複雑な関係性の問いに強くなります。 |
| **`Chunker`** | **文書の分割** | 元の文書を、意味的な一貫性を保ちながら検索に適した単位（チャンク）に分割します。 <br> ・**`StructuredMarkdownChunker`**: Markdownの文書構造（見出しレベル）を解析し、セクション単位での文脈を維持したままチャンクを生成します。 |
| **`Embedder`** | **テキストのベクトル化** | 各チャンクを、セマンティックな意味を捉えた高次元の数値ベクトル（Embedding）に変換します。 <br> ・**`SentenceTransformerEmbedder`**: ローカル環境で実行可能な事前学習済みモデルを利用し、テキストをベクトル化します。 <br> ・**`GeminiEmbedder`**: Googleの提供する大規模モデルAPIを利用し、より高品質なベクトル表現を生成します。 |


-----

### クエリ実行フェーズ (`query_rag.py`)

ユーザーからの質問を受け付け、構築されたデータベースを用いて最適な回答を生成するリアルタイム処理フェーズです。

| コンポーネントの種類 | 責務・役割 | 詳細解説 |
| :--- | :--- | :--- |
| **`Judge`** | **検索要否の判断** | **(Self-RAG)** ユーザーの質問に対し、外部知識（データベース検索）が必要か否かをLLMが判断します。 <br> ・**`RetrievalJudge`**: 挨拶や一般的な対話など、検索が不要なクエリを識別し、後続のRAGプロセスをスキップすることで、応答の効率化と低コスト化を実現します。 |
| **`Query Enhancer`** | **検索クエリの拡張** | ユーザーの入力クエリを、検索精度を向上させるためにより効果的な形式に変換または拡張します。 <br> ・**`HydeQueryEnhancer`**: 質問に対する架空の理想的な回答（Hypothetical Document）をLLMに生成させ、その内容で検索することで、潜在的なキーワードを補完します。 <br> ・**`MultiQueryGenerator`**: 単一の質問を、LLMを用いて複数の異なる視点を持つサブクエリ群に分解し、検索の網羅性を向上させます。 |
| **`Retriever`** | **関連文書の検索** | ベクトル化されたクエリを用いて、データベースから関連性の高い上位k件のチャンクを検索（リトリーブ）します。 <br> ・**`ChromaDBRetriever`**: ベクトル間の類似度計算（コサイン類似度など）のみに基づき、高速に検索を実行します。 <br> ・**`HybridRetriever`**: 意味的な類似性で検索するベクトル検索と、キーワードの一致で検索するBM25を組み合わせ、Reciprocal Rank Fusion (RRF)で結果を統合することで、検索の再現率と適合率の両立を目指します。 <br>・**`GraphRetriever`**: 自然言語の質問からキーワードを抽出し、Neo4jナレッジグラフを横断的に検索して関連情報を取得します。 |
| **`Reranker`** | **検索結果の再ランキング** | `Retriever`によって取得された候補群を、より計算コストが高いが精度の優れたモデルで再評価し、関連性の高い順に並べ替えます。 <br> ・**`CrossEncoderReranker`**: 質問と候補チャンクをペアで入力として受け取り、文脈的な関連性をより深く考慮したスコアリングを行います。 |
| **`Filter`** | **候補文書のフィルタリング** | リランキング後の候補群から、ノイズや矛盾を含む不適切な情報を除去し、最終的なコンテキストの品質を向上させます。 <br> ・**`NLIFilter`**: 自然言語推論（NLI）モデルを用い、質問と候補チャンクの関係が論理的に「矛盾(Contradiction)」していないかを判定し、矛盾する情報を除外します。 <br> ・**`SelfReflectiveFilter`**: **(Self-RAG)** 候補チャンクが質問に回答するための根拠として適切かをLLM自身が評価（[RELEVANT] / [IRRELEVANT]）し、より厳密な基準でコンテキストを精選します。 |
| **`LLM`** | **最終回答の生成** | 厳選された最終的なコンテキストと元の質問をプロンプトとして、大規模言語モデル（LLM）がユーザーへの回答を生成します。`schemas.py`と連携することで、**構造化されたJSON形式での出力も可能**です。 |
-----





## 🗺️ 今後の検証ロードマップ (Future Validation Roadmap)

### フェーズ1: 盤石な信頼性基盤の完成 (STEP 1-5)
**目標**: まずはAIの回答が**「絶対に信頼できる」**状態を目指します。ハルシネーションを徹底的に排除し、全ての回答の根拠を明確にすることで、臨床現場での利用に耐えうる基盤を完成させます。

| ステップ | 実装する手法 | 目的・ゴール |
| :--- | :--- | :--- |
| **STEP 5 (次回)** | **ナレッジグラフ活用RAG (GraphRAG)** | 疾患・薬剤・治療法といった医療用語の関係性をグラフで表現し、「AとBを併用禁忌とする疾患は？」のような複雑な関係性の問いに答えられるようにする。 |
| **STEP 6** | **根拠優先RAG (Provenance-first RAG)** | AIの回答に、**どの文書のどの部分を根拠にしたのか**を常に明示させる。医師が回答の妥当性を瞬時に検証できる、透明性の高いシステムを構築する。 |
| **STEP 7** | **自己検証ループ (Chain-of-Verification)** | AIが生成した回答に対し、「この回答は本当に正しいか？」と自問自答させ、**再度検索してファクトチェックを行う**自己修正ループを実装する。医療過誤を防ぐ安全機構。 |
| **STEP 8** | **検索拡張ファインチューニング (RAFT)** | 検索に失敗した質の悪い文書や、わざと関連性の低い文書をAIに見せ、「このような情報が来ても、惑わされずに正しい答えを出せるか？」という特殊な訓練（ファインチューニング）を行う。ノイズに強い頑健なモデルを育成する。 |
| **STEP 9** | **体系的な性能評価ベンチマークの構築** | これまで実装した全手法の組み合わせ（例: RAPTOR + Hybrid + Self-RAG）の性能を`evaluate_rag.py`で網羅的に測定し、**どの組み合わせが最も優れているか**を定量的に評価する。 |

<br>

### フェーズ2: 検索・構築技術の深化 (STEP 10-14)
**目標**: データベースの「作り方」と「探し方」をさらに洗練させ、情報の見落としをなくし、より質の高い根拠（コンテキスト）をAIに提供できるようにします。

| ステップ | 実装する手法 | 目的・ゴール |
| :--- | :--- | :--- |
| **STEP 10** | **チャンキング手法の体系的比較** | 文書の分割方法（チャンキング）はRAGの性能を大きく左右する。**適応的チャンキング**（文書の内容に応じて分割サイズを変える）などを実装し、どの手法が医療文書に最適かを見極める。 |
| **STEP 11** | **高度なベクトル検索 (ColBERT)** | 文書全体を一つのベクトルで表現するのではなく、単語やフレーズ単位でベクトル化し、**よりきめ細やかな検索**を可能にする`ColBERT`を実装する。見つけにくかった細かな情報も捉えられるようにする。 |
| **STEP 12**| **時間認識RAG (Temporal-Aware RAG)** | 文書の公開日や更新日時をメタデータとして重視し、「最新のガイドライン」や「過去1年以内の論文」といった**時間的な制約を考慮した検索**を可能にする。情報の鮮度を保証する。 |
| **STEP 13**| **専門家ルーター (Expert-Router)** | 質問の意図をAIが読み取り、「これは薬の質問だから薬学DBへ」「これはリハビリの質問だから理学療法ガイドラインへ」と、**最適な情報源を自動で選択**する司令塔を実装する。 |
| **STEP 14**| **根拠の細粒度化 (Micro-evidence / Span-level Retrieval)**| 文書全体や段落だけでなく、回答の根拠となる**一文やフレーズだけをピンポイントで抽出**する能力を実装する。LLMに与える情報のノイズを極限まで減らす。 |

<br>

### フェーズ3: LLM推論能力の最大化 (STEP 15-17)
**目標**: 検索してきた情報を、LLMがより深く、多角的に「思考」し、人間のような推論プロセスを経て回答を生成できるようにします。

| ステップ | 実装する手法 | 目的・ゴール |
| :--- | :--- | :--- |
| **STEP 15**| **思考の連鎖 (Chain-of-Thought RAG)**| 質問に対してすぐに答えを出すのではなく、「まずAを調べて、次にBを考慮し、その結果Cという結論に至る」というように、**思考のプロセスを段階的に記述**させながら回答を生成させる。複雑な問いに対する論理的推論能力を向上させる。 |
| **STEP 16**| **証拠グラフの構築 (Chain-of-Evidence Graph)**| 複数の検索結果（証拠）の関係性をAIに分析させ、「証拠Aと証拠Bは互いに支持している」「証拠CはAと矛盾する」といった**証拠間の関係グラフ**を動的に構築させる。情報の信頼性をより深く評価する。 |
| **STEP 17**| **マルチエージェント討論 (DebateRAG)**| 1つの問いに対し、**肯定派、否定派、中立派など、異なる役割を持つ複数のAIエージェント**に回答を生成させ、最後に審判役がそれらを統合して結論を出す。単一の視点に偏らない、バランスの取れた回答を生成する。 |

<br>

### フェーズ4: 自律性と継続的改善 (STEP 18-20)
**目標**: AI自身が継続的に賢くなり、運用性を高め、公平性を担保する、自律的なシステムへと進化させます。

| ステップ | 実装する手法 | 目的・ゴール |
| :--- | :--- | :--- |
| **STEP 18**| **継続的学習 (Continual Learning RAG)**| 新しいガイドラインや論文が追加された際に、**差分だけを効率的に学習・更新**する仕組みを導入する。また、医師からのフィードバック（例：「この回答は役に立った」）を記録し、それを元に検索精度を自動で改善させる。 |
| **STEP 19**| **公平性・多様性配慮 (Fairness-Aware Retrieval)**| 検索結果が特定の論文や治療法に偏らないよう、**情報源の多様性を評価**し、バランスの取れた根拠を提示するようAIを制御する。診断や治療方針の偏りを防ぐ。 |
| **STEP 20**| **説明可能性の強化 (Explainable RAG)**| なぜAIがその回答に至ったのか、という思考プロセス全体（どのルーターを選択し、どの根拠をどう解釈し、なぜ他の選択肢を棄却したか）を**人間が理解できる形で可視化**する。AIの判断プロセスをブラックボックスにしない。 |

<br>

### 未来展望 (Future Vision)
上記の20ステップを達成した先に、病院システムとの完全統合という究極の目標があります。これらは技術的・倫理的ハードルが極めて高いため、長期的な研究開発課題とします。

* **マルチモーダルRAG**: レントゲン画像やCT画像なども含めて検索・回答する。
* **ツール拡張RAG**: 電子カルテや各種医療システムとAPIで直接連携する。
* **プライバシー保護RAG**: 連合学習や暗号化技術を駆使し、個人情報を完全に保護しながらRAGを利用する。
---

## 各手法の技術的背景と参考文献

本プロジェクトで実装された各コンポーネントは、近年の自然言語処理および情報検索の研究成果に基づいています。ここでは、主要な手法に関する技術的背景と、原典となる論文を紹介します。

### HyDE (Hypothetical Document Embeddings)

* **技術解説**: ユーザーのクエリから直接ベクトルを生成するのではなく、まず言語モデルを用いてそのクエリに対する架空の理想的な回答（Hypothetical Document）を生成します。その後、生成された架空の文書をベクトル化し、そのベクトルを用いて文書検索を行います。これにより、元のクエリが短くキーワードが不足している場合でも、検索空間内での関連文書とのベクトル類似度を高めることが可能になります。これは`zero-shot`な状況、つまり特定のタスクに対する事前学習なしで高い検索精度を達成する上で効果的です。
* **参考文献**: Gao, L., Ma, X., Lin, J., & Callan, J. (2022). *Precise Zero-Shot Dense Retrieval without Relevance Labels*. arXiv preprint arXiv:2212.10496.
* **URL**: [https://arxiv.org/abs/2212.10496](https://arxiv.org/abs/2212.10496)

### Hybrid Search with RRF (Reciprocal Rank Fusion)

* **技術解説**: 異なる検索システムからのランキング結果を統合するための手法です。本プロジェクトでは、セマンティックな類似性に基づく**ベクトル検索**と、キーワードの一致度に基づく**BM25**という2つの異なる検索結果を統合するために使用されます。各文書に対して、それぞれの検索システムでのランキング（順位）の逆数を算出し、それらを合計したスコアで最終的な順位を決定します。これにより、どちらかの検索システムで高くランク付けされた文書が最終結果の上位に来るようになり、検索の網羅性と頑健性が向上します。
* **参考文献**: <br>
  - 理論: Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). *Reciprocal Rank Fusion for Extreme Scale Search*.  
  - 実践: Microsoft Azure AI Search Documentation. Hybrid search ranking with Reciprocal Rank Fusion.

* **URL**: 
  - [https://dl.acm.org/doi/10.1145/1645953.1646033](https://dl.acm.org/doi/10.1145/1645953.1646033)
  - [https://learn.microsoft.com/ja-jp/azure/search/hybrid-search-ranking](https://learn.microsoft.com/ja-jp/azure/search/hybrid-search-ranking)

### Multi-Query Generation

* **技術解説**: 単一のユーザーの質問を、大規模言語モデル（LLM）を用いて複数の異なる視点を持つサブクエリ群に分解するクエリ拡張手法です。生成された各サブクエリで独立して検索を実行し、得られた結果を統合・重複排除することで、元の質問が多角的であったり曖昧であったりする場合でも、関連文書の見落としを減らし、情報の網羅性を高めることを目的とします。
* **参考文献**: この手法は複数の研究で探求されていますが、概念の基盤となる論文の一つとして以下を挙げます。
    * Wang, J., et al. (2023). *Query Expansion by an Generative Language Model*. arXiv preprint arXiv:2305.09311.
* **URL**: [https://arxiv.org/abs/2305.09311](https://arxiv.org/abs/2305.09311)

### Cross-Encoder Reranking

* **技術解説**: `Retriever`が取得した文書候補群を、より精度の高いモデルで再評価（リランキング）する手法です。一般的なベクトル検索（Bi-Encoder）がクエリと文書を別々にベクトル化するのに対し、Cross-Encoderは**クエリと文書をペアで**モデルに入力し、両者の文脈的な相互作用を直接的に考慮した関連度スコアを算出します。計算コストは高くなりますが、より正確な関連性判断が可能となり、最終的なコンテキストの品質向上に大きく寄与します。
* **参考文献**: Sentence-BERTの論文では、Bi-EncoderとCross-Encoderのアーキテクチャが比較されており、この概念の理解に役立ちます。
    * Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks*. arXiv preprint arXiv:1908.10084.
* **URL**: [https://arxiv.org/abs/1908.10084](https://arxiv.org/abs/1908.10084)

### RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)

* **技術解説**: 文書群から情報の階層構造（ツリー）を自動構築する、先進的なデータベース構築手法です。まず文書を小さなチャンクに分割（葉ノード）し、それらをベクトル空間上でクラスタリングします。次に、各クラスタのチャンク群をLLMで要約し、上位階層のノード（枝ノード）を生成します。このプロセスを再帰的に繰り返し、最終的に文書全体を代表する単一のルートノードを構築します。検索時には、クエリはツリーの全階層のノードと比較されるため、質問の抽象度（具体的か、概観的か）に応じて最適な粒度の情報を取得することが可能になります。
* **参考文献**: Sarthi, P., et al. (2024). *RAPTOR: RECURSIVE ABSTRACTIVE PROCESSING FOR TREE-ORGANIZED RETRIEVAL*. arXiv preprint arXiv:2401.18059.
* **URL**: [https://arxiv.org/abs/2401.18059](https://arxiv.org/abs/2401.18059)

### Self-RAG (Self-Reflective RAG)

* **技術解説**: LLM自身が生成プロセスを能動的に制御・評価するフレームワークです。固定的なパイプラインではなく、LLMが**リフレクショントークン**と呼ばれる特殊なトークンを生成することで、動的に挙動を変化させます。具体的には、(1)検索がそもそも必要か、(2)検索結果は有用か、(3)生成した回答は検索結果に忠実か、といった複数の判断をLLM自身が行います。これにより、不要な検索をスキップしたり、不適切な情報を破棄したりすることで、RAGパイプラインの効率性と信頼性を大幅に向上させます。
* **参考文献**: Asai, A., et al. (2023). *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection*. arXiv preprint arXiv:2310.11511.
* **URL**: [https://arxiv.org/abs/2310.11511](https://arxiv.org/abs/2310.11511)