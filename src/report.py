from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
import os
import textwrap
from uuid import uuid4

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path.cwd() / ".cache"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from .indicator_config import INDICATOR_META
from .profiler import DataProfile
from .scoring import sub_scores_dataframe
from .screening import ColumnScreening
from .utils import configure_chinese_font


def _format_metric_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _metrics_table(metrics: dict) -> str:
    if not metrics:
        return ""
    rows = "\n".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(_format_metric_value(value))}</td></tr>"
        for key, value in metrics.items()
    )
    return f"<table class=\"metrics\"><tbody>{rows}</tbody></table>"


def _chart_img(chart: str, alt: str) -> str:
    return f"<img src=\"{escape(Path(chart).name)}\" alt=\"{escape(alt)}\">"


def _screening_table(records: list[ColumnScreening] | None) -> str:
    if not records:
        return ""
    rows = "\n".join(
        f"""
        <tr>
          <td>{escape(item.column)}</td>
          <td>{escape(item.raw_dtype)}</td>
          <td>{escape(item.role)}</td>
          <td>{"是" if item.entered_analysis else "否"}</td>
          <td>{item.non_null_count}</td>
          <td>{item.missing_rate:.2%}</td>
          <td>{item.unique_count}</td>
          <td>{item.numeric_valid_rate:.2%}</td>
          <td>{item.datetime_valid_rate:.2%}</td>
          <td>{escape(item.handling)}</td>
        </tr>
        """
        for item in records
    )
    return f"""
    <h2>文件粗筛</h2>
    <p class="note">只有数值可解析率不低于 70%、有效唯一值不少于 3 个、且不是时间列的字段会进入所选可信度检测中的数值类指标。</p>
    <table>
      <thead>
        <tr>
          <th>列名</th>
          <th>原始类型</th>
          <th>粗筛角色</th>
          <th>进入检测</th>
          <th>非空数</th>
          <th>缺失率</th>
          <th>唯一值数</th>
          <th>数值可解析率</th>
          <th>时间可解析率</th>
          <th>处理方式</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """


