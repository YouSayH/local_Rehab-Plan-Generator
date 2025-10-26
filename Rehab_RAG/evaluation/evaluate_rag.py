import os
import sys
import pandas as pd
import argparse
from tqdm import tqdm
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
import importlib.util
from dotenv import load_dotenv
import logging
from datetime import datetime
from ragas.run_config import RunConfig
import time

# グローバル変数
# このスクリプト(evaluate_rag.py)は'evaluation'フォルダにあるという前提で、プロジェクトのルートディレクトリを特定します。
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# プロジェクトルートにある.envファイルへの絶対パスを作成し、環境変数を一度だけ読み込みます。
dotenv_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=dotenv_path)

# プロジェクトルートをPythonのモジュール検索パスに追加し、他の自作モジュールをインポートできるようにします。
sys.path.append(PROJECT_ROOT)


def setup_logger(log_dir: str, experiment_name: str, limit: int = None):
    """
    実行情報に基づいたファイル名でロガーを動的に設定する関数。
    これにより、どの実験のログなのかが一目でわかるようになります。
    """
    # --limit引数が指定されていればファイル名に含める
    limit_str = f"_limit-{limit}" if limit is not None else "_all"

    # タイムスタンプと実験情報を含んだログファイル名を生成
    log_filename = f"log_{experiment_name}{limit_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_filepath = os.path.join(log_dir, log_filename)

    # 既存のロガー設定をクリア（再実行時にログが重複しないようにするため）
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # ロガーを新規に設定（ファイルとコンソールの両方に出力）
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filepath, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    return log_filepath


def load_rag_pipeline_from_path(experiment_path: str):
    """
    指定された実験パスからRAGPipelineクラスとload_config関数を動的に読み込む。
    これにより、評価スクリプトはどの実験パイプラインにも対応できます。
    """
    query_rag_path = os.path.join(PROJECT_ROOT, experiment_path, "query_rag.py")
    if not os.path.exists(query_rag_path):
        raise FileNotFoundError(f"`query_rag.py` が見つかりません: {query_rag_path}")
    spec = importlib.util.spec_from_file_location("query_rag", query_rag_path)
    query_rag_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(query_rag_module)
    RAGPipeline = getattr(query_rag_module, "RAGPipeline")
    load_config = getattr(query_rag_module, "load_config")
    return RAGPipeline, load_config


