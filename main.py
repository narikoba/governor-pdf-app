# main.py
import streamlit as st
import pdfplumber
from datetime import datetime
import re
from openai import OpenAI
import tiktoken

# OpenAI APIクライアント初期化（v1対応）
client = OpenAI(api_key=st.secrets["openai_api_key"])

st.title("知事記者会見録 自動整形アプリ（高精度版・テキスト出力）")

uploaded_file = st.file_uploader("PDFファイルをアップロードしてください", type="pdf")

# ファイルがアップロードされたらすぐ処理を実行（ユーザー操作不要）
if uploaded_file is not None:
    with st.spinner("ファイルを処理中です。しばらくお待ちください..."):
        match = re.search(r"[\(\[]?(\d{4})(\d{2})(\d{2})[\)\]]?", uploaded_file.name)
        if match:
            year, month, day = match.groups()
            formatted_date = f"{int(year)}.{int(month)}.{int(day)}"
            japanese_date = f"令和{int(year)-2018}年{int(month)}月{int(day)}日"
        else:
            st.error("ファイル名に日付が含まれていません（例：20250328）。")
            st.stop()

        # PDFからテキストを抽出
        with pdfplumber.open(uploaded_file) as pdf:
            full_text = "\n".join(page.extract_text() for page in pdf.pages[1:] if page.extract_text())

        # トークン分割処理
        encoding = tiktoken.encoding_for_model("gpt-4")
        tokens = encoding.encode(full_text)
        max_tokens = 4000
        chunks = []
        while tokens:
            chunk = tokens[:max_tokens]
            chunks.append(encoding.decode(chunk))
            tokens = tokens[max_tokens:]

        cleaned_parts = []
        for i, chunk_text in enumerate(chunks):
            prompt = f"""
以下の東京都知事会見録のテキストを、別添の公式記録PDFと同等のフォーマットに整形してください。

【目的】
会見録を公的記録文書として体裁よく整理し、見出し、段落、語調を整えて読みやすくしてください。

【編集方針】
- 話題ごとに「＜タイトル＞」を見出しとして使い、1行空けて内容を記載してください
- 発言者（知事、記者、司会など）は【知事】のように行頭に明示し、段落を分けてください
- 発言の途中で主語が切り替わる箇所などは改行してください
- 読点や助詞の重複、省略、冗長な言い回しを自然に整えてください
- 会見中に話された内容は意味を変えずにわかりやすい構成にしてください
- 以下のような定型文は完全に削除してください：
    ・「会見で使用したスライド資料はこちらからご覧いただけます」
    ・「詳細は○○までお問い合わせください」など
- 見出し直後は必ず【知事】などで始め、1行で複数トピックを詰めないでください
- 公的文書らしく、句点「。」で文章を整え、句読点の重複や口語は排除してください
- 語尾の「～と思っています」「～と考えています」は整理してください
- 会見録の文体にふさわしい端的な敬体または常体で統一してください
- 「〈質疑応答〉」という表現は「質疑応答」に変え、前後に空行を挿入してください

---
{chunk_text}
            """

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたは東京都庁の行政文書編集官です。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            cleaned_parts.append(response.choices[0].message.content)

        cleaned_text = "\n\n".join(cleaned_parts)

        final_text = f"知事記者会見({japanese_date})\n\n\n＜知事冒頭発言＞\n\n{cleaned_text}"

        st.success("整形が完了しました！")
        st.download_button("テキストファイルをダウンロード", final_text, file_name=f"{formatted_date}知事記者会見.txt")
        st.text_area("整形済みテキストプレビュー", final_text, height=600)
