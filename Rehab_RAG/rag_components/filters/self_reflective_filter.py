"""
SelfReflectiveFilter: 検索結果の関連性を自己評価・フィルタリングするコンポーネント
"""
from tqdm import tqdm
import time

class SelfReflectiveFilter:
    """
    [Filter解説: SelfReflectiveFilter (自己反省フィルタ)]
    これは、Self-RAGのもう一つの重要な要素で、データベースから検索してきた情報が
    「本当にユーザーの質問に答える上で役に立つか？」をLLM自身が一つ一つ吟味し、
    不要な情報をふるい落とすフィルタです。

    [フィルタリングの仕組み]
    1. Retrieverが検索してきた文書のリストを受け取ります。
    2. 各文書について、LLMに「この文書は、元の質問に答えるための適切な根拠になりますか？」と尋ねます。
    3. LLMは、文書と質問の関係を分析し、以下のいずれかの「評価トークン」を返します。
       - [RELEVANT]: 関連性が高く、回答の根拠として適切。
       - [IRRELEVANT]: 関連性が低い、またはノイズ。
    4. [RELEVANT]と評価された文書だけを残し、[IRRELEVANT]と評価された文書は捨てます。

    [期待される効果]
    - ベクトル検索だけでは排除しきれない、文脈的に微妙にずれた情報を正確に除去します。
    - 最終的な回答を生成するLLMに、本当に質の高い情報だけを提供することで、
      回答の精度と信頼性を大幅に向上させます。
    - ハルシネーション（AIがもっともらしい嘘をつく現象）のリスクを低減します。
    """
    def __init__(self, llm):
        self.llm = llm
        print("Self-Reflective Filterが初期化されました。")

    def filter(self, query: str, documents: list[str], metadatas: list[dict]) -> tuple[list[str], list[dict]]:
        """
        LLMを使って、クエリと関連性の低いドキュメントを除外します。
        """
        filtered_docs = []
        filtered_metadatas = []
        
        print(f"  - {len(documents)}件の文書を自己評価フィルタリング中...")
        for doc, meta in tqdm(zip(documents, metadatas), total=len(documents), desc="Self-Reflecting"):
            prompt = f"""あなたは、与えられた文書がユーザーの質問に答える上で関連性があるか評価する専門家です。
以下の「質問」と「文書」を比較し、文書が質問に対する直接的な答えや有用な根拠を含む場合は [RELEVANT]、
そうでない場合は [IRRELEVANT] とだけ答えてください。

# 質問
"{query}"

# 文書
"{doc}"

# あなたの評価:"""
            
            time.sleep(10) # APIレート制限対策
            response = self.llm.generate(prompt, temperature=0.0, max_output_tokens=10)
            
            if "[RELEVANT]" in response:
                filtered_docs.append(doc)
                filtered_metadatas.append(meta)
        
        return filtered_docs, filtered_metadatas