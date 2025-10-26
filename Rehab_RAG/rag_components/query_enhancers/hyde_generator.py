class HydeQueryEnhancer:
    """
    [手法解説: HyDE (Hypothetical Document Embeddings)]
    ユーザーからの短い、あるいは曖昧な質問を、より検索に適した具体的な文章に変換するコンポーネントです。

    仕組み:
    1. ユーザーの質問を受け取る (例: 「脳卒中のリハビリは？」)
    2. LLMに「この質問に対する完璧な回答を想像して書いてください」とお願いする。
    3. LLMが架空の回答を生成する (例: 「脳卒中のリハビリテーションでは、急性期から...」)
    4. この生成された文章を、次の検索ステップの入力として使用する。

    期待される効果:
    - 短いクエリよりも多くの検索キーワードや文脈が含まれるため、検索精度が向上する。
    - ユーザーが思いつかない専門用語などをLLMが補ってくれる。
    """

    def __init__(self, llm):
        """
        コンストラクタ。文章生成のためのLLMインスタンスを受け取ります。

        Args:
            llm: GeminiLLMなど、`generate`メソッドを持つLLMラッパークラスのインスタンス。
        """
        self.llm = llm

    def enhance(self, query: str) -> str:
        """
        与えられたクエリから架空の理想的な回答を生成する (HyDE)。

        Args:
            query (str): ユーザーからの元の質問文。

        Returns:
            str: LLMによって生成された、検索用の架空の回答文。
        """
        prompt = f"""以下の質問に対して、あなたが完璧な知識を持つ専門家であると仮定して、理想的な回答を生成してください。
この回答は検索の精度を高めるために使います。質問の意図を汲み取った具体的で詳細な文章にしてください。

質問: {query}

理想的な回答:"""

        hypothetical_answer = self.llm.generate(prompt, max_output_tokens=512)

        # LLMがエラーを返したり、空の文字列を生成した場合は、元のクエリをそのまま使う
        if (
            "回答を生成できませんでした" in hypothetical_answer
            or not hypothetical_answer.strip()
        ):
            print("HyDEの生成に失敗したため、元のクエリを検索に使用します。")
            return query

        return hypothetical_answer