def run_evaluation(experiment_path: str, log_dir: str, limit: int = None):
    """
    指定された実験パスのRAGパイプラインを評価するメインの関数。
    """
    # 1. RAGパイプラインとテストデータセットの読み込み
    try:
        RAGPipeline, load_config = load_rag_pipeline_from_path(experiment_path)
    except (FileNotFoundError, AttributeError) as e:
        logging.error(
            f"エラー: RAGパイプラインの読み込みに失敗しました。パスが正しいか確認してください。"
        )
        logging.error(f"詳細: {e}")
        sys.exit(1)

    logging.info("RAGパイプラインを初期化中...")
    config_path = os.path.join(PROJECT_ROOT, experiment_path, "config.yaml")
    config = load_config(config_path)
    rag_pipeline = RAGPipeline(config)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_dataset_path = os.path.join(script_dir, "test_dataset.jsonl")
    logging.info(f"テストデータセットを '{test_dataset_path}' から読み込み中...")
    test_df = pd.read_json(test_dataset_path, lines=True)

    # limit引数が指定されていれば、データセットを先頭からその件数だけに絞る
    if limit is not None and limit > 0:
        logging.info(f"評価件数を先頭 {limit} 件に制限します。")
        test_df = test_df.head(limit)

    # 2. RAGパイプラインを実行して評価用データを生成
    results = []
    logging.info(
        f"テストデータセットの各質問（計{len(test_df)}件）に対してRAGパイプラインを実行中..."
    )
    for record in tqdm(test_df.to_dict("records"), desc="Generating RAG Answers"):
        query = record["question"]
        rag_output = rag_pipeline.query(query)

        results.append(
            {
                "question": query,
                "answer": rag_output["answer"],
                "contexts": rag_output["contexts"],
                "ground_truth": record["ground_truth"],
            }
        )

    # レート制限のリセットのために待機時間を追加
    logging.info(
        "RAGパイプラインの実行が完了しました。レート制限のリセットのため、60秒間待機します..."
    )
    time.sleep(60)

    # 3. Ragasによる評価の実行
    ragas_dataset = Dataset.from_list(results)

    api_key = os.getenv("GEMINI_API_KEY")

    logging.info("Ragas評価用のLLM (gemini-2.5-flash-lite) を初期化中...")
    ragas_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite", google_api_key=api_key
    )

    logging.info("Ragas評価用のEmbeddingモデル (gemini-embedding-001) を初期化中...")
    ragas_embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        task_type="RETRIEVAL_DOCUMENT",
        google_api_key=api_key,
    )

    # Ragasは内部で多くのAPIコールを並列実行しようとしてレート制限エラーを引き起こします。
    # `RunConfig`を使って、その動作を制御します。
    logging.info("レート制限を回避するため、Ragasの実行設定を調整します。")
    run_config = RunConfig(
        # `max_workers=1` が最も重要。APIコールを同時に複数実行せず、1つずつ順番に行うように強制します。
        # これにより、APIコールの「嵐」が発生するのを防ぎます。
        max_workers=1,
        # タイムアウトを長めに設定し、langchainライブラリの自動リトライが待機する時間を確保します。
        timeout=300,
        max_wait=600,
    )

    logging.info(
        "Ragasによる評価を実行中... (LLMへのAPIコールが発生します。時間がかかります...)"
    )
    # 制御した実行設定(`run_config`)を使って、データセット全体を一度に評価します。
    result_scores = evaluate(
        dataset=ragas_dataset,
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        run_config=run_config,
    )

    # 4. 結果の保存と表示
    logging.info("\n--- 評価結果 ---")
    result_df = result_scores.to_pandas()
    logging.info("\n" + result_df.to_string())

    # 実験名とlimit数を含んだ、より分かりやすいファイル名を生成
    experiment_name = os.path.basename(experiment_path)
    limit_str = f"_limit-{limit}" if limit is not None else "_all"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # CSVの保存先を引数で受け取った log_dir に変更
    results_csv_path = os.path.join(
        log_dir, f"scores_{experiment_name}{limit_str}_{timestamp}.csv"
    )
    result_df.to_csv(results_csv_path, index=False, encoding="utf-8-sig")
    logging.info(f"\n評価スコアを '{results_csv_path}' に保存しました。")

    logging.info("\n--- 平均スコア ---")
    logging.info("\n" + str(result_df.mean(numeric_only=True)))


if __name__ == "__main__":
    # スクリプト実行時に渡される引数を解釈します。
    parser = argparse.ArgumentParser(description="RAGパイプラインを評価するスクリプト")
    parser.add_argument(
        "experiment_path",
        type=str,
        help="評価対象の実験フォルダのパス (例: experiments/your_experiment)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="評価する質問の最大件数を指定します。 (例: --limit 3)",
    )
    args = parser.parse_args()

    # ログと結果を保存するためのディレクトリを定義し、存在しない場合は作成する
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, "logs")
    os.makedirs(
        log_dir, exist_ok=True
    )  # exist_ok=Trueでフォルダが既に存在してもエラーにならない

    # 引数を解釈した「後」でロガーを設定することで、ファイル名に引数の情報を含めることができます。
    experiment_name = os.path.basename(args.experiment_path)
    # setup_loggerに新しいlog_dirを渡す
    log_filepath = setup_logger(log_dir, experiment_name, args.limit)

    # ログに実行開始を記録
    logging.info(f"--- '{args.experiment_path}' の評価を開始します ---")
    logging.info(f"全ログは '{log_filepath}' に保存されます。")

    # .envファイルからAPIキーが読み込めているか最終チェック
    if not os.getenv("GEMINI_API_KEY"):
        logging.error("エラー: 環境変数 `GEMINI_API_KEY` が設定されていません。")
        logging.error(
            f"プロジェクトのルートディレクトリ ({PROJECT_ROOT}) に .env ファイルを作成し、"
        )
        logging.error('`GEMINI_API_KEY="あなたのAPIキー"` と記述してください。')
        sys.exit(1)

    # run_evaluation関数に log_dir を渡す
    run_evaluation(args.experiment_path, log_dir, args.limit)
