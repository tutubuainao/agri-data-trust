from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicalRule:
    key: str
    label: str
    patterns: tuple[str, ...]
    soft_min: float | None = None
    soft_max: float | None = None
    hard_min: float | None = None
    hard_max: float | None = None
    unit_note: str = ""


SCENARIOS: dict[str, dict[str, object]] = {
    "auto": {
        "label": "自动识别",
        "description": "系统按字段名称自动匹配通用农业规则。",
    },
    "greenhouse": {
        "label": "温室数据",
        "description": "适合温度、湿度、土壤水分、光照、CO2、pH、EC 等连续传感器。",
    },
    "pest": {
        "label": "虫害调查",
        "description": "适合卵量、幼虫、成虫、诱捕量、寄生率等调查表。",
    },
    "yield": {
        "label": "产量调查",
        "description": "适合产量、面积、株高、穗数、千粒重等农艺调查数据。",
    },
    "residue": {
        "label": "农残检测",
        "description": "适合农药残留、检出限、含量浓度等检测数据。",
    },
}


COMMON_RULES: tuple[PhysicalRule, ...] = (
    PhysicalRule("temperature", "温度", ("温度", "气温", "temperature", "temp"), -20, 60, -50, 80, "默认按摄氏度复核。"),
    PhysicalRule("humidity", "湿度", ("湿度", "humidity", "rh"), 0, 100, 0, 100, "默认按百分比 0-100 复核。"),
    PhysicalRule("soil_moisture", "土壤水分", ("土壤水", "墒情", "soil_moisture", "moisture"), 0, 100, 0, 100, "默认按百分比 0-100 复核。"),
    PhysicalRule("rainfall", "降雨量", ("降雨", "雨量", "rain", "rainfall", "precip"), 0, 300, 0, 1000, "默认按毫米复核，极端暴雨仍建议人工确认。"),
    PhysicalRule("light", "光照", ("光照", "照度", "light", "lux"), 0, 200000, 0, 250000, "默认按 lux 复核。"),
    PhysicalRule("ph", "pH", ("ph", "酸碱"), 3, 10, 0, 14, "pH 按 0-14 的物理范围复核。"),
    PhysicalRule("ec", "电导率", ("ec", "电导", "conductivity"), 0, 20, 0, 50, "默认按常见农业 EC 范围做宽松复核。"),
    PhysicalRule("co2", "二氧化碳", ("co2", "二氧化碳"), 250, 5000, 0, 10000, "默认按 ppm 复核。"),
    PhysicalRule("yield", "产量", ("产量", "yield"), 0, 30000, 0, 100000, "默认按 kg/ha 或同类非负产量指标做宽松复核。"),
    PhysicalRule("pesticide_residue", "农药残留", ("农药残留", "残留", "residue", "pesticide"), 0, 50, 0, 1000, "不同药剂限量差异很大，这里只做非负和极端值复核，不替代法规判定。"),
)

SCENARIO_EXTRA_RULES: dict[str, tuple[PhysicalRule, ...]] = {
    "pest": (
        PhysicalRule("pest_count", "虫害计数", ("卵", "幼虫", "成虫", "虫量", "诱捕", "螟", "蛾", "count"), 0, 100000, 0, 1000000, "虫害调查计数应为非负值。"),
        PhysicalRule("rate", "比例/率", ("率", "比例", "percent", "rate"), 0, 100, 0, 100, "默认按百分比 0-100 复核。"),
    ),
    "yield": (
        PhysicalRule("area", "面积", ("面积", "area"), 0, 100000, 0, 10000000, "面积应为非负值，异常大值需复核单位。"),
        PhysicalRule("plant_height", "株高", ("株高", "height"), 0, 400, 0, 1000, "默认按厘米复核。"),
        PhysicalRule("weight", "重量", ("重量", "千粒重", "weight"), 0, 10000, 0, 100000, "重量应为非负值，异常大值需复核单位。"),
    ),
    "residue": (
        PhysicalRule("detection_limit", "检出限", ("检出限", "lod", "loq"), 0, 10, 0, 1000, "检出限应为非负值，异常大值需复核单位。"),
        PhysicalRule("concentration", "浓度/含量", ("浓度", "含量", "mg/kg", "ppm"), 0, 1000, 0, 100000, "浓度应为非负值，超大值需复核单位。"),
    ),
}


def scenario_info(scenario: str | None) -> dict[str, str]:
    key = scenario if scenario in SCENARIOS else "auto"
    item = SCENARIOS[key]
    return {"key": key, "label": str(item["label"]), "description": str(item["description"])}


def rules_for_scenario(scenario: str | None) -> tuple[PhysicalRule, ...]:
    key = scenario_info(scenario)["key"]
    return COMMON_RULES + SCENARIO_EXTRA_RULES.get(key, ())


def match_rule(column: object, scenario: str | None) -> PhysicalRule | None:
    name = str(column).lower()
    for rule in rules_for_scenario(scenario):
        if any(re.search(re.escape(pattern.lower()), name) for pattern in rule.patterns):
            return rule
    return None
