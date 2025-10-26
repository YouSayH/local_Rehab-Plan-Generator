"""
RAGデータベース構築スクリプト (The Commander / 司令塔)

[このスクリプトの役割]
このスクリプトは、RAGパイプラインの「事前準備」フェーズの司令塔です。
現在の役割はただ一つ、`config.yaml` で指定された「Builder」コンポーネントを
呼び出し、データベースの構築を完全に任せることです。

[後方互換性]
このスクリプトは、古いconfig.yamlファイルにも対応しています。
- `config.yaml`に`builder:`セクションがあれば、指定されたBuilderを使います (例: RAPTORBuilder)。
- `config.yaml`に`builder:`セクションがなければ、自動的に従来のシンプルな構築方法を
  実行する`DefaultBuilder`が呼び出されます。

これにより、全ての実験でこのファイルを共通して使用できます。
"""

import yaml
import importlib
import os
import shutil
import sys

# プロジェクトのルートディレクトリをPythonのパスに追加
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..")))


def load_config(config_path="config.yaml"):
    """YAML設定ファイルを読み込む"""
    full_path = os.path.join(SCRIPT_DIR, config_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_instance(module_name, class_name, params={}):
    """モジュールとクラス名からインスタンスを動的に生成するヘルパー関数"""
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    return class_(**params)


def main():
    config = load_config()

    # 構築を始める前に、古いデータベースがあれば削除する
    db_path = config["database"]["path"]
    full_db_path = os.path.join(SCRIPT_DIR, db_path)
    if os.path.exists(full_db_path):
        print(f"既存のデータベース '{full_db_path}' を削除します。")
        shutil.rmtree(full_db_path)

    print("--- データベース構築開始 ---")

    # config.yamlに'builder'セクションがあるかチェック
    if "builder" in config:
        # あれば、指定されたBuilderを読み込む (RAPTORなど新しい手法用)
        builder_cfg = config["builder"]
        print(f"Builder '{builder_cfg['class']}' を使用してDBを構築します...")
    else:
        # なければ、自動的にDefaultBuilderを指定する (古い設定ファイル用)
        print("config.yamlに'builder'の指定がないため、DefaultBuilderを使用します。")
        builder_cfg = {
            "module": "rag_components.builders.default_builder",
            "class": "DefaultBuilder",
        }

    # Builderが必要とする情報（設定全体、DBの保存場所など）を準備する
    builder_params = builder_cfg.get("params", {})
    builder_params["config"] = config
    builder_params["db_path"] = full_db_path

    # 指定されたBuilderのインスタンスを動的に生成する
    builder = get_instance(
        module_name=builder_cfg["module"],
        class_name=builder_cfg["class"],
        params=builder_params,
    )

    # Builderに構築の実行を命令する
    builder.build()

    print("\n--- データベース構築完了 ---")
    print(f"データベースのパス: {os.path.abspath(full_db_path)}")
    print(f"コレクション名: {config['database']['collection_name']}")


if __name__ == "__main__":
    main()
