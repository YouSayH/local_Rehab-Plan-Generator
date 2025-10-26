"""
RetrievalJudge: 検索を実行すべきか判断するコンポーネント
"""

import re


class RetrievalJudge:
    """
    [Judge解説: RetrievalJudge (検索判断役)]
    これは、Self-RAGの心臓部の一つで、ユーザーの質問を受け取った際に、
    「そもそもデータベースに情報を探しに行く必要があるか？」を判断するAIエージェントです。

    [判断の仕組み]
    1. ユーザーの質問を受け取ります (例: 「こんにちは」, 「変形性股関節症について教えて」)
    2. LLMに対し、「この質問に答えるには、専門知識データベースの検索が必要ですか？」と尋ねます。
    3. LLMは、質問の内容を分析し、以下のいずれかの「判断トークン」を返します。
       - [RETRIEVAL_NEEDED]: 専門的な知識が必要な質問。 (例: 「変形性股関節症〜」)
       - [NO_RETRIEVAL]: 挨拶や一般的な会話、自己完結した質問。 (例: 「こんにちは」)

    [期待される効果]
    - 不要なデータベース検索をスキップすることで、応答速度を向上させ、コストを削減します。
    - AIが状況に応じて最適な行動（検索するか、直接答えるか）を選択する、より自律的なシステムを実現します。
    """

    def __init__(self, llm):
        self.llm = llm
        print("Retrieval Judgeが初期化されました。")

    def judge(self, query: str) -> str:
        """
        与えられたクエリに対して、検索が必要かどうかを判断します。

        Args:
            query (str): ユーザーの質問文。

        Returns:
            str: "RETRIEVAL_NEEDED" または "NO_RETRIEVAL" のいずれかの判断結果。
        """
        prompt = f"""あなたは、ユーザーからの質問が専門知識データベースでの検索を必要とするか判断する分類器です。
以下の質問を分析し、回答するために検索が必要な場合は [RETRIEVAL_NEEDED]、一般的な知識や会話で回答できる場合は [NO_RETRIEVAL] とだけ答えてください。

質問: "{query}"

あなたの判断:"""

        response = self.llm.generate(prompt, temperature=0.0, max_output_tokens=10)

        # LLMの回答から判断トークンを抽出
        if "[RETRIEVAL_NEEDED]" in response:
            print("  - Judgeの判断: 検索が必要 (RETRIEVAL_NEEDED)")
            return "RETRIEVAL_NEEDED"
        else:
            print("  - Judgeの判断: 検索は不要 (NO_RETRIEVAL)")
            return "NO_RETRIEVAL"
