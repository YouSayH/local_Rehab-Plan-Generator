"""
GraphRetriever（GraphCypherQAChain.from_llm を利用する版）

ポイント:
- GraphCypherQAChain.from_llm を使って、内部でスキーマ生成等を任せる（コードが簡潔）。
- 環境変数: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, GEMINI_API_KEY を .env から読み込み。
- 実行時のエラーは print() で出力して把握しやすくしています。
"""

import os
from typing import Any, Dict

from dotenv import load_dotenv

# LangChain / Neo4j ラッパー
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_neo4j import Neo4jGraph
# GraphCypherQAChain を深い階層から取り出す（from_llm を使う）
from langchain_neo4j.chains.graph_qa.cypher import GraphCypherQAChain

# Google Gemini 用のラッパー（あなたの環境で使用しているもの）
from langchain_google_genai import ChatGoogleGenerativeAI


# プロンプト定義

CYPHER_GENERATION_TEMPLATE = """Task:Generate Cypher statement to query a graph database.
Instructions:
Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Schema:
{schema}

Note: Do not include any explanations or apologies in your response.
Do not respond to questions that might ask for anything else than a Cypher statement.
Try to use simple Cypher queries. Do not use UNION, APOC, or overly complex queries.
The question is:
{question}
"""
CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], template=CYPHER_GENERATION_TEMPLATE
)

QA_TEMPLATE = """
You are a rehabilitation expert assistant that answers questions based on provided information.
The user is asking a question about a rehabilitation guideline.
You are given a question and a context. The context is the result of a Cypher query over a knowledge graph.
You must answer the question based on the context.
If the context is empty, just say that you don't have enough information.
Do not use any prior knowledge.

Question:
{question}

Context:
{context}

Helpful Answer:"""
QA_PROMPT = PromptTemplate(input_variables=["context", "question"], template=QA_TEMPLATE)


