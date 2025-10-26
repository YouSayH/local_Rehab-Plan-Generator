"""
DefaultBuilder: 従来のシンプルなDB構築プロセスをコンポーネント化したもの
"""

import os
import importlib


class DefaultBuilder:
    """
    [Builder解説: DefaultBuilder]
    これは、最も基本的なデータベース構築プロセスを実行するコンポーネントです。
    RAPTORのような高度な手法を使わず、シンプルなパイプラインを試す際に使用します。
    過去の実験設定との後方互換性を保つ役割も担っています。

    [処理の流れ]
    1. Chunker: Markdownファイルを意味のある塊（チャンク）に分割します。
    2. Embedder: 各チャンクを、AIが意味を理解できる数値のベクトルに変換します。
    3. Retriever: ベクトル化されたチャンクをデータベースに保存します。
    """

    def __init__(self, config: dict, db_path: str, **kwargs):
        self.config = config
        self.db_path = db_path
        self.retriever = None

    def _get_instance(self, module_name, class_name, params={}):
        """設定に応じてコンポーネントのインスタンスを生成する内部ヘルパー"""
        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        return class_(**params)

    def build(self):
        """データベース構築のメイン処理"""
        # 1. 必要なコンポーネントを準備
        build_cfg = self.config["build_components"]

        chunker_cfg = build_cfg["chunker"]
        chunker = self._get_instance(
            module_name=chunker_cfg["module"],
            class_name=chunker_cfg["class"],
            params=chunker_cfg.get("params", {}),
        )

        embedder_cfg = build_cfg["embedder"]
        embedder = self._get_instance(
            module_name=embedder_cfg["module"],
            class_name=embedder_cfg["class"],
            params=embedder_cfg.get("params", {}),
        )

        retriever_cfg = build_cfg.get("retriever")
        retriever_params = {
            "path": self.db_path,
            "collection_name": self.config["database"]["collection_name"],
            "embedder": embedder,
            **(retriever_cfg.get("params", {}) if retriever_cfg else {}),
        }
        if retriever_cfg:
            self.retriever = self._get_instance(
                retriever_cfg["module"], retriever_cfg["class"], retriever_params
            )
        else:  # 古いconfigファイルのための後方互換処理
            self.retriever = self._get_instance(
                "rag_components.retrievers.chromadb_retriever",
                "ChromaDBRetriever",
                retriever_params,
            )

        # 2. ドキュメントを読み込み、チャンクに分割
        # config.yamlからの相対パスを正しく解決する
        config_dir = os.path.dirname(self.db_path)
        source_path = os.path.abspath(
            os.path.join(config_dir, self.config["source_documents_path"])
        )

        print(f"'{source_path}' からドキュメントを読み込みます...")
        all_chunks = []
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

        # 3. 全てのチャンクをデータベースに追加
        print(f"\n合計 {len(all_chunks)} 個のチャンクをデータベースに格納します。")
        self.retriever.add_documents(all_chunks)

        print("\n構築後の情報を表示します:")
        if hasattr(self.retriever, "vector_retriever") and hasattr(
            self.retriever.vector_retriever, "count"
        ):
            print(
                f"  - 格納されたアイテム数: {self.retriever.vector_retriever.count()}"
            )
        elif hasattr(self.retriever, "count"):
            print(f"  - 格納されたアイテム数: {self.retriever.count()}")
