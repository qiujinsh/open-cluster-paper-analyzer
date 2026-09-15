#### `app.py`
这是整合了本地 JSON 存储、arXiv 检索和 PDF 翻译的完整代码。

```python
import streamlit as st
import arxiv
import fitz  # PyMuPDF
import google.generativeai as genai
import json
import os

# ================= 配置区 =================
# 请填入你的 Gemini API Key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

DB_FILE = "papers_db.json"

st.set_page_config(page_title="疏散星团文献助手", layout="wide")

# ================= 核心函数 =================
def load_saved_papers():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_paper(title, source, summary_result):
    papers = load_saved_papers()
    if not any(p['title'] == title for p in papers):
        papers.append({
            "title": title,
            "source": source,
            "summary_result": summary_result
        })
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(papers, f, ensure_ascii=False, indent=4)

def fetch_arxiv_papers(query="all:open cluster", max_results=5):
    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.SubmittedDate)
    return [{"title": r.title, "summary": r.summary, "pdf_url": r.pdf_url, "published": r.published} for r in client.results(search)]

def extract_text_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def summarize_and_translate(text):
    prompt = f"""
    你是一个天体物理学领域的专家。请阅读以下有关“疏散星团”的论文文本：
    1. 【中文总结】：用一段话概括这篇论文的核心发现和研究方法。
    2. 【要点提取】：列出3-5个核心研究要点（例如是否涉及Gaia DR3数据、等色线拟合、动力学演化等），并翻译成中文。
    
    内容：
    {text[:30000]} 
    """
    response = model.generate_content(prompt)
    return response.text

# ================= 网页 UI 构建 =================
st.title("🌌 疏散星团文献分析与构建系统")

option = st.sidebar.radio("🧭 导航菜单", ("📚 我的文献库 (已存文章)", "📥 从 arXiv 获取最新文章", "📂 导入本地 PDF"))

if option == "📚 我的文献库 (已存文章)":
    st.header("📚 我的知识库")
    saved_papers = load_saved_papers()
    if not saved_papers:
        st.info("文献库为空，请前往其他页面获取或导入文献。")
    else:
        for i, paper in enumerate(reversed(saved_papers)):
            with st.expander(f"📌 {paper['title']} ({paper['source']})"):
                st.markdown(paper['summary_result'])

elif option == "📥 从 arXiv 获取最新文章":
    st.header("📥 最新 arXiv 论文检索")
    if st.button("获取最新 5 篇文章"):
        with st.spinner("正在检索中..."):
            papers = fetch_arxiv_papers("ti:\"open cluster\" OR abs:\"open cluster\"", 5)
            for i, paper in enumerate(papers):
                st.subheader(f"{i+1}. {paper['title']}")
                st.write(f"📅 **发布时间**: {paper['published'].strftime('%Y-%m-%d')} | [📄 查看 PDF]({paper['pdf_url']})")
                
                if st.button(f"翻译与总结并保存", key=f"btn_{i}"):
                    with st.spinner("AI 正在分析..."):
                        result = summarize_and_translate(paper['summary'])
                        st.markdown(result)
                        save_paper(paper['title'], "arXiv", result)
                        st.success("✅ 已保存至【我的文献库】！")
                st.divider()

elif option == "📂 导入本地 PDF":
    st.header("📂 本地文献深度解析")
    uploaded_file = st.file_uploader("上传 PDF 文件", type="pdf")
    if uploaded_file and st.button("开始提取并分析全文"):
        with st.spinner("正在解析 PDF 并调用 AI 模型，请稍候..."):
            paper_text = extract_text_from_pdf(uploaded_file)
            result = summarize_and_translate(paper_text)
            st.markdown("### 🧠 AI 分析结果")
            st.markdown(result)
            save_paper(uploaded_file.name, "本地 PDF", result)
            st.success("✅ 全文总结已保存至【我的文献库】！")
