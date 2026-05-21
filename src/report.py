from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

from .profiler import DataProfile
from .scoring import sub_scores_dataframe


def generate_markdown_report(
    analysis: dict,
    profile: DataProfile,
    source_name: str,
    reports_dir: Path,
) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = reports_dir / f"trust_report_{timestamp}.md"
    lines: list[str] = []
    lines.append("# 农业原始数据可信度检测报告")
    lines.append("")
    lines.append(f"- 数据文件：{source_name}")
    lines.append(f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 总可信度评分：**{analysis['total_score']} / 100**")
    lines.append(f"- 风险等级：**{analysis['risk_level']}**")
    lines.append("")
    lines.append("> 本系统仅输出可信度评分和可疑风险，不判定数据一定为假。")
    lines.append("")
    lines.append("## 数据概况")
    lines.append("")
    lines.append(f"- 行数：{profile.rows}")
    lines.append(f"- 列数：{profile.columns}")
    lines.append(f"- 时间列：{profile.time_column or '未识别'}")
    lines.append(f"- 数值列：{', '.join(profile.numeric_columns) if profile.numeric_columns else '未识别'}")
    lines.append(f"- 缺失率：{profile.missing_rate:.2%}")
    lines.append("")
    lines.append("## 指标评分")
    lines.append("")
    lines.append(sub_scores_dataframe(analysis["sub_scores"]).to_markdown(index=False))
    lines.append("")
    lines.append("## 主要可疑原因")
    lines.append("")
    for reason in analysis["reasons"]:
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("## 分列检测详情")
    lines.append("")
    for col, checks in analysis["column_results"].items():
        lines.append(f"### {col}")
        lines.append("")
        for result in checks.values():
            lines.append(f"#### {result['label']}：{result['score']:.1f}")
            for reason in result.get("reasons", []):
                lines.append(f"- {reason}")
            if result.get("metrics"):
                metric_text = ", ".join(f"{k}={v}" for k, v in result["metrics"].items())
                lines.append(f"- 关键指标：{metric_text}")
            for chart in result.get("charts", []):
                rel = Path(chart).name
                lines.append(f"![{result['label']}]({rel})")
            lines.append("")
    lines.append("## 多变量相关性")
    lines.append("")
    lines.append(f"- 评分：{analysis['correlation']['score']:.1f}")
    for reason in analysis["correlation"].get("reasons", []):
        lines.append(f"- {reason}")
    for chart in analysis["correlation"].get("charts", []):
        lines.append(f"![相关性热力图]({Path(chart).name})")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def markdown_to_simple_html(markdown_text: str, title: str = "农业原始数据可信度检测报告") -> str:
    body = escape(markdown_text)
    body = body.replace("\n", "<br>\n")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 960px; margin: 40px auto; line-height: 1.65; color: #1f2937; }}
    code, pre {{ background: #f3f4f6; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>{body}</body>
</html>"""


def generate_html_report(markdown_path: Path) -> Path:
    html_path = markdown_path.with_suffix(".html")
    html_path.write_text(markdown_to_simple_html(markdown_path.read_text(encoding="utf-8")), encoding="utf-8")
    return html_path
