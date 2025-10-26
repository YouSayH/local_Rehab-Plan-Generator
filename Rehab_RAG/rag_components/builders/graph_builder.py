import os
import importlib
import time
from neo4j import GraphDatabase
from tqdm import tqdm
from dotenv import load_dotenv
from typing import List, Optional
from pydantic import BaseModel, Field
import enum

# ガイドラインの構造に特化したEnumとPydanticモデルを定義

class NodeType(str, enum.Enum):
    """グラフのノードタイプを厳密に定義するEnum"""
    DISEASE = "疾患"
    CONDITION = "状態"
    TREATMENT = "治療法"
    RECOMMENDATION = "推奨"
    EVIDENCE = "エビデンス"
    FEATURE = "臨床的特徴"

class RelationshipType(str, enum.Enum):
    """グラフの関係タイプを厳密に定義するEnum"""
    HAS_CONDITION = "HAS_CONDITION"
    HAS_TREATMENT = "HAS_TREATMENT"
    HAS_RECOMMENDATION = "HAS_RECOMMENDATION"
    HAS_EVIDENCE = "HAS_EVIDENCE"
    HAS_FEATURE = "HAS_FEATURE"
    RELATED_TO = "RELATED_TO"

class Node(BaseModel):
    id: str = Field(description="テキスト内のエンティティ名")
    label: NodeType = Field(description="エンティティのカテゴリ")

class Relationship(BaseModel):
    source: str = Field(description="関係の始点となるノードのid")
    target: str = Field(description="関係の終点となるノードのid")
    type: RelationshipType = Field(description="関係の種類")

class KnowledgeGraph(BaseModel):
    nodes: Optional[List[Node]] = Field(description="抽出されたエンティティのリスト", default_factory=list)
    relationships: Optional[List[Relationship]] = Field(description="抽出された関係性のリスト", default_factory=list)


class GraphBuilder:
    def __init__(self, config: dict, db_path: str, **kwargs):
        self.config = config
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        
        if not all([uri, user, password]):
            raise ValueError("環境変数 NEO4J_URI, NEO4J_USERNAME, NEOJ_PASSWORD が設定されていません。")

        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.llm = self._get_instance('llm')

    def _get_instance(self, component_type: str):
        cfg = self.config['build_components'][component_type]
        module = importlib.import_module(cfg['module'])
        class_ = getattr(module, cfg['class'])
        return class_(**cfg.get('params', {}))

    def _extract_graph_from_chunk(self, chunk_text: str) -> Optional[KnowledgeGraph]:
        # 新しいグラフ構造に従うよう、プロンプトを刷新
        prompt = f"""あなたは理学療法の臨床ガイドラインを解析し、ナレッジグラフを構築する専門家です。
以下のテキストから、定義されたカテゴリ（ラベル）と関係（タイプ）のみを使用して、エンティティとそれらの関係を抽出してください。

# 抽出ルール
- **疾患 (Disease)**: ガイドラインの中心となる病名（例: "変形性股関節症", "肩関節周囲炎"）。
- **状態 (Condition)**: 疾患の特定の段階、症状、分類（例: "炎症期", "K-L分類3"）。
- **治療法 (Treatment)**: 具体的な理学療法や介入（例: "運動療法", "理学療法と生活指導の併用"）。
- **推奨 (Recommendation)**: ガイドラインの結論（例: "条件付き推奨", "ステートメント"）。
- **臨床的特徴 (Feature)**: 疫学や病態など、疾患に関する事実情報。

# 関係性のルール
- 疾患とその状態をつなぐ: `HAS_CONDITION`
- 疾患や状態とその治療法をつなぐ: `HAS_TREATMENT`
- 治療法とその推奨度をつなぐ: `HAS_RECOMMENDATION`

# テキスト
"{chunk_text}"
"""
        try:
            response = self.llm.client.models.generate_content(
                model=self.llm.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": KnowledgeGraph,
                },
            )
            return response.parsed
        except Exception as e:
            print(f"警告: グラフ抽出中にエラーが発生しました。スキップします。エラー: {e}")
            return None

    def _write_to_neo4j(self, graph_data: KnowledgeGraph, chunk_text: str):
        if not graph_data or not graph_data.nodes:
            return

        with self.driver.session() as session:
            for node in graph_data.nodes:
                # Enumの値（例: NodeType.DISEASE）を文字列（"疾患"）に変換して使用
                session.run("MERGE (n:`{label}` {{id: $id}})".format(label=node.label.value), id=node.id)

            if graph_data.relationships:
                for rel in graph_data.relationships:
                    # Enumの値を文字列（"HAS_CONDITION"など）に変換して使用
                    session.run(
                        """
                        MATCH (a {{id: $source}}), (b {{id: $target}})
                        MERGE (a)-[r:`{type}`]->(b)
                        SET r.context = $context
                        """.format(type=rel.type.value),
                        source=rel.source, target=rel.target, context=chunk_text
                    )

    def build(self):
        with self.driver.session() as session:
            print("既存のグラフデータを削除しています...")
            session.run("MATCH (n) DETACH DELETE n")
        chunker = self._get_instance('chunker')
        config_file_path = self.config['builder']['params']['config_path']
        config_dir = os.path.dirname(config_file_path)
        source_path = os.path.abspath(os.path.join(config_dir, self.config['source_documents_path']))
        all_chunks = []
        for filename in sorted(os.listdir(source_path)):
            if filename.endswith(".md"):
                file_path = os.path.join(source_path, filename)
                chunks = chunker.chunk(file_path)
                all_chunks.extend(chunks)
        print(f"合計 {len(all_chunks)} 個のチャンクからナレッジグラフを構築します...")
        for chunk in tqdm(all_chunks, desc="Building Knowledge Graph"):
            time.sleep(1) 
            graph_data = self._extract_graph_from_chunk(chunk['text'])
            if graph_data:
                self._write_to_neo4j(graph_data, chunk['text'])
        print("ナレッジグラフの構築が完了しました。")
        self.driver.close()