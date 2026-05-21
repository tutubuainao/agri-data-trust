from __future__ import annotations

import streamlit as st

from src.ui import apply_global_styles


st.set_page_config(page_title="评分标准与实现原理", layout="wide")
apply_global_styles()

st.markdown(
    """
    <section class="trust-hero">
      <h1>评分标准与实现原理</h1>
      <p>这里说明本 MVP 如何读取文件、筛选字段、处理缺失值、计算五类可信度指标，以及如何把子评分合成为总可信度评分。所有结果都只是复核线索，不是“真假”结论。</p>
      <div class="trust-actions">
        <a class="trust-link" href="./" target="_self">返回检测页面</a>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.subheader("1. 风险等级")
st.markdown(
    """
| 总可信度评分 | 风险等级 | 含义 |
| --- | --- | --- |
| 70-100 | 低风险 | 未发现明显高风险模式，但仍建议结合采集设备、作物、采样频率和业务规则复核。 |
| 50-69.99 | 中风险 | 存在若干可疑模式，需要人工查看原始记录、设备日志或业务背景。 |
| 0-49.99 | 高风险 | 多个指标同时表现异常，建议优先复核数据来源、采集链路和生成方式。 |
"""
)

st.subheader("2. 总分合成")
st.markdown("系统先对五类指标分别得到 0-100 的子评分，再按权重合成总分：")
st.latex(
    r"""
    S =
    0.22S_{smoothness}
    + 0.22S_{timeseries}
    + 0.18S_{digit}
    + 0.18S_{outlier}
    + 0.20S_{correlation}
    """
)
st.markdown(
    """
- 分数越高，说明当前规则下越接近“可解释的自然采集数据”。
- 分数越低，说明出现了更多“过于平滑、过于整齐、异常点分布不自然、变量关系过强”等可疑信号。
- 评分不是法律、审计或鉴定结论，只是数据复核排序工具。
"""
)

st.subheader("3. 文件粗筛")
st.markdown(
    """
系统不会把所有列都强行塞进数值模型。上传文件后，会先按列做粗筛：

| 列类型 | 处理方式 |
| --- | --- |
| 时间列 | 用 `pandas.to_datetime(..., errors="coerce")` 解析；识别成功后用于排序和时间序列解释，不作为数值变量评分。 |
| 数值检测列 | 使用 `pandas.to_numeric(..., errors="coerce")` 解析；数值可解析率 >= 70%，且有效唯一值数 >= 3，才进入五类检测。 |
| 常量或变化不足列 | 如果一列都是同一个值，或有效唯一值少于 3，不进入时间序列类检测；页面会提示可能是常量列、停滞传感器或填充值。 |
| 文本/分类列 | 当前 MVP 不对文本或分类变量做可信度评分，只在粗筛表中解释为什么跳过。 |
| 日期辅助列 | 如果不是主时间列，当前版本不评分；后续可扩展为多时间字段一致性校验。 |
| 空列 | 不进入检测，只计入缺失情况。 |
"""
)

st.subheader("4. 缺失值怎么处理")
st.markdown(
    """
- 系统不会自动填补缺失值，避免人为制造平滑或规律。
- 文件概况会展示整体缺失率，粗筛表会展示每列缺失率。
- 数值列在进入指标计算时，会先通过 `pandas.to_numeric(..., errors="coerce")` 把不可解析值转成缺失。
- 单变量指标使用清洗后的有效数值序列，即 `dropna()` 后再计算。
- 相关性矩阵使用 pandas 的 `corr(method="pearson")` 与 `corr(method="spearman")`，只基于可用数值对计算。
- 如果缺失导致有效样本太少，部分指标会返回 50 分的中性提示，并说明“样本过少，判断不稳定”。
"""
)

st.subheader("5. 五类指标实现")

with st.expander("平滑度检测", expanded=True):
    st.markdown(
        """
目标：判断序列是否过于平滑、变化节奏是否过于机械。

主要计算：

- 一阶差分：`Δx_t = x_t - x_{t-1}`
- 归一化平均变化幅度：`mean(abs(Δx)) / (max(x) - min(x))`
- 差分变异系数：`std(Δx) / (abs(mean(Δx)) + ε)`
- 二阶差分：`Δ²x_t = Δx_t - Δx_{t-1}`
- rolling variance：使用 3-7 左右的自适应窗口
- 变化率标准差：`std(pct_change(x))`

可疑信号：

- 一阶差分相对整体范围过小
- 相邻变化幅度高度稳定
- 二阶差分几乎没有波动
- rolling variance 长期偏低
- 变化率标准差过低
"""
    )

with st.expander("时间序列自然性检测"):
    st.markdown(
        """
目标：判断数据是否具有真实农业采集数据常见的时间相关性、趋势变化和短期扰动。

使用库：

- `statsmodels.tsa.stattools.acf`
- `numpy.corrcoef`

主要计算：

- ACF 自相关函数，重点观察 `lag1`、`lag2` 和高阶滞后
- 趋势方向变化率：相邻差分符号变化次数 / 可比较区间数
- 趋势强度：`abs(corr(time_index, value))`

可疑信号：

- `lag1 autocorrelation` 接近 1，呈机械式连续变化
- 趋势方向变化很少
- 整体趋势近似完美线性
- 高阶 ACF 几乎全部接近 0，时间结构过弱
"""
    )

with st.expander("小数位/数字规律检测"):
    st.markdown(
        """
目标：检测数据是否过于整齐，是否有人工整理或生成痕迹。

主要计算：

- 整数比例：`mean(isclose(x % 1, 0))`
- 小数位数量分布
- 尾数分布：将数值放大 100 后观察最后一位
- 是否大量落在 `0.05` 的倍数上
- 重复值比例：`1 - nunique(x) / n`

可疑信号：

- 整数比例过高
- 小数位数量高度一致
- 尾数集中在少数数字
- 大量数值落在固定步长上
- 重复值比例过高
"""
    )

with st.expander("异常点分布检测"):
    st.markdown(
        """
目标：判断是否存在合理的自然异常波动。真实农业传感器数据通常会有少量噪声、突变、采集扰动或环境冲击；完全没有异常点也可能值得复核。

使用库：

- `scikit-learn IsolationForest`
- `numpy`
- `pandas`

主要计算：

- z-score：`z = (x - mean(x)) / std(x)`，通常 `abs(z) > 3` 视作异常候选
- IQR：低于 `Q1 - 1.5 * IQR` 或高于 `Q3 + 1.5 * IQR` 视作异常候选
- IsolationForest：污染率 `contamination = min(0.15, max(0.02, 3 / n))`

可疑信号：

- z-score 和 IQR 完全没有异常点
- 异常点比例过高
- 异常点比例过低且样本较多，可能经过过度清洗
- 整体变异系数极低
"""
    )

with st.expander("多变量相关性检测"):
    st.markdown(
        """
目标：检测变量之间是否存在过强相关或近乎完美线性关系。

使用库：

- `pandas.DataFrame.corr(method="pearson")`
- `pandas.DataFrame.corr(method="spearman")`
- `matplotlib` 生成相关性热力图

主要计算：

- Pearson correlation：线性相关
- Spearman correlation：秩相关，对单调关系更敏感
- 平均绝对 Pearson 相关

可疑信号：

- 任意变量对 `max(abs(Pearson), abs(Spearman)) > 0.99`
- 近乎完美相关：大于 `0.999`
- 多组变量整体平均相关性过高

注意：强相关不一定代表造假。例如温度和光照、湿度和土壤水分可能有真实相关性。系统只提示“需要业务解释”。
"""
    )

st.subheader("6. 当前版本边界")
st.markdown(
    """
- 第一版不使用深度学习。
- 不读取设备编号、地块、作物品种、采样频率等元数据，因此无法做完整业务审计。
- 文本列、分类列、图片、传感器日志暂不纳入评分。
- 当前模型更适合做“可疑线索发现”和“人工复核排序”，不适合作为最终判断。
"""
)
