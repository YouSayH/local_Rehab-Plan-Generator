"""
RAPTORBuilder: 階層的な情報ツリーを構築する先進的なBuilder
"""
import os
import importlib
import numpy as np
from sklearn.cluster import DBSCAN
from tqdm import tqdm
import hashlib
import time

class RAPTORBuilder:
    """
    [Builder解説: RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval)]
    これは、文書から情報の「ツリー構造」を自動的に構築する、非常に高度なデータベース構築手法です。
    木の葉のような細かい情報から、枝、幹といった全体を要約した情報まで、
    AIが様々な粒度で知識を整理することを可能にします。

    [処理の流れを木に例えると...]
    1. レベル0 (木の葉): 最初に、元となる文書をたくさんの小さなチャンク（＝木の葉）に分割します。
       これは、最も詳細な情報単位です。

    2. レベル1 (小枝): 全ての「葉」をAIに見せて、意味が似ているものをグループ分け（クラスタリング）させます。
       そして、各グループの内容をLLMで要約して、新しいチャンク（＝小枝）を作ります。
       この「小枝」は、「葉」よりも少し抽象的な情報を持っています。

    3. レベル2 (中枝): 次に、出来上がった「小枝」たちを同じようにグループ分けし、要約して「中枝」を作ります。
       これを繰り返していきます。

    4. 再帰的な処理: この「グループ分け→要約」のプロセスを、最終的に全体をまとめた1つのチャンク（＝幹）
       になるまで繰り返します。

    5. データベース化: 最後に、このツリーを構成する全てのチャンク（葉、小枝、中枝、幹...）を
       一つのデータベースに保存します。

    [期待される効果]
    ユーザーが「大腿骨近位部骨折のリハビリは？」のような広い質問をしたときは「幹」や「太い枝」が、
    「術後3日目の等尺性運動の注意点は？」のような具体的な質問をしたときは「葉」がヒットしやすくなります。
    これにより、質問の抽象度に応じた最適な情報をAIに提供できるようになり、回答の質が劇的に向上する
    可能性があります。
    """
    def __init__(self, config: dict, db_path: str, **kwargs):
        self.config = config
        self.db_path = db_path
        self.params = config['builder'].get('params', {})

    def _get_instance(self, component_type: str, params_override={}):
        """設定に応じてコンポーネントのインスタンスを生成する内部ヘルパー"""
        cfg = self.config['build_components'][component_type]
        params = {**cfg.get('params', {}), **params_override}
        module = importlib.import_module(cfg['module'])
        class_ = getattr(module, cfg['class'])
        return class_(**params)

    def _generate_summary(self, context_texts: list, llm) -> str:
        """LLMを使ってクラスタの要約を生成する"""
        if not context_texts:
            return ""
            
        context_str = "\n\n---\n\n".join(context_texts)
        prompt = f"""以下の複数のテキストチャンクが与えられています。
これらのテキストに共通する主要なテーマや情報を抽出し、簡潔に要約してください。要約は、元のテキスト群の重要な情報を網羅しつつ、一つの独立した段落として成立するように記述してください。

# 与えられたテキストチャンク群
{context_str}

# 要約:"""
        time.sleep(1) # APIレート制限対策
        summary = llm.generate(prompt, max_output_tokens=1024)
        return summary.strip()

    def build(self):
        # 1. RAPTORに必要なコンポーネントを準備
        print("RAPTOR Builderのコンポーネントを初期化中...")
        chunker = self._get_instance('chunker')
        embedder = self._get_instance('embedder')
        llm = self._get_instance('llm', params_override={'safety_block_none': True})
        
        retriever_module = importlib.import_module('rag_components.retrievers.chromadb_retriever')
        RetrieverClass = getattr(retriever_module, 'ChromaDBRetriever')
        retriever = RetrieverClass(
            path=self.db_path,
            collection_name=self.config['database']['collection_name'],
            embedder=embedder
        )

        # 2. 初期チャンク（レベル0、木の葉）を生成
        # config.yamlからの相対パスを正しく解決する
        config_dir = os.path.dirname(self.db_path)
        source_path = os.path.abspath(os.path.join(config_dir, self.config['source_documents_path']))
        
        print(f"'{source_path}' からドキュメントを読み込み、レベル0のチャンク（葉）を生成中...")
        base_chunks = []
        for filename in os.listdir(source_path):
            if filename.endswith(".md"):
                file_path = os.path.join(source_path, filename)
                chunks = chunker.chunk(file_path)
                for chunk in chunks:
                    chunk['metadata']['level'] = 0
                base_chunks.extend(chunks)
        
        all_levels_chunks = list(base_chunks)
        current_level_texts = [chunk['text'] for chunk in base_chunks]

        # 3. 再帰的にクラスタリングと要約を実行
        level = 0
        max_levels = self.params.get('max_levels', 3)
        while len(current_level_texts) > 1 and level < max_levels:
            print(f"\n--- RAPTOR レベル {level} -> {level+1} を構築中 ---")
            print(f"現在のチャンク数: {len(current_level_texts)}")

            print("  - ベクトル化中...")
            embeddings = np.array(embedder.embed_documents(current_level_texts))
            
            print("  - クラスタリング中...")
            clustering = DBSCAN(
                eps=self.params.get('clustering_eps', 0.5), 
                min_samples=self.params.get('min_samples', 2), 
                metric='cosine'
            ).fit(embeddings)
            labels = clustering.labels_
            
            unique_labels, counts = np.unique(labels, return_counts=True)
            print(f"  - {len(unique_labels[unique_labels != -1])}個のクラスタを発見しました。(ノイズ除く)")

            print("  - LLMで要約チャンクを生成中...")
            next_level_texts = []
            
            for label in tqdm(unique_labels, desc=f"レベル{level+1}の要約を生成"):
                if label == -1:
                    continue
                
                cluster_indices = np.where(labels == label)[0]
                cluster_texts = [current_level_texts[i] for i in cluster_indices]
                
                if len(cluster_texts) < self.params.get('min_samples', 2):
                    continue

                summary = self._generate_summary(cluster_texts, llm)
                
                if summary and summary not in cluster_texts:
                    next_level_texts.append(summary)
                    summary_id = hashlib.sha256(summary.encode()).hexdigest()
                    all_levels_chunks.append({
                        "id": summary_id,
                        "text": summary,
                        "metadata": {"source": "RAPTOR Summary", "level": level + 1, "cluster_id": f"{level+1}-{label}"}
                    })

            if not next_level_texts or len(next_level_texts) >= len(current_level_texts):
                print(f"レベル{level+1}でチャンク数が減少しなかったため、ツリーの構築を終了します。")
                break

            current_level_texts = next_level_texts
            level += 1

        # 4. 全ての階層のチャンクをデータベースに追加
        print(f"\n--- 全階層（レベル0〜{level}）のチャンクをDBに格納します ---")
        print(f"合計チャンク数: {len(all_levels_chunks)}")
        retriever.add_documents(all_levels_chunks)
        
        print("\n構築後の情報を表示します:")
        print(f"  - 格納されたアイテム数: {retriever.count()}")