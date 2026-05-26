from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


ALL_INDICATORS = (
    "sampling",
    "smoothness",
    "digit",
    "outlier",
    "physical",
    "timeseries",
    "drift",
    "changepoint",
    "correlation",
    "ml_anomaly",
)

DEFAULT_CORE_INDICATORS = (
    "sampling",
    "smoothness",
    "digit",
    "outlier",
    "physical",
)

OPTIONAL_INDICATORS = (
    "timeseries",
    "drift",
    "changepoint",
    "correlation",
    "ml_anomaly",
)

INDICATOR_META: dict[str, dict[str, str | bool]] = {
    "sampling": {
        "label": "采样完整性",
        "short": "采样",
        "group": "默认核心指标",
        "default": True,
        "applicability": "CSV/Excel 原始文件都建议检测，特别适合带时间列、多 sheet 或存在缺测的文件。",
        "reason": "先判断文件结构、时间间隔、重复时间戳和连续缺测，避免后续指标建立在明显不完整的数据上。",
    },
    "smoothness": {
        "label": "平滑度检测",
        "short": "平滑",
        "group": "默认核心指标",
        "default": True,
        "applicability": "传感器连续值、产量测量值、农残浓度等数值列均可作为基础风险线索。",
        "reason": "识别过度平滑、固定步长和变化率过稳的模式，是人工生成或过度处理数据的常见线索。",
    },
    "digit": {
        "label": "小数位/数字规律",
        "short": "数字",
        "group": "默认核心指标",
        "default": True,
        "applicability": "适合连续测量值和人工记录表。计数型整数列会自动放宽整数相关扣分。",
        "reason": "检查整数比例、小数位、末位数字、固定刻度和重复值，发现过度整齐的录入模式。",
    },
    "outlier": {
        "label": "异常点分布",
        "short": "异常",
        "group": "默认核心指标",
        "default": True,
        "applicability": "适合大多数数值列。完全没有异常点或异常点过多都会作为复核线索。",
        "reason": "真实农业采集通常存在一定自然波动；该指标关注点级异常，而不是阶段性结构变化。",
    },
    "physical": {
        "label": "物理范围/单位",
        "short": "物理",
        "group": "默认核心指标",
        "default": True,
        "applicability": "适合温度、湿度、降雨量、农残、产量、虫害计数等常见字段。",
        "reason": "用可配置农业规则做防呆，提示超出物理范围、疑似单位错用和字段规则覆盖不足。",
    },
    "timeseries": {
        "label": "时间序列自然性",
        "short": "时序",
        "group": "可选增强指标",
        "default": False,
        "applicability": "更适合按时间连续采集的数据，如温室环境、土壤墒情、气象传感器。",
        "reason": "检查自相关、ACF、趋势反转和周期线索；与平滑度相关但不等价，重点是时间依赖结构。",
    },
    "drift": {
        "label": "传感器漂移",
        "short": "漂移",
        "group": "可选增强指标",
        "default": False,
        "applicability": "只建议用于同一设备长期连续采集的数据；人工调查表通常不需要。",
        "reason": "识别基线缓慢偏移、前后窗口均值变化和 CUSUM 累积偏差，提示设备校准或老化风险。",
    },
    "changepoint": {
        "label": "变化点检测",
        "short": "变点",
        "group": "可选增强指标",
        "default": False,
        "applicability": "适合怀疑换设备、换批次、改采样条件或阶段性农情变化的数据。",
        "reason": "关注段级均值/分布突变；与异常点分布有交集，但异常点偏点级，变化点偏阶段结构。",
    },
    "correlation": {
        "label": "多变量相关性",
        "short": "相关",
        "group": "可选增强指标",
        "default": False,
        "applicability": "至少有两个有业务含义的数值列时建议开启；单变量文件不需要。",
        "reason": "检查 Pearson/Spearman 过强相关和近乎复制列，适合多变量传感器和综合调查表。",
    },
    "ml_anomaly": {
        "label": "机器学习异常识别",
        "short": "机器",
        "group": "可选增强指标",
        "default": False,
        "applicability": "适合至少 20 行、至少 2 个有效数值特征的数据；无标签时作为辅助复核指标。",
        "reason": "使用 IsolationForest、LocalOutlierFactor、One-Class SVM 做多变量行级无监督集成，作为异常点和相关性之外的辅助复核线索。",
    },
}


