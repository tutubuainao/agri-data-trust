from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.loader import load_data
from src.profiler import profile_data
from src.report import generate_html_report
from src.scoring import run_full_analysis, sub_scores_dataframe
from src.screening import screen_columns, screening_dataframe
from src.ui import apply_global_styles, risk_badge


BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"


st.set_page_config(page_title="农业原始数据可信度检测 MVP", layout="wide")
apply_global_styles()

st.markdown(
    """
    <section class="trust-hero">
      <h1>农业原始数据可信度检测系统 MVP</h1>
      <p>上传 CSV 或 Excel 后，系统会先做文件粗筛，再对可分析的数值列执行五类可信度检测，输出评分、风险等级、解释和 HTML 报告。本系统只提示可疑风险，不判定数据一定为假。</p>
      <div class="trust-actions">
        <a class="trust-link" href="methodology" target="_self">查看评分标准与实现原理</a>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("项目说明")
    try:
        st.page_link("pages/01_methodology.py", label="评分标准与实现原理")
    except Exception:
        st.markdown("[评分标准与实现原理](methodology)")
    st.caption("普通数值检测、文件粗筛、缺失值处理和评分阈值说明都在说明页中。")

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
screening_records = screen_columns(df, profile)
screening_df = screening_dataframe(screening_records)

st.markdown('<div class="trust-section-title">数据概况</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="trust-metrics">
      <div class="trust-metric"><span>数据文件</span><strong>{escape(source_name or "uploaded_data")}</strong></div>
      <div class="trust-metric"><span>行数</span><strong>{profile.rows}</strong></div>
      <div class="trust-metric"><span>列数</span><strong>{profile.columns}</strong></div>
      <div class="trust-metric"><span>整体缺失率</span><strong>{profile.missing_rate:.2%}</strong></div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("自动识别结果", expanded=True):
    st.write(f"时间列：`{profile.time_column or '未识别'}`")
    st.write(f"进入五类检测的数值列：`{', '.join(profile.numeric_columns) if profile.numeric_columns else '未识别'}`")
    if profile.time_column is None:
        st.caption("未识别到时间列时，系统会按数据原始行顺序执行时间序列类检测。")

st.markdown('<div class="trust-section-title">文件粗筛</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="trust-note">文件粗筛会先判断每一列是时间列、数值检测列、文本/分类列、日期辅助列还是常量/变化不足列。只有“数值可解析率 >= 70% 且有效唯一值数 >= 3”的非时间列会进入五类可信度检测。</div>',
    unsafe_allow_html=True,
)
st.dataframe(screening_df, use_container_width=True, hide_index=True)

st.markdown('<div class="trust-section-title">数据预览</div>', unsafe_allow_html=True)
st.dataframe(prepared.head(50), use_container_width=True, hide_index=True)

if not profile.numeric_columns:
    st.warning("未识别到可分析的数值列，请检查数据格式。")
    st.stop()

with st.spinner("正在执行五类可信度检测..."):
    analysis = run_full_analysis(prepared, profile.numeric_columns, REPORTS_DIR)
    html_path = generate_html_report(
        analysis,
        profile,
        source_name or "uploaded_data",
        REPORTS_DIR,
        screening_records=screening_records,
    )

overview_tab, detail_tab, correlation_tab, report_tab = st.tabs(["总体结果", "分列详情", "相关性", "检测报告"])

with overview_tab:
    st.markdown(
        f"""
        <div class="trust-metrics">
          <div class="trust-metric"><span>总可信度评分</span><strong>{analysis['total_score']} / 100</strong></div>
          <div class="trust-metric"><span>风险等级</span><strong>{risk_badge(analysis['risk_level'])}</strong></div>
          <div class="trust-metric"><span>检测数值列</span><strong>{len(profile.numeric_columns)}</strong></div>
          <div class="trust-metric"><span>报告格式</span><strong>HTML</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("五项指标子评分")
    st.dataframe(sub_scores_dataframe(analysis["sub_scores"]), use_container_width=True, hide_index=True)

    st.subheader("可疑原因解释")
    for reason in analysis["reasons"]:
        st.write(f"- {reason}")

with detail_tab:
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

with correlation_tab:
    st.subheader("多变量相关性")
    st.write(f"评分：**{analysis['correlation']['score']:.1f}**")
    for reason in analysis["correlation"].get("reasons", []):
        st.write(f"- {reason}")
    for chart in analysis["correlation"].get("charts", []):
        st.image(chart)

with report_tab:
    st.subheader("检测报告")
    st.write(f"HTML 报告：`{html_path}`")
    st.download_button(
        "下载 HTML 报告",
        html_path.read_text(encoding="utf-8"),
        file_name=html_path.name,
        mime="text/html",
    )