def generate_html_report(
    analysis: dict,
    profile: DataProfile,
    source_name: str,
    reports_dir: Path,
    screening_records: list[ColumnScreening] | None = None,
    scenario: dict | None = None,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid4().hex[:6]
    html_path = reports_dir / f"trust_report_{timestamp}_{suffix}.html"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    numeric_columns = ", ".join(profile.numeric_columns) if profile.numeric_columns else "未识别"
    reasons = "\n".join(f"<li>{escape(reason)}</li>" for reason in analysis["reasons"])
    score_table = sub_scores_dataframe(
        analysis["sub_scores"],
        analysis.get("weights"),
    ).to_html(index=False, escape=True)
    scenario_label = escape((scenario or {}).get("label", "自动识别"))
    selected_indicators = analysis.get("selected_indicators", [])
    selected_names = "、".join(
        str(INDICATOR_META.get(key, {}).get("label", key)) for key in selected_indicators
    ) or "默认核心指标"
    selection_mode = escape(str(analysis.get("indicator_selection_mode", "默认核心指标")))

    column_sections: list[str] = []
    for col, checks in analysis["column_results"].items():
        check_sections: list[str] = []
        for result in checks.values():
            result_reasons = "\n".join(
                f"<li>{escape(reason)}</li>" for reason in result.get("reasons", [])
            )
            charts = "\n".join(
                _chart_img(chart, result["label"]) for chart in result.get("charts", [])
            )
            check_sections.append(
                f"""
                <section class="check">
                  <h4>{escape(result["label"])}：{result["score"]:.1f}</h4>
                  <ul>{result_reasons}</ul>
                  {_metrics_table(result.get("metrics", {}))}
                  <div class="charts">{charts}</div>
                </section>
                """
            )
        column_sections.append(
            f"""
            <section class="column">
              <h3>{escape(col)}</h3>
              {''.join(check_sections)}
            </section>
            """
        )

    correlation_block = ""
    if not analysis["correlation"].get("skipped"):
        correlation_reasons = "\n".join(
            f"<li>{escape(reason)}</li>" for reason in analysis["correlation"].get("reasons", [])
        )
        correlation_charts = "\n".join(
            _chart_img(chart, "相关性热力图") for chart in analysis["correlation"].get("charts", [])
        )
        correlation_block = f"""
  <h2>多变量相关性</h2>
  <p>评分：<strong>{analysis["correlation"]["score"]:.1f}</strong></p>
  <ul>{correlation_reasons}</ul>
  <div class="charts">{correlation_charts}</div>
"""
    dataset_sections: list[str] = []
    for result in analysis.get("dataset_results", {}).values():
        result_reasons = "\n".join(f"<li>{escape(reason)}</li>" for reason in result.get("reasons", []))
        charts = "\n".join(_chart_img(chart, result["label"]) for chart in result.get("charts", []))
        dataset_sections.append(
            f"""
            <section class="check">
              <h3>{escape(result["label"])}：{result["score"]:.1f}</h3>
              <ul>{result_reasons}</ul>
              {_metrics_table(result.get("metrics", {}))}
              <div class="charts">{charts}</div>
            </section>
            """
        )

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>农业原始数据可信度检测报告</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1080px; margin: 40px auto; line-height: 1.65; color: #1f2937; background: #ffffff; }}
    h1, h2, h3, h4 {{ color: #111827; line-height: 1.25; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 24px 0; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 14px 16px; }}
    .metric span {{ display: block; color: #6b7280; font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 4px; font-size: 22px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 20px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    .note {{ background: #f9fafb; border-left: 4px solid #2563eb; padding: 12px 14px; margin: 18px 0; }}
    .column, .check {{ border-top: 1px solid #e5e7eb; padding-top: 14px; margin-top: 18px; }}
    .metrics th {{ width: 260px; }}
    img {{ display: block; max-width: 100%; height: auto; margin: 12px 0; border: 1px solid #e5e7eb; border-radius: 6px; }}
    code {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>农业原始数据可信度检测报告</h1>
  <p class="note">本系统仅输出可信度评分和可疑风险，不判定数据一定为假。</p>

  <section class="summary">
    <div class="metric"><span>数据文件</span><strong>{escape(source_name)}</strong></div>
    <div class="metric"><span>生成时间</span><strong>{escape(generated_at)}</strong></div>
    <div class="metric"><span>总可信度评分</span><strong>{analysis["total_score"]} / 100</strong></div>
    <div class="metric"><span>风险等级</span><strong>{escape(analysis["risk_level"])}</strong></div>
  </section>

  <h2>数据概况</h2>
  <table>
    <tbody>
      <tr><th>行数</th><td>{profile.rows}</td></tr>
      <tr><th>列数</th><td>{profile.columns}</td></tr>
      <tr><th>时间列</th><td>{escape(profile.time_column or "未识别")}</td></tr>
      <tr><th>数值列</th><td>{escape(numeric_columns)}</td></tr>
      <tr><th>缺失率</th><td>{profile.missing_rate:.2%}</td></tr>
      <tr><th>规则场景</th><td>{scenario_label}</td></tr>
      <tr><th>指标模式</th><td>{selection_mode}</td></tr>
      <tr><th>本次检测指标</th><td>{escape(selected_names)}</td></tr>
    </tbody>
  </table>

  {_screening_table(screening_records)}

  <h2>指标评分</h2>
  {score_table}

  <h2>主要可疑原因</h2>
  <ul>{reasons}</ul>

  <h2>分列检测详情</h2>
  {''.join(column_sections) or '<p class="note">本次未选择需要按数值列逐列计算的指标。</p>'}

  <h2>数据集级检测详情</h2>
  {''.join(dataset_sections)}

  {correlation_block}
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    return html_path


def _pdf_lines(text: object, width: int = 52) -> list[str]:
    value = str(text)
    if not value:
        return [""]
    lines: list[str] = []
    for part in value.splitlines():
        wrapped = textwrap.wrap(part, width=width, replace_whitespace=False)
        lines.extend(wrapped or [""])
    return lines


def _add_pdf_text_page(
    pdf: PdfPages,
    title: str,
    lines: list[str],
    *,
    footnote: str = "本报告仅提示可信度评分和可疑风险，不判断数据一定为假。",
) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.08, 0.94, title, fontsize=20, weight="bold", color="#111827")
    y = 0.90
    for line in lines:
        if y < 0.08:
            fig.text(0.08, 0.04, footnote, fontsize=9, color="#6b7280")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.patch.set_facecolor("white")
            fig.text(0.08, 0.94, f"{title}（续）", fontsize=18, weight="bold", color="#111827")
            y = 0.90
        fig.text(0.08, y, line, fontsize=10.5, color="#1f2937")
        y -= 0.026
    fig.text(0.08, 0.04, footnote, fontsize=9, color="#6b7280")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def generate_pdf_report(
    analysis: dict,
    profile: DataProfile,
    source_name: str,
    reports_dir: Path,
    screening_records: list[ColumnScreening] | None = None,
    scenario: dict | None = None,
) -> Path:
    configure_chinese_font()
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid4().hex[:6]
    pdf_path = reports_dir / f"trust_report_{timestamp}_{suffix}.pdf"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    selected = analysis.get("selected_indicators", [])
    selected_names = "、".join(
        str(INDICATOR_META.get(key, {}).get("label", key)) for key in selected
    )
    weights = analysis.get("weights", {})

    summary_lines: list[str] = []
    for item in [
        f"数据文件：{source_name}",
        f"生成时间：{generated_at}",
        f"规则场景：{(scenario or {}).get('label', '自动识别')}",
        f"指标模式：{analysis.get('indicator_selection_mode', '默认核心指标')}",
        f"本次检测指标：{selected_names}",
        f"总可信度评分：{analysis['total_score']} / 100",
        f"风险等级：{analysis['risk_level']}",
        f"数据规模：{profile.rows} 行 × {profile.columns} 列",
        f"时间列：{profile.time_column or '未识别'}",
        f"数值列：{', '.join(profile.numeric_columns) if profile.numeric_columns else '未识别'}",
        f"整体缺失率：{profile.missing_rate:.2%}",
        "",
        "主要可疑原因：",
    ]:
        summary_lines.extend(_pdf_lines(item))
    for index, reason in enumerate(analysis.get("reasons", []), start=1):
        summary_lines.extend(_pdf_lines(f"{index}. {reason}", width=58))

    score_lines = ["指标子评分与当前权重："]
    for key, value in analysis.get("sub_scores", {}).items():
        label = INDICATOR_META.get(key, {}).get("label", key)
        score_lines.append(f"{label}：{value:.2f} 分，权重 {weights.get(key, 0) * 100:.1f}%")
    score_lines.append("")
    score_lines.append("文件粗筛摘要：")
    for item in (screening_records or [])[:40]:
        status = "进入检测" if item.entered_analysis else "跳过"
        score_lines.extend(
            _pdf_lines(
                f"{item.column}：{status}；角色={item.role}；缺失率={item.missing_rate:.2%}；处理={item.handling}",
                width=62,
            )
        )

    with PdfPages(pdf_path) as pdf:
        _add_pdf_text_page(pdf, "农业原始数据可信度检测报告", summary_lines)
        _add_pdf_text_page(pdf, "指标评分与文件粗筛", score_lines)
    return pdf_path