class GraphRetriever:
    """
    GraphRetriever: Natural language -> Cypher -> Neo4j 検索 -> コンテキスト返却

    実装: GraphCypherQAChain.from_llm を使ってチェインを構築します。
    """

    def __init__(self, path: str, collection_name: str, embedder: Any, **kwargs):
        # .env を読み込む
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        load_dotenv(dotenv_path=env_path)

        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        api_key = os.getenv("GEMINI_API_KEY")

        if not all([uri, user, password, api_key]):
            raise ValueError("環境変数 NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, GEMINI_API_KEY のいずれかが設定されていません。")

        # Neo4j に接続する Graph オブジェクト
        try:
            graph = Neo4jGraph(url=uri, username=user, password=password)
        except Exception as e:
            raise RuntimeError(f"Neo4jGraph の初期化に失敗しました: {e}")

        # LLM (Google Gemini) を初期化
        # モデル名やパラメータは環境に合わせて変更してください
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", google_api_key=api_key, temperature=0.0)

        # cypher 用と QA 用の LLM が同じ場合でも from_llm にそのまま渡せます
        # 必要であれば個別の LLM を用意して差し替えてください。
        cypher_llm = llm
        qa_llm = llm

        # (オプション) ここで LLMChain を用意して別プロンプトを渡すことも可能です。
        # ただし from_llm を使えば内部でチェインを作る場合があるため、簡潔にするため省略。

        # GraphCypherQAChain をファクトリ経由で作成する（簡潔・推奨）
        try:
            # 引数名はライブラリのバージョン差で異なる可能性あり。
            # 代表的なもの: cypher_llm, qa_llm, verbose, exclude_types, include_types, allow_dangerous_requests
            self.cypher_chain = GraphCypherQAChain.from_llm(
                graph=graph,
                cypher_llm=cypher_llm,
                qa_llm=qa_llm,
                verbose=True, # デバッグ情報表示
                return_direct=False,  # 回答を生成
                # 必要に応じて include_types / exclude_types を指定してください
                include_types=None,     # 例: ["Patient", "Guideline"] などで限定したい場合に設定
                exclude_types=[],       # 例: ["InternalLog"]
                allow_dangerous_requests=True,  # 危険なクエリ生成を抑制するオプション
                return_intermediate_steps=True,  # バージョンにより無い場合があるので必要ならコメント解除して試行
                top_k=10
            )
        except TypeError as te:
            # from_llm のシグネチャが違う可能性があるため、詳細なエラーメッセージを表示して分かりやすくする
            raise RuntimeError(f"GraphCypherQAChain.from_llm の呼び出しで TypeError が発生しました: {te}")
        except Exception as e:
            raise RuntimeError(f"GraphCypherQAChain の初期化に失敗しました: {e}")

        print("Graph Retriever が初期化され、Neo4j に接続しました。")

    def retrieve(self, query_text: str, n_results: int = 10) -> Dict[str, Any]:
        """
        自然言語クエリを受け取り、Cypher を生成・実行して結果を返す。
        戻り値は既存の RAG パイプライン互換形式に整形します。
        """
        print(f"  - クエリ '{query_text}' を Cypher に変換して検索中...")

        try:
            # ここは実行 API が環境によって run/invoke/call など異なる場合があるため、
            # invoke をまず試し、なければ run を試す等のフォールバックを用意します。
            try:
                result = self.cypher_chain.invoke({"query": query_text})
                # デバッグ情報
                print(f"DEBUG1: 戻り値の型: {type(result)}")
                print(f"DEBUG2: 戻り値の内容: {result}")
            except AttributeError:
                # invoke がなければ run を試す
                try:
                    result = self.cypher_chain.run({"query": query_text})
                    # デバッグ情報
                    print(f"DEBUG3: 戻り値の型: {type(result)}")
                    print(f"DEBUG4: 戻り値の内容: {result}")
                except Exception:
                    # 最終手段として __call__ を試す
                    result = self.cypher_chain({"query": query_text})
                    # デバッグ情報
                    print(f"DEBUG5: 戻り値の型: {type(result)}")
                    print(f"DEBUG6: 戻り値の内容: {result}")

            # デバッグ: 返り値全体を確認（実行時は必要に応じてコメントアウト）
            print("DEBUG: chain result type:", type(result))
            # print("DEBUG: chain result content:", result)

            # result の構造はバージョンにより異なるため安全に取り出す
            # 例: {'result': '...', 'intermediate_steps': [...] } の場合を想定
            context_str = ""
            if isinstance(result, dict):
                # 中間ステップに context（検索結果）があるか先に探す
                intermediate = result.get("intermediate_steps") or result.get("intermediate_results") or []
                if intermediate:
                    # intermediate の形式はライブラリ差があるので汎用に変換
                    try:
                        # intermediate がリストで最初の要素が dict なら 'context' を取り出す試み
                        first = intermediate[0]
                        if isinstance(first, dict) and "context" in first:
                            context_str = str(first.get("context", ""))
                        else:
                            # あまり厳格にせず、文字列化して返す
                            context_str = str(intermediate)
                    except Exception:
                        context_str = str(intermediate)
                else:
                    # 直接 'result' というキーに最終回答が入るケース
                    if "result" in result:
                        context_str = str(result["result"])
                    elif "answer" in result:
                        context_str = str(result["answer"])
                    else:
                        # 最後の手段: dict 全体を文字列化
                        context_str = str(result)
            else:
                # dict でない戻り値（文字列など）の場合は文字列化
                context_str = str(result)

            # 検索結果が空かどうか判定
            if not context_str or context_str.strip() == "" or context_str.strip() == "[]":
                return {"documents": [[]], "metadatas": [[]]}

            return {
                "documents": [[context_str]],
                "metadatas": [[{"source": "Knowledge Graph"}]],
            }

        except Exception as e:
            print(f"エラー: GraphCypherQAChain の実行中に問題が発生しました: {e}")
            return {"documents": [[]], "metadatas": [[]]}

    def add_documents(self, chunks: list[dict]):
        """
        GraphRetriever は検索専用のため add_documents は noop（GraphBuilder が担当）。
        """
        print("GraphRetriever.add_documents が呼ばれました — このクラスでは処理しません。")
        return
