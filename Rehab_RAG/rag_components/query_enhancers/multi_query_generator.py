import re

class MultiQueryGenerator:
    """
    [手法解説: Multi-Query Generation]
    1つの質問から、LLMを使って複数の異なる視点の質問を自動生成する
    「クエリ拡張」コンポーネント。

    仕組み:
    1. ユーザーの質問を受け取る (例: 「脳卒中のリハビリについて教えて」)
    2. LLMに「この質問を、機能回復、日常生活、社会的復帰の3つの視点から書き換えてください」と依頼。
    3. 生成された複数の質問をリストとして返す。

    期待される効果:
    - ユーザーの漠然とした質問でも、多角的な検索によって関連情報を見つけやすくなる。
    - このコンポーネントはクエリを生成するだけで、実際の検索はRetrieverに任せるため、
      どんなRetrieverとも自由に組み合わせることができる。
    """
    def __init__(self, llm):
        """
        コンストラクタ。
        
        Args:
            llm: LLMインスタンス (質問生成用)。
        """
        self.llm = llm
        print("Multi-Query Generatorが初期化されました。")

    def enhance(self, query: str) -> list[str]:
        """LLMを使って複数の検索クエリを生成し、リストとして返す"""
        prompt = f"""あなたは、ユーザーの質問をより効果的なデータベース検索クエリに変換するアシスタントです。
ユーザーの質問を分析し、異なる3つの視点から、関連情報を検索するための質問を生成してください。
元の質問の意図は変えず、具体的で多様なクエリにしてください。

# 元の質問
{query}

# 生成するクエリ (元の質問も含めて、箇条書きで4つ生成してください)
1. {query}
2. 
3. 
4. 
"""
        response = self.llm.generate(prompt, temperature=0.5)
        
        # LLMの出力から箇条書きの行を抽出
        queries = re.findall(r'^\s*\d+\.\s*(.*)', response, re.MULTILINE)
        
        # もし抽出に失敗したら、元のクエリだけをリストに入れて返す
        if not queries:
            return [query]
            
        # 元のクエリがリストに含まれていることを保証する
        if query not in queries:
            queries.insert(0, query)
            
        print(f"  - 生成された検索クエリ: {queries}")
        return queries