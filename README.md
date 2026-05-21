# 农业原始数据可信度检测系统 MVP

这是一个可直接运行的 Python/Streamlit MVP，用于对农业原始数据进行可信度风险检测。系统不会判断“数据一定是假的”，只输出可信度评分、风险等级和可解释的可疑原因。

## 功能

- 支持上传 CSV、XLSX、XLS 文件
- 自动识别时间列和数值列；没有时间列时按原始行顺序分析
- 对每个数值列执行四类单变量检测
- 对所有数值列执行多变量相关性检测
- 输出 0-100 总可信度评分、五项子评分、风险等级和解释
- 生成 HTML 检测报告
- 输出趋势图、ACF 图、尾数分布图、异常点扫描图和相关性热力图

## 五类指标

1. 平滑度检测：一阶差分、rolling variance、变化率稳定性
2. 时间序列自然性检测：autocorrelation、ACF、趋势变化、方向变化
3. 小数位/数字规律检测：整数比例、小数位分布、尾数分布、重复值模式
4. 异常点分布检测：z-score、IQR、IsolationForest；完全没有异常点也会提示风险
5. 多变量相关性检测：Pearson、Spearman、相关矩阵、近完美相关变量对

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
streamlit run app.py
```

浏览器打开 Streamlit 提供的本地地址后，可以上传自己的 CSV/Excel 文件，也可以点击页面按钮加载示例数据。

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
├── requirements.txt
├── README.md
├── data/
│   ├── sample_real.csv
│   └── sample_fake.csv
├── src/
│   ├── loader.py
│   ├── profiler.py
│   ├── smoothness.py
│   ├── timeseries.py
│   ├── digit_analysis.py
│   ├── outlier.py
│   ├── correlation.py
│   ├── scoring.py
│   ├── report.py
│   └── utils.py
└── reports/
```

## 评分说明

系统采用规则型评分，第一版优先保证可运行、可解释、易调整。总分由五个子指标加权得到：

- 平滑度检测：22%
- 时间序列自然性检测：22%
- 小数位/数字规律检测：18%
- 异常点分布检测：18%
- 多变量相关性检测：20%

风险等级：

- 70-100：低风险
- 50-69.99：中风险
- 0-49.99：高风险

## 注意事项

- 评分不是法律或审计结论，只是数据复核线索。
- 不同作物、设备和采样频率会影响指标表现，建议结合业务规则解释。
- 第一版没有使用深度学习模型，后续可以加入更多领域规则、设备元数据校验和人工复核流程。
