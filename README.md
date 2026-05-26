# 农业原始数据可信度检测系统 MVP

这是一个可直接运行的 Python/FastAPI MVP，用于对农业原始数据进行可信度风险检测。系统不会判断“数据一定是假的”，只输出可信度评分、风险等级和可解释的可疑原因。当前线上版使用 FastAPI 提供算法接口，前端使用 Vue 页面呈现。

## 功能

- 支持上传 CSV、XLSX、XLS 文件
- 自动识别时间列和数值列；没有时间列时按原始行顺序分析
- 上传后先执行文件粗筛，解释常量列、文本列、日期列和缺失列的处理方式
- 默认启用 5 个核心指标，支持按数据类型自定义开启增强指标
- 支持采样完整性、物理范围与单位异常、规则场景配置
- 可选执行时间序列自然性、传感器漂移、变化点、多变量相关性和机器学习异常识别
- 输出 0-100 总可信度评分、所选指标子评分、风险等级和解释
- FastAPI 接口调用核心算法，Vue 前端展示结果
- 生成 HTML 和 PDF 检测报告
- 提供“评分标准与实现原理”说明页，解释评分等级、公式、依赖库和缺失值处理规则
- 输出趋势图、ACF 图、末位数字分布图、异常点扫描图、传感器漂移扫描图、变化点扫描图和相关性热力图

## 指标结构

默认核心指标：

1. 采样完整性检测：时间间隔 CV、重复时间戳、断点数量、连续缺测、sheet 结构异常
2. 平滑度检测：一阶差分、rolling variance、变化率稳定性
3. 小数位/数字规律检测：整数比例、小数位分布、末位数字分布、重复值模式；计数型农业调查列会按整数计数规则降权
4. 异常点分布检测：z-score、IQR、IsolationForest；完全没有异常点也会提示风险
5. 物理范围与单位异常检测：按温室、虫害、产量、农残等场景匹配规则

可选增强指标：

1. 时间序列自然性检测：autocorrelation、ACF、趋势变化、方向变化
2. 传感器漂移检测：前后窗口均值、滚动均值斜率、CUSUM、方差变化、变化方向单一性
3. 变化点检测：CUSUM、Page-Hinkley、滑动窗口均值差异
4. 多变量相关性检测：Pearson、Spearman、相关矩阵、近完美相关变量对
5. 机器学习异常识别：IsolationForest、LocalOutlierFactor、One-Class SVM 多变量行级无监督集成，作为辅助复核指标

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

浏览器打开 `http://127.0.0.1:8501/agri-trust/` 后，可以上传自己的 CSV/Excel 文件。页面不会默认分析示例数据；需要测试时可上传 `data/` 目录中的示例文件。

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
│   ├── indicator_config.py
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
│   ├── ml_detection.py
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

系统采用规则型评分，第一版优先保证可运行、可解释、易调整。总分由本次启用的指标加权得到：

```text
S = Σ(Wi × Si)
```

其中 `Si` 是本次启用指标的子评分，`Wi` 是当前规则场景下该指标的归一化权重。未启用的可选指标不会进入总分。

权重不是固定写死的百分比。系统先按规则场景给每个指标一个相对权重系数 `Ri`，再只对本次实际选择的指标归一化：

```text
Wi = Ri / ΣRj
```

其中 `j` 只遍历本次实际启用的指标。用户自定义加入机器学习、相关性等可选指标后，所有已选指标会重新分配权重；未勾选的指标不参与总分。

自动识别默认核心权重：

- 采样完整性：20.2%
- 平滑度检测：22.9%
- 小数位/数字规律：19.3%
- 异常点分布：19.3%
- 物理范围与单位：18.3%

默认核心指标场景化权重：

| 场景 | 采样 | 平滑 | 数字 | 异常 | 物理 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 自动识别 | 20.2% | 22.9% | 19.3% | 19.3% | 18.3% |
| 温室数据 | 23.7% | 23.7% | 14.0% | 19.4% | 19.4% |
| 虫害调查 | 21.1% | 12.6% | 23.2% | 21.1% | 22.1% |
| 产量调查 | 21.5% | 15.1% | 20.4% | 20.4% | 22.6% |
| 农残检测 | 18.6% | 11.3% | 23.7% | 20.6% | 25.8% |

风险等级：

- 70-100：低风险
- 50-69.99：中风险
- 0-49.99：高风险

## 注意事项

- 评分不是法律或审计结论，只是数据复核线索。
- 不同作物、设备和采样频率会影响指标表现，建议结合业务规则解释。
- 当前机器学习指标是无监督辅助复核，不等同于真伪分类器；后续积累标注数据后，可再加入监督学习或深度时序模型。
- 机器学习指标与异常点分布有交集：异常点分布是单列点级检测，机器学习是多列组合后的行级检测。两者同时异常时，应作为同一风险的不同侧面复核，不要简单当成两份完全独立证据。