SCENARIO_RELEVANCE: dict[str, dict[str, float]] = {
    "auto": {
        "sampling": 1.10,
        "smoothness": 1.25,
        "digit": 1.05,
        "outlier": 1.05,
        "physical": 1.00,
        "timeseries": 0.80,
        "drift": 0.55,
        "changepoint": 0.65,
        "correlation": 0.75,
        "ml_anomaly": 0.80,
    },
    "greenhouse": {
        "sampling": 1.10,
        "smoothness": 1.10,
        "digit": 0.65,
        "outlier": 0.90,
        "physical": 0.90,
        "timeseries": 1.00,
        "drift": 1.00,
        "changepoint": 0.80,
        "correlation": 0.70,
        "ml_anomaly": 0.90,
    },
    "pest": {
        "sampling": 1.00,
        "smoothness": 0.60,
        "digit": 1.10,
        "outlier": 1.00,
        "physical": 1.05,
        "timeseries": 0.45,
        "drift": 0.25,
        "changepoint": 0.85,
        "correlation": 0.70,
        "ml_anomaly": 0.65,
    },
    "yield": {
        "sampling": 1.00,
        "smoothness": 0.70,
        "digit": 0.95,
        "outlier": 0.95,
        "physical": 1.05,
        "timeseries": 0.45,
        "drift": 0.25,
        "changepoint": 0.60,
        "correlation": 1.00,
        "ml_anomaly": 0.70,
    },
    "residue": {
        "sampling": 0.90,
        "smoothness": 0.55,
        "digit": 1.15,
        "outlier": 1.00,
        "physical": 1.25,
        "timeseries": 0.30,
        "drift": 0.20,
        "changepoint": 0.55,
        "correlation": 0.85,
        "ml_anomaly": 0.75,
    },
}


def available_indicator_payload() -> list[dict[str, Any]]:
    return [
        {"key": key, **INDICATOR_META[key]}
        for key in ALL_INDICATORS
    ]


def default_indicators_for_scenario(_: str | None = None) -> list[str]:
    return list(DEFAULT_CORE_INDICATORS)


def normalize_selected_indicators(indicators: str | Iterable[str] | None) -> list[str]:
    if indicators is None:
        raw: list[Any] = []
    elif isinstance(indicators, str):
        text = indicators.strip()
        if not text:
            raw = []
        elif text.startswith("["):
            try:
                loaded = json.loads(text)
                raw = list(loaded) if isinstance(loaded, list) else []
            except json.JSONDecodeError:
                raw = text.split(",")
        else:
            raw = text.split(",")
    else:
        raw = list(indicators)

    selected: list[str] = []
    for item in raw:
        key = str(item).strip()
        if key in INDICATOR_META and key not in selected:
            selected.append(key)
    return selected


def resolve_indicator_selection(
    scenario: str | None = None,
    indicators: str | Iterable[str] | None = None,
    custom_indicators: bool = False,
) -> dict[str, Any]:
    selected = normalize_selected_indicators(indicators) if custom_indicators else []
    mode = "自定义指标" if custom_indicators and selected else "默认核心指标"
    if not selected:
        selected = default_indicators_for_scenario(scenario)
    return {
        "mode": mode,
        "selected": selected,
        "available": available_indicator_payload(),
        "default_core": list(DEFAULT_CORE_INDICATORS),
        "optional": list(OPTIONAL_INDICATORS),
    }


def weights_for_selection(scenario: str | None, selected: str | Iterable[str] | None) -> dict[str, float]:
    keys = [key for key in normalize_selected_indicators(selected) if key in INDICATOR_META]
    if not keys:
        keys = default_indicators_for_scenario(scenario)
    relevance = SCENARIO_RELEVANCE.get(scenario or "auto", SCENARIO_RELEVANCE["auto"])
    raw_weights = {key: max(float(relevance.get(key, 1.0)), 0.0) for key in keys}
    total = sum(raw_weights.values())
    if total <= 0:
        return {key: round(1.0 / len(keys), 6) for key in keys}
    return {key: round(value / total, 6) for key, value in raw_weights.items()}
