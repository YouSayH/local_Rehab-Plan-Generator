from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class NLIFilter:
    """
    [手法解説: NLI (Natural Language Inference) Filtering]
    検索結果として得られた文書が、本当にユーザーの質問と関連があるか、あるいは矛盾していないかを
    判定するための高度なフィルタリングコンポーネントです。

    仕組み:
    1. NLIモデルは、2つの文（前提、仮説）を受け取り、その関係を判定する。
       - premise (前提): 検索された文書チャンク
       - hypothesis (仮説): ユーザーの元の質問文
    2. モデルは3つのラベルの確率を出力する。
       - Entailment (含意): 前提は仮説を支持する。 (例: 「彼は独身だ」→「彼は結婚していない」) -> 採用
       - Contradiction (矛盾): 前提は仮説と矛盾する。 (例: 「彼は独身だ」→「彼は既婚だ」) -> 破棄
       - Neutral (中立): どちらでもない。 -> 採用

    期待される効果:
    - ベクトル検索だけでは除去しきれない、文脈的に無関係・不適切な情報を弾き、ノイズを減らす。
    - LLMに渡す情報の品質を高め、最終的な回答の信頼性を向上させる。
    """
    def __init__(self, model_name: str, device: str = "auto", **kwargs):
        """
        コンストラクタ。指定されたNLIモデルをHugging Faceからロードします。
        
        Args:
            model_name (str): Hugging Face上のNLIモデル名。
            device (str): "cuda", "cpu", "auto"。
        """
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"NLIモデル ({model_name}) を {self.device} にロード中...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name).to(self.device)
        print("NLIモデルのロード完了。")

    def filter(self, query: str, documents: list[str], metadatas: list[dict]) -> tuple[list[str], list[dict]]:
        """
        NLIモデルを使用して、クエリと矛盾するドキュメントを除外する。
        
        Args:
            query (str): ユーザーの元の質問文 (仮説として使用)。
            documents (list[str]): 検索された文書チャンクのリスト (前提として使用)。
            metadatas (list[dict]): 各文書チャンクに対応するメタデータのリスト。

        Returns:
            tuple[list[str], list[dict]]: フィルタリング後の文書とメタデータのタプル。
        """
        filtered_docs = []
        filtered_metadatas = []
        
        for doc, meta in zip(documents, metadatas):
            premise = doc
            hypothesis = query

            # モデルに入力するためにテキストをトークン化
            input_data = self.tokenizer(premise, hypothesis, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            with torch.no_grad(): # 推論モードで勾配計算をオフにし、高速化
                outputs = self.model(**input_data)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=1).cpu().numpy()[0]
            
            # モデルの出力から各ラベルの確率を取得
            # モデル設定によると、0: contradiction, 1: neutral, 2: entailment
            contradiction_score = probabilities[0] # model.config.label2id['contradiction'] is 0
            entailment_score = probabilities[2]  # model.config.label2id['entailment'] is 2

            # フィルタリングのロジック: 矛盾スコアが低く(0.5未満)、かつ含意または中立スコアがある程度高いものを採用
            # このしきい値は調整可能
            # 矛盾スコアが低く、含意または中立スコアがある程度あるものを採用
            if contradiction_score < 0.5 and (entailment_score > 0.1 or probabilities[1] > 0.1): 
                filtered_docs.append(doc)
                filtered_metadatas.append(meta)
        
        return filtered_docs, filtered_metadatas