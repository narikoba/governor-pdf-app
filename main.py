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
        # ファイル名から日付抽出（カッコ内も含めてOKに）
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
            text = "\n".join(page.extract_text() for page in pdf.pages[1:] if page.extract_text())

        # トークン数で制限（gpt-4上限を考慮して4000トークン以内に）
        encoding = tiktoken.encoding_for_model("gpt-4")
        tokens = encoding.encode(text)
        max_tokens = 4000
        text = encoding.decode(tokens[:max_tokens])

        # ChatGPTに渡すプロンプト（精度向上版）
        prompt = f"""
以下の東京都知事会見録のテキストを、レイアウトと読みやすさを整えてください。

【目的】
都知事会見の記録として、見出しを明確にし、各話題が読みやすいように整えてください。読み手が内容をスムーズに理解できるよう工夫してください。

【編集方針】
- 話題ごとに「◉〇〇〇（タイトル）」という見出しを付けてください
- 話題の切れ目が分かるよう、段落を分けてください
- 発言者（知事、記者など）は【知事】のように記載し、行頭で改行してください
- 【知事】や【記者】は太字で表示する前提で構成してください
- インデント、行間を自然に整えてください
- 冗長な言い回しや繰り返し表現は削除・言い換えてください
- 以下のような定型文は削除してください：
    ・「詳細については〇〇へお問い合わせください」
    ・「会見で使用したスライド資料はこちらからご覧いただけます」
- 日本語として自然で、公式記録として適した文章にしてください

---
{text}
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは日本語の行政文書編集の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        cleaned_text = response.choices[0].message.content

        # 冒頭に定型文を追加
        final_text = f"知事記者会見({japanese_date})\n<知事冒頭発言>\n\n{cleaned_text}"

        st.success("整形が完了しました！")
        st.download_button("テキストファイルをダウンロード", final_text, file_name=f"{formatted_date}知事記者会見.txt")
        st.text_area("整形済みテキストプレビュー", final_text, height=600)
