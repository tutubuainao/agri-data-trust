from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.loader import load_data
from src.profiler import profile_data
from src.report import generate_html_report, generate_markdown_report
from src.scoring import run_full_analysis, sub_scores_dataframe


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"


st.set_page_config(page_title="农业原始数据可信度检测 MVP", layout="wide")
st.title("农业原始数据可信度检测系统 MVP")
st.caption("输出可信度评分和可疑风险，不判定数据一定为假。")

uploaded = st.file_uploader("上传 CSV 或 Excel 文件", type=["csv", "xlsx", "xls"])

sample_col1, sample_col2 = st.columns(2)
with sample_col1:
    use_real = st.button("加载模拟真实数据")
with sample_col2:
    use_fake = st.button("加载过度平滑数据")

df: pd.DataFrame | None = None
source_name = ""

try:
    if uploaded is not None:
        df = load_data(uploaded, uploaded.name)
        source_name = uploaded.name
    elif use_real:
        source_name = "sample_real.csv"
        df = load_data(BASE_DIR / "data" / source_name)
    elif use_fake:
        source_name = "sample_fake.csv"
        df = load_data(BASE_DIR / "data" / source_name)
except Exception as exc:
    st.error(f"读取文件失败：{exc}")

if df is None:
    st.info("请上传数据文件，或点击上方按钮加载示例数据。")
    st.stop()

prepared, profile = profile_data(df)

st.subheader("数据预览")
st.dataframe(prepared.head(50), use_container_width=True)

left, right = st.columns([1, 2])
with left:
    st.metric("行数", profile.rows)
    st.metric("列数", profile.columns)
    st.metric("缺失率", f"{profile.missing_rate:.2%}")
with right:
    st.write("自动识别结果")
    st.write(f"时间列：`{profile.time_column or '未识别'}`")
    st.write(f"数值列：`{', '.join(profile.numeric_columns) if profile.numeric_columns else '未识别'}`")
    if profile.time_column is None:
        st.caption("未识别到时间列时，系统会按数据原始行顺序执行时间序列类检测。")

if not profile.numeric_columns:
    st.warning("未识别到可分析的数值列，请检查数据格式。")
    st.stop()

with st.spinner("正在执行五类可信度检测..."):
    analysis = run_full_analysis(prepared, profile.numeric_columns, REPORTS_DIR)
    markdown_path = generate_markdown_report(analysis, profile, source_name or "uploaded_data", REPORTS_DIR)
    html_path = generate_html_report(markdown_path)

st.subheader("总体结果")
score_col, risk_col = st.columns(2)
score_col.metric("总可信度评分", f"{analysis['total_score']} / 100")
risk_col.metric("风险等级", analysis["risk_level"])

st.subheader("五项指标子评分")
st.dataframe(sub_scores_dataframe(analysis["sub_scores"]), use_container_width=True)

st.subheader("可疑原因解释")
for reason in analysis["reasons"]:
    st.write(f"- {reason}")

st.subheader("分列检测详情")
for col, checks in analysis["column_results"].items():
    with st.expander(f"{col}", expanded=False):
        for result in checks.values():
            st.markdown(f"**{result['label']}：{result['score']:.1f}**")
            for reason in result.get("reasons", []):
                st.write(f"- {reason}")
            if result.get("metrics"):
                st.json(result["metrics"], expanded=False)
            for chart in result.get("charts", []):
                st.image(chart)

st.subheader("多变量相关性")
st.write(f"评分：**{analysis['correlation']['score']:.1f}**")
for reason in analysis["correlation"].get("reasons", []):
    st.write(f"- {reason}")
for chart in analysis["correlation"].get("charts", []):
    st.image(chart)

st.subheader("检测报告")
st.write(f"Markdown 报告：`{markdown_path}`")
st.write(f"HTML 报告：`{html_path}`")
st.download_button("下载 Markdown 报告", markdown_path.read_text(encoding="utf-8"), file_name=markdown_path.name)
st.download_button("下载 HTML 报告", html_path.read_text(encoding="utf-8"), file_name=html_path.name, mime="text/html")
