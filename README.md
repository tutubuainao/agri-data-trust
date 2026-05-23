# 农业原始数据可信度检测系统 MVP

这是一个可直接运行的 Python/FastAPI MVP，用于对农业原始数据进行可信度风险检测。系统不会判断“数据一定是假的”，只输出可信度评分、风险等级和可解释的可疑原因。当前线上版使用 FastAPI 提供算法接口，前端使用 Vue 页面呈现。

## 功能

- 支持上传 CSV、XLSX、XLS 文件
- 自动识别时间列和数值列；没有时间列时按原始行顺序分析
- 上传后先执行文件粗筛，解释常量列、文本列、日期列和缺失列的处理方式
- 对每个数值列执行六类单变量检测
- 支持采样完整性、物理范围与单位异常、规则场景配置
- 对所有数值列执行多变量相关性检测
- 输出 0-100 总可信度评分、九项子评分、风险等级和解释
- FastAPI 接口调用核心算法，Vue 前端展示结果
- 生成 HTML 检测报告
- 提供“评分标准与实现原理”说明页，解释评分等级、公式、依赖库和缺失值处理规则
- 输出趋势图、ACF 图、末位数字分布图、异常点扫描图、传感器漂移扫描图、变化点扫描图和相关性热力图

## 九类指标

1. 平滑度检测：一阶差分、rolling variance、变化率稳定性
2. 时间序列自然性检测：autocorrelation、ACF、趋势变化、方向变化
3. 小数位/数字规律检测：整数比例、小数位分布、末位数字分布、重复值模式；计数型农业调查列会按整数计数规则降权
4. 异常点分布检测：z-score、IQR、IsolationForest；完全没有异常点也会提示风险
5. 传感器漂移检测：前后窗口均值、滚动均值斜率、CUSUM、方差变化、变化方向单一性
6. 变化点检测：CUSUM、Page-Hinkley、滑动窗口均值差异
7. 采样完整性检测：时间间隔 CV、重复时间戳、断点数量、连续缺测、sheet 结构异常
8. 物理范围与单位异常检测：按温室、虫害、产量、农残等场景匹配规则
9. 多变量相关性检测：Pearson、Spearman、相关矩阵、近完美相关变量对

## 安装

建议使用 Python 3.10 或更高版本。

```bash
cd agri-data-trust
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

```bash
uvicorn api_app:app --reload --host 127.0.0.1 --port 8501
```

浏览器打开 `http://127.0.0.1:8501/agri-trust/` 后，可以上传自己的 CSV/Excel 文件，也可以点击页面按钮加载示例数据。

旧版 Streamlit 页面仍保留在 `app.py`，用于对照和回退；线上默认使用 `api_app.py`。

## 线上部署

服务器已配置 SSH key 后，可在本地一键部署：

```bash
./deploy.sh
```

脚本会自动打包当前项目、上传到服务器、更新 `/opt/agri-data-trust`、重启 `agri-data-trust.service`，并验证线上地址。

更多后续维护说明见：`项目操作说明.md`

## GitHub 同步

项目已同步到 GitHub 私有仓库：

```text
https://github.com/tutubuainao/agri-data-trust
```

项目已准备 `.gitignore`，会排除虚拟环境、运行报告、缓存和本地密钥文件。当前本地仓库已配置专用 SSH Deploy key，日常流程为：

```text
本地改代码 → 本地测试 → git commit → git push → ./deploy.sh
```

## 示例数据

- `data/sample_real.csv`：模拟真实农业传感器数据，包含自然波动、昼夜变化和少量不规则扰动
- `data/sample_fake.csv`：模拟人工或 AI 生成的过度平滑数据，数值变化过于线性、尾数过于整齐、变量相关性过强

## 项目结构

```text
agri-data-trust/
├── app.py
├── api_app.py
├── requirements.txt
├── README.md
├── data/
│   ├── sample_real.csv
│   └── sample_fake.csv
├── pages/
│   └── 01_methodology.py
├── src/
│   ├── analysis_service.py
│   ├── loader.py
│   ├── profiler.py
│   ├── screening.py
│   ├── smoothness.py
│   ├── timeseries.py
│   ├── digit_analysis.py
│   ├── outlier.py
│   ├── drift.py
│   ├── changepoint.py
│   ├── sampling_integrity.py
│   ├── physical_rules.py
│   ├── rule_config.py
│   ├── correlation.py
│   ├── scoring.py
│   ├── report.py
│   ├── ui.py
│   └── utils.py
├── web/
│   ├── index.html
│   ├── methodology.html
│   └── assets/
│       ├── app.js
│       └── styles.css
└── reports/
```

## 评分说明

系统采用规则型评分，第一版优先保证可运行、可解释、易调整。总分由九个子指标加权得到：

```text
S = Σ(Wi × Si)
```

其中 `Si` 是各指标子评分，`Wi` 是当前规则场景权重。选择不同规则场景会影响两件事：物理范围与单位规则的字段匹配方式，以及九个指标汇总为总分时的权重。各指标子评分的计算公式保持一致。

自动识别默认权重：

- 平滑度检测：18%
- 时间序列自然性检测：16%
- 小数位/数字规律检测：13%
- 异常点分布检测：6%
- 传感器漂移检测：14%
- 变化点检测：6%
- 采样完整性检测：4%
- 物理范围与单位检测：4%
- 多变量相关性检测：19%

场景化权重：

| 场景 | 平滑 | 时序 | 数字 | 异常 | 漂移 | 变点 | 采样 | 物理 | 相关 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 自动识别 | 18% | 16% | 13% | 6% | 14% | 6% | 4% | 4% | 19% |
| 温室数据 | 16% | 18% | 8% | 8% | 16% | 10% | 8% | 6% | 10% |
| 虫害调查 | 10% | 8% | 14% | 12% | 8% | 14% | 8% | 14% | 12% |
| 产量调查 | 10% | 8% | 12% | 12% | 8% | 10% | 10% | 14% | 16% |
| 农残检测 | 8% | 6% | 16% | 12% | 6% | 10% | 8% | 20% | 14% |

风险等级：

- 70-100：低风险
- 50-69.99：中风险
- 0-49.99：高风险

## 注意事项

- 评分不是法律或审计结论，只是数据复核线索。
- 不同作物、设备和采样频率会影响指标表现，建议结合业务规则解释。
- 第一版没有使用深度学习模型，后续可以加入更多领域规则、设备元数据校验和人工复核流程。
