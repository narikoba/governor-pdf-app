# main.py
import streamlit as st
import pdfplumber
from io import BytesIO
from datetime import datetime
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from openai import OpenAI

# OpenAI APIクライアント初期化（v1対応）
client = OpenAI(api_key=st.secrets["openai_api_key"])

st.title("知事記者会見録 自動整形アプリ（高精度版・有料会員向け）")

uploaded_file = st.file_uploader("PDFファイルをアップロードしてください", type="pdf")

if uploaded_file:
    # ファイル名から日付抽出（カッコ内も含めてOKに）
    match = re.search(r"[\(\[]?(\d{4})(\d{2})(\d{2})[\)\]]?", uploaded_file.name)
    if match:
        year, month, day = match.groups()
        formatted_date = f"{int(year)}.{int(month)}.{int(day)}"
        output_filename = f"{formatted_date}知事記者会見.pdf"
    else:
        st.error("ファイル名に日付が含まれていません（例：20250328）。")
        st.stop()

    # PDFからテキストを抽出
    with pdfplumber.open(uploaded_file) as pdf:
        # 最初の1ページ目は表紙としてスキップ
        text = "\n".join(page.extract_text() for page in pdf.pages[1:] if page.extract_text())
        # gpt-4の上限に収まるよう調整（約12000文字程度）
        text = text[:12000]

    # ChatGPTに渡すプロンプト
    prompt = f"""
以下の東京都知事会見録のテキストを、レイアウトと読みやすさを整えてください。
- インデント、フォント、行間を整えてください。
- ＜見出し＞形式でセクションを明確にしてください。
- ダブルスペースや読点の不自然な箇所を修正してください。
- 意味を変えずに、言い直しや重複した表現を省いてください。

---
{text}
    """

    with st.spinner("ChatGPT（gpt-4）で文章を整形中..."):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは日本語の文章校正の専門家です。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
        )
        cleaned_text = response.choices[0].message.content

    # PDFファイルとして保存
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y_position = height - 50
    for line in cleaned_text.split("\n"):
        if y_position < 50:
            c.showPage()
            y_position = height - 50
        c.drawString(50, y_position, line.strip())
        y_position -= 15

    c.save()
    buffer.seek(0)

    st.success("整形が完了しました！")
    st.download_button("PDFファイルをダウンロード", buffer, file_name=output_filename)
