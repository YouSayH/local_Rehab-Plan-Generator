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
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = []

        # 章タイトル(# H1)を抽出し、メタデータとして利用する
        chapter_match = re.search(r"^#\s*(.*?)\n", content)
        chapter_title = chapter_match.group(1).strip() if chapter_match else "不明な章"

        # H2見出し(##)を「疾患」の区切りとみなし、文書を大きなセクションに分割。
        # これにより、「大腿骨近位部骨折」と「変形性股関節症」の情報が混ざるのを防ぎ、文脈を維持します。

        sections = re.split(r"\n(##\s)", content)

        # 最初のセクション（H2見出しより前）の処理
        current_content = sections[0]
        current_disease = "疾患総論"  # H2がない場合は総論として扱う
        chunk_counter = 0

        chunk_counter = self._process_section(
            chunks,
            current_content,
            file_path,
            chapter_title,
            current_disease,
            chunk_counter,
        )

        # H2見出し以降のセクションをループ処理
        for i in range(1, len(sections), 2):
            # `re.split`の仕様上、区切り文字(##)とそれに続くコンテンツが交互にリストに入るため、2つずつ結合する

            current_content = sections[i] + sections[i + 1]

            disease_match = re.search(r"##\s*(.*?)\n", current_content)
            if disease_match:
                current_disease = disease_match.group(1).strip()

            chunk_counter = self._process_section(
                chunks,
                current_content,
                file_path,
                chapter_title,
                current_disease,
                chunk_counter,
            )

        return chunks

    def _process_section(
        self, chunks_list, section_content, file_path, chapter, disease, start_index
    ):
        """
        [最終修正版ロジック]
        ヘッダーで分割し、ヘッダータイトルと本文を明確に分離する。
        """
        paragraphs = re.split(r"\n(###\s*|####\s*|#####\s*)", section_content)

        current_section = "N/A"
        current_subsection = "N/A"
        current_subsubsection = "N/A"
        chunk_index = start_index

        # 最初の要素(paragraphs)はヘッダーの前に来るテキストなので、先に処理する
        if paragraphs and paragraphs[0]:
            text_content = paragraphs[0].strip()
            if len(text_content.split()) >= 5:
                metadata = {
                    "source": os.path.basename(file_path),
                    "chapter": chapter,
                    "disease": disease,
                    "section": current_section,
                    "subsection": current_subsection,
                    "subsubsection": current_subsubsection,
                }
                unique_string = f"{file_path}:{chunk_index}:{text_content}"
                chunk_id = hashlib.sha256(unique_string.encode()).hexdigest()
                chunks_list.append(
                    {"id": chunk_id, "text": text_content, "metadata": metadata}
                )
                chunk_index += 1

        # ヘッダーとテキストのペアを処理
        for i in range(1, len(paragraphs), 2):
            header_marker = paragraphs[i].strip()
            if i + 1 >= len(paragraphs):
                continue

            full_text_block = paragraphs[i + 1]
            block_parts = full_text_block.split("\n", 1)

            header_title = block_parts[0].strip()
            text_content = block_parts[1].strip() if len(block_parts) > 1 else ""

            # ヘッダーレベルに応じて現在の階層を更新
            if header_marker.startswith("###"):
                cq_bq_match = re.search(
                    r"(Clinical Question|BQ)\s*(\d+)", header_title, re.IGNORECASE
                )
                current_section = (
                    f"{cq_bq_match.group(1).upper()} {cq_bq_match.group(2)}"
                    if cq_bq_match
                    else header_title
                )
                current_subsection = "N/A"
                current_subsubsection = "N/A"
            elif header_marker.startswith("####"):
                current_subsection = header_title
                current_subsubsection = "N/A"
            elif header_marker.startswith("#####"):
                current_subsubsection = header_title

            # 本文が短すぎる場合はチャンク化しない (タイトルだけの行などをスキップ)
            # Mermaidコードはそれ自体がテキストなので、特別扱いは不要
            if len(text_content.split()) < 2:
                continue

            metadata = {
                "source": os.path.basename(file_path),
                "chapter": chapter,
                "disease": disease,
                "section": current_section,
                "subsection": current_subsection,
                "subsubsection": current_subsubsection,
            }
            unique_string = f"{file_path}:{chunk_index}:{text_content}"
            chunk_id = hashlib.sha256(unique_string.encode()).hexdigest()

            # チャンクの"text"には、純粋な本文だけを保存する（これが重要）
            chunks_list.append(
                {"id": chunk_id, "text": text_content, "metadata": metadata}
            )
            chunk_index += 1

        return chunk_index
