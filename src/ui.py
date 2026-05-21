from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    st.markdown(
        """
        <style>
          :root {
            --trust-ink: #17202a;
            --trust-muted: #5f6f7a;
            --trust-line: #d9e2dc;
            --trust-green: #1f7a4d;
            --trust-teal: #0f766e;
            --trust-amber: #b7791f;
            --trust-red: #b42318;
            --trust-bg: #f6f8f5;
            --trust-panel: #ffffff;
          }

          .stApp {
            background: linear-gradient(180deg, #f6f8f5 0%, #ffffff 44%);
            color: var(--trust-ink);
          }

          .main .block-container {
            max-width: 1180px;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
          }

          .trust-hero {
            border: 1px solid var(--trust-line);
            background: linear-gradient(135deg, #ffffff 0%, #eef6f1 58%, #fbf7ea 100%);
            border-radius: 10px;
            padding: 22px 24px;
            margin-bottom: 18px;
          }

          .trust-hero h1 {
            margin: 0 0 8px 0;
            font-size: clamp(1.72rem, 3vw, 2.45rem);
            line-height: 1.16;
            letter-spacing: 0;
          }

          .trust-hero p {
            margin: 0;
            color: var(--trust-muted);
            font-size: 1rem;
            max-width: 780px;
          }

          .trust-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 16px;
          }

          .trust-link {
            display: inline-flex;
            align-items: center;
            min-height: 36px;
            padding: 0 12px;
            border: 1px solid #b7cbbb;
            border-radius: 6px;
            color: #14532d !important;
            text-decoration: none !important;
            background: #ffffff;
            font-weight: 600;
          }

          .trust-section-title {
            margin: 18px 0 10px;
            color: var(--trust-muted);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }

          .trust-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 12px 0 18px;
          }

          .trust-metric {
            background: var(--trust-panel);
            border: 1px solid var(--trust-line);
            border-radius: 8px;
            padding: 14px 16px;
            min-height: 92px;
          }

          .trust-metric span {
            display: block;
            color: var(--trust-muted);
            font-size: 0.82rem;
          }

          .trust-metric strong {
            display: block;
            margin-top: 8px;
            color: var(--trust-ink);
            font-size: clamp(1.15rem, 2.5vw, 1.65rem);
            line-height: 1.1;
            word-break: break-word;
          }

          .risk-badge {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.9rem;
          }

          .risk-low { color: #14532d; background: #dcfce7; }
          .risk-mid { color: #7c2d12; background: #ffedd5; }
          .risk-high { color: #7f1d1d; background: #fee2e2; }

          .trust-note {
            border-left: 4px solid var(--trust-teal);
            background: #f0fdfa;
            padding: 12px 14px;
            border-radius: 6px;
            color: #134e4a;
          }

          .trust-muted {
            color: var(--trust-muted);
          }

          div[data-testid="stFileUploader"] section {
            border-color: #b7cbbb;
            background: rgba(255, 255, 255, 0.74);
          }

          div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--trust-line);
            border-radius: 8px;
            padding: 12px 14px;
          }

          div[data-testid="stTabs"] button {
            font-weight: 650;
          }

          @media (max-width: 760px) {
            .main .block-container {
              padding-left: 1rem;
              padding-right: 1rem;
            }

            .trust-hero {
              padding: 18px 16px;
              border-radius: 8px;
            }

            .trust-metrics {
              grid-template-columns: 1fr 1fr;
            }
          }

          @media (max-width: 460px) {
            .trust-metrics {
              grid-template-columns: 1fr;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def risk_badge(risk_level: str) -> str:
    css_class = {
        "低风险": "risk-low",
        "中风险": "risk-mid",
        "高风险": "risk-high",
    }.get(risk_level, "risk-mid")
    return f'<span class="risk-badge {css_class}">{risk_level}</span>'
