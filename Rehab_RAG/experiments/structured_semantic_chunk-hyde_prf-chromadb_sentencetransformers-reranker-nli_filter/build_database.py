"""
RAGデータベース構築スクリプト (The Builder)

[このスクリプトの役割]
このスクリプトは、RAGパイプラインの「事前準備」フェーズを担当します。
`config.yaml` ファイルで定義された設定に基づき、以下の処理を自動的に行います。

1. 設定ファイル(`config.yaml`)を読み込む。
2. 指定されたチャンカー(Chunker)とエンベッダー(Embedder)を動的にロードする。
3. `source_documents` フォルダから知識源となるMarkdownファイルを読み込む。
4. チャンカーを使って、各ファイルを意味のあるチャンク(塊)に分割する。
5. エンベッダーを使って、各チャンクをベクトル化する。
6. ベクトル化されたチャンクを、メタデータと共にベクトルデータベース(ChromaDB)に保存する。

[実行方法]
プロジェクトのルートディレクトリから、以下のコマンドで実行します。
`python .\\experiments\\<実験名>\\build_database.py`
"""

import yaml
import importlib
import os
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..")))


def load_config(config_path="config.yaml"):
    """YAML設定ファイルを読み込む"""
    full_path = os.path.join(SCRIPT_DIR, config_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_instance(module_name, class_name, params={}):
    """モジュールとクラス名からインスタンスを動的に生成する"""
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    return class_(**params)


def main():
    config = load_config()

    # 既存DBを削除
    db_path = config["database"]["path"]
    full_db_path = os.path.join(SCRIPT_DIR, db_path)
    if os.path.exists(full_db_path):
        print(f"既存のデータベース '{full_db_path}' を削除します。")
        shutil.rmtree(full_db_path)

    print("--- データベース構築開始 ---")

    # コンポーネントのインスタンス化
    build_cfg = config["build_components"]

    chunker_cfg = build_cfg["chunker"]
    chunker = get_instance(
        module_name=chunker_cfg["module"],
        class_name=chunker_cfg["class"],
        params=chunker_cfg.get("params", {}),  # paramsがない場合も考慮
    )

    embedder_cfg = build_cfg["embedder"]
    embedder = get_instance(
        module_name=embedder_cfg["module"],
        class_name=embedder_cfg["class"],
        params=embedder_cfg.get("params", {}),
    )
    # ------------------

    # ChromaDBRetrieverにはembedderインスタンスが必要
    retriever_params = {
        "path": full_db_path,  # <--- 修正箇所 full_db_pathを使用
        "collection_name": config["database"]["collection_name"],
        "embedder": embedder,
    }
    retriever = get_instance(
        "rag_components.retrievers.chromadb_retriever",
        "ChromaDBRetriever",
        retriever_params,
    )

    # ドキュメントの読み込みとチャンキング
    all_chunks = []
    source_path = os.path.join(SCRIPT_DIR, config["source_documents_path"])
    print(f"'{source_path}' からドキュメントを読み込みます...")
    # ------------------
    for filename in os.listdir(source_path):
        if filename.endswith(".md"):
            file_path = os.path.join(source_path, filename)
            print(f"\nファイル '{filename}' を処理中...")
            chunks = chunker.chunk(file_path)
            all_chunks.extend(chunks)
            print(f"-> {len(chunks)} 個のチャンクを抽出しました。")

    if not all_chunks:
        print(
            f"警告: '{source_path}' 内に処理対象のMarkdownファイルが見つかりませんでした。"
        )
        return

    # データベースへの追加
    print(f"\n合計 {len(all_chunks)} 個のチャンクをデータベースに格納します。")
    retriever.add_documents(all_chunks)

    print("\n--- データベース構築完了 ---")
    print(f"データベースのパス: {os.path.abspath(full_db_path)}")
    print(f"コレクション名: {config['database']['collection_name']}")
    print(f"格納されたアイテム数: {retriever.count()}")


if __name__ == "__main__":
    main()
