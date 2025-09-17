import os
import re
import hashlib

class StructuredMarkdownChunker:
    """
    [手法解説: 構造化チャンキング]
    RAGの性能は「いかにして文書を意味のある単位に分割するか」に大きく依存します。
    このチャンカーは、単純な文字数や段落で区切るのではなく、Markdownの文書構造（見出しレベル）を
    利用してチャンキングを行います。

    目的:
    - 関連性の低い情報が同じチャンクに混ざるのを防ぐ (例: ある疾患の章と別の疾患の章が混ざらないようにする)。
    - 見出し情報をメタデータとして付与し、検索結果の文脈理解を助ける。
    - 結果として、検索精度(リコールとプレシジョン)の向上を目指します。
    """
    def __init__(self):
        pass

    def chunk(self, file_path: str) -> list[dict]:
        """
        Markdownファイルを解析し、構造に基づいたチャンクとメタデータのリストを生成する。
        これがこのクラスのメインの実行メソッドです。
        
        Args:
            file_path (str): 処理対象のMarkdownファイルのパス。

        Returns:
            list[dict]: チャンク情報の辞書(`id`, `text`, `metadata`)のリスト。
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = []

        # 章タイトル(# H1)を抽出し、メタデータとして利用する
        chapter_match = re.search(r'^#\s*(.*?)\n', content)
        chapter_title = chapter_match.group(1).strip() if chapter_match else "不明な章"

        # H2見出し(##)を「疾患」の区切りとみなし、文書を大きなセクションに分割。
        # これにより、「大腿骨近位部骨折」と「変形性股関節症」の情報が混ざるのを防ぎ、文脈を維持します。

        sections = re.split(r'\n(##\s)', content)
        
        # 最初のセクション（H2見出しより前）の処理
        current_content = sections[0]
        current_disease = "疾患総論" # H2がない場合は総論として扱う
        chunk_counter = 0

        chunk_counter = self._process_section(chunks, current_content, file_path, chapter_title, current_disease, chunk_counter)

        # H2見出し以降のセクションをループ処理
        for i in range(1, len(sections), 2):
            # `re.split`の仕様上、区切り文字(##)とそれに続くコンテンツが交互にリストに入るため、2つずつ結合する

            current_content = sections[i] + sections[i+1]
            
            disease_match = re.search(r'##\s*(.*?)\n', current_content)
            if disease_match:
                current_disease = disease_match.group(1).strip()
            
            chunk_counter = self._process_section(chunks, current_content, file_path, chapter_title, current_disease, chunk_counter)
            
        return chunks

    def _process_section(self, chunks_list, section_content, file_path, chapter, disease, start_index):
        """
        疾患ごとのセクションをさらにチャンクに分割し、メタデータを付与する内部メソッド。
        ここでは主に段落単位で分割し、H3, H4見出しをメタデータとして抽出します。
        """
        # 2つ以上の連続した改行を段落の区切りとみなし、セクションをさらに細かく分割します。

        paragraphs = re.split(r'\n{2,}', section_content)
        
        current_section = "N/A" # H3見出し
        current_subsection = "N/A" # H4見出し
        chunk_index = start_index

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # ヘッダー情報(H3, H4)を抽出し、現在のチャンクのメタデータとして利用
            h3_match = re.search(r'^###\s*(.*?)\n', paragraph)
            h4_match = re.search(r'^####\s*(.*?)\n', paragraph)

            if h3_match:
                # CQやBQの番号も抽出し、メタデータに含める
                cq_bq_match = re.search(r'(Clinical Question|BQ)\s*(\d+)', h3_match.group(1), re.IGNORECASE)
                if cq_bq_match:
                    current_section = f"{cq_bq_match.group(1).upper()} {cq_bq_match.group(2)}"
                else:
                    current_section = h3_match.group(1).strip()
                current_subsection = "N/A" # H3が変わったらH4はリセット

            if h4_match:
                current_subsection = h4_match.group(1).strip()

            # 短すぎるチャンクはノイズになる可能性が高いため除外する
            if len(paragraph.split()) < 5:
                continue

            # RAGの検索精度と回答生成の質を向上させるための重要なメタデータを作成
            metadata = {
                "source": os.path.basename(file_path),
                "chapter": chapter,
                "disease": disease,
                "section": current_section,
                "subsection": current_subsection
            }
            
            # [エラー解決の記録: DuplicateIDError]
            # 課題: 当初、チャンクのテキスト内容(paragraph)のみからハッシュIDを生成していました。
            #       しかし、ガイドライン内には「推奨度A」のような全く同じ短いテキストが
            #       複数存在するため、IDが重複しChromaDBへの登録時にエラーが発生しました。
            #
            # 解決策: IDの生成元に「ファイルパス」と「ファイル内での連番(chunk_index)」を追加しました。
            #         これにより、たとえテキスト内容が同じでも、由来する場所が異なれば
            #         必ずユニークなIDが生成されるようになり、IDの重複が完全に解消されました。
            
            # チャンクごとにユニークなIDを生成する。
            # テキスト内容だけでなくファイルパスと連番を含めることで、完全に重複しないIDを保証する。
            unique_string = f"{file_path}:{chunk_index}:{paragraph}"
            chunk_id = hashlib.sha256(unique_string.encode()).hexdigest()

            chunks_list.append({
                "id": chunk_id,
                "text": paragraph,
                "metadata": metadata
            })
            
            chunk_index += 1

        return chunk_index