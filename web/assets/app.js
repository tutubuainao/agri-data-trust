const { createApp } = Vue;

const indicatorCatalog = [
{
    key: "smoothness",
    label: "平滑度检测",
    short: "平滑",
    group: "默认核心指标",
    default: true,
    applicability: "适合连续测量值、产量测量值和农残浓度等数值列。",
    reason: "识别过度平滑、固定步长和变化率过稳的集体异常模式。",
  },
{
    key: "digit",
    label: "小数位/数字规律",
    short: "数字",
    group: "默认核心指标",
    default: true,
    applicability: "适合连续测量值和人工记录表；计数型整数列会自动放宽整数相关扣分。",
    reason: "检查整数比例、小数位、末位数字、固定刻度和重复值。",
  },
{
    key: "outlier",
    label: "异常点分布",
    short: "异常",
    group: "默认核心指标",
    default: true,
    applicability: "适合大多数数值列，完全没有异常点或异常点过多都会作为复核线索。",
    reason: "关注点级异常和自然波动，不把“过度干净”自动视为更可信。",
  },
{
    key: "physical",
    label: "有效性/物理范围与单位",
    short: "物理",
    group: "默认核心指标",
    default: true,
    applicability: "适合温度、湿度、降雨量、农残、产量、虫害计数等常见字段。",
    reason: "用可配置农业规则做有效性校验，提示超范围、疑似单位错用和规则覆盖不足。",
  },
{
    key: "sampling",
    label: "采样完整性",
    short: "采样",
    group: "可选质量指标",
    default: false,
    applicability: "适合连续采集、有明确时间列、多工作表或需要复核采样链路的数据；普通人工调查表可不默认启用。",
    reason: "复核文件结构、时间间隔、重复时间戳和连续缺测，但它更偏数据质量链路，不作为默认核心可信度证据。",
  },
{
    key: "timeseries",
    label: "时间序列自然性",
    short: "时序",
    group: "可选增强指标",
    default: false,
    applicability: "更适合按时间连续采集的数据，如温室环境、土壤墒情、气象传感器。",
    reason: "检查自相关、ACF、趋势反转和周期线索；与平滑度相关但不等价。",
  },
{
    key: "drift",
    label: "传感器漂移",
    short: "漂移",
    group: "可选增强指标",
    default: false,
    applicability: "建议用于同一设备长期连续采集的数据；人工调查表通常不需要。",
    reason: "识别基线缓慢偏移、前后窗口均值变化和 CUSUM 累积偏差。",
  },
{
    key: "changepoint",
    label: "变化点检测",
    short: "变点",
    group: "可选增强指标",
    default: false,
    applicability: "适合怀疑换设备、换批次、改采样条件或阶段性农情变化的数据。",
    reason: "关注段级均值/分布突变；与异常点分布有交集，但异常点偏点级，变化点偏阶段结构。",
  },
{
    key: "correlation",
    label: "多变量相关性",
    short: "相关",
    group: "可选增强指标",
    default: false,
    applicability: "至少有两个有业务含义的数值列时建议开启；单变量文件不需要。",
    reason: "检查 Pearson/Spearman 过强相关和近乎复制列。",
  },
{
    key: "ml_anomaly",
    label: "机器学习异常识别",
    short: "机器",
    group: "可选增强指标",
    default: false,
    applicability: "适合至少 20 行、至少 2 个有效数值特征的数据；无标签时作为辅助复核指标。",
    reason: "使用 IsolationForest、LocalOutlierFactor、One-Class SVM 做多变量行级无监督集成，作为异常点和相关性之外的辅助复核线索。",
  },
];

const labels = Object.fromEntries(indicatorCatalog.map((item) => [item.key, [item.label, item.short]]));
const defaultIndicators = indicatorCatalog.filter((item) => item.default).map((item) => item.key);
const STORAGE_KEY = "agri-trust-last-result";

const chartHelp = [
  {
    token: "smoothness",
    title: "平滑度走势",
    description: "展示某个数值列按样本顺序的变化轨迹，用来观察是否长期过于平直、固定步长或缺少自然波动。",
  },
  {
    token: "acf",
    title: "自相关 ACF",
    description: "展示当前列与前面若干滞后样本之间的相关性，用来判断时间序列是否具有合理的连续性、趋势衰减或周期线索。",
  },
  {
    token: "digits",
    title: "末位数字分布",
    description: "统计数值最后一位有效数字 0-9 的出现次数。计数型整数列会按调查计数规则降权，避免把天然整数误判为过度整齐。",
  },
  {
    token: "outlier",
    title: "异常点扫描",
    description: "展示数值序列的整体波动形态，用来辅助理解 z-score、IQR 和 IsolationForest 检出的异常点比例是否合理。",
  },
  {
    token: "drift",
    title: "传感器漂移扫描",
    description: "观察数值基线是否随样本顺序持续偏移，用来提示设备校准变化、长期基线迁移或真实农情趋势。",
  },
  {
    token: "changepoint",
    title: "变化点扫描",
    description: "标记疑似阶段性突变位置，用来复核设备校准、采样条件变化或人工分段处理痕迹。",
  },
  {
    token: "correlation",
    title: "相关性热力图",
    description: "展示合格数值列两两之间的 Pearson 相关系数，用来识别过强相关、近似复制列或完美线性关系。",
  },
  {
    token: "ml_anomaly",
    title: "机器学习异常比例",
    description: "展示多个无监督机器学习模型识别出的异常样本比例，以及多个模型共同判为异常的样本比例。",
  },
];

function basePath() {
  return window.location.pathname.startsWith("/agri-trust") ? "/agri-trust" : "";
}

function uploadPath() {
  return `${basePath()}/` || "/";
}

function resultPath() {
  return `${basePath()}/result` || "/result";
}

function replaceRoute(path) {
  if (window.location.pathname !== path) {
    window.history.replaceState({}, "", path);
  }
}

function pushRoute(path) {
  if (window.location.pathname !== path) {
    window.history.pushState({}, "", path);
  }
}

createApp({
  data() {
    return {
      result: null,
      stats: null,
      loading: false,
      error: "",
      progress: 0,
      progressText: "",
      progressTimer: null,
      alertMessage: "",
      navOpen: false,
      scenario: "auto",
      customIndicators: false,
      selectedIndicators: [...defaultIndicators],
      indicatorCatalog,
      scenarioOptions: [
        { value: "auto", label: "自动识别", description: "通用农业规则，默认只启用最关键的 4 个核心可信度指标" },
        { value: "greenhouse", label: "温室数据", description: "物理规则更偏向温室环境字段；自定义时可开启时序、漂移和变化点" },
        { value: "pest", label: "虫害调查", description: "物理规则更偏向卵量、幼虫、成虫、诱捕量和寄生率" },
        { value: "yield", label: "产量调查", description: "物理规则更偏向产量、面积、株高、重量等非负农艺指标" },
        { value: "residue", label: "农残检测", description: "物理规则更偏向农药残留、浓度、含量和检出限等字段" },
      ],
    };
  },
  computed: {
    hasResult() {
      return Boolean(this.result);
    },
    hasAnalysis() {
      return Boolean(this.result?.ok);
    },
    totalScore() {
      if (this.result && !this.result.ok) return "未识别";
      return this.result?.analysis?.total_score ?? "--";
    },
    riskLevel() {
      if (this.result && !this.result.ok) return "无法评分";
      return this.result?.analysis?.risk_level ?? "等待上传";
    },
    riskClass() {
      if (this.result && !this.result.ok) return "risk-blocked";
      const level = this.riskLevel;
      if (level.includes("高")) return "risk-high";
      if (level.includes("中")) return "risk-medium";
      if (level.includes("低")) return "risk-low";
      return "risk-idle";
    },
    scoreStyle() {
      const score = Number(this.result?.analysis?.total_score || 0);
      const deg = Math.max(0, Math.min(100, score)) * 3.6;
      return { background: `conic-gradient(var(--risk-color) ${deg}deg, var(--bar-track) 0deg)` };
    },
    selectedScenarioLabel() {
      return this.scenarioOptions.find((item) => item.value === this.scenario)?.label || "自动识别";
    },
    selectedScenarioDescription() {
      return this.scenarioOptions.find((item) => item.value === this.scenario)?.description || "";
    },
    coreIndicatorOptions() {
      return this.indicatorCatalog.filter((item) => item.default);
    },
    optionalIndicatorOptions() {
      return this.indicatorCatalog.filter((item) => !item.default);
    },
    selectedIndicatorNames() {
      return this.selectedIndicators
        .map((key) => this.indicatorCatalog.find((item) => item.key === key)?.label || key)
        .join("、");
    },
    selectionModeText() {
      return this.customIndicators ? "自定义指标" : "默认核心指标";
    },
    subScoreItems() {
      const scores = this.result?.analysis?.sub_scores || {};
      const weights = this.result?.analysis?.weights || {};
      const order = this.result?.analysis?.selected_indicators || Object.keys(scores);
      return order
        .filter((key) => scores[key] !== undefined)
        .map((key) => {
          const [label, short] = labels[key] || [key, key];
          return {
            key,
            label,
            short,
            score: Math.round(scores[key]?.score ?? 0),
            risk: scores[key]?.risk_level ?? "待检测",
            weight: weights[key] ?? null,
          };
        });
    },
    weightItems() {
      const weights = this.result?.analysis?.weights || {};
      const order = this.result?.analysis?.selected_indicators || Object.keys(weights);
      return order
        .filter((key) => weights[key] !== undefined)
        .map((key) => ({ key, label: labels[key]?.[0] || key, weight: weights[key] }));
    },
    chartUrls() {
      if (!this.result?.ok) return [];
      const charts = [];
      Object.values(this.result.analysis.column_results || {}).forEach((checks) => {
        Object.values(checks).forEach((check) => charts.push(...(check.charts || [])));
      });
      Object.values(this.result.analysis.dataset_results || {}).forEach((check) => {
        charts.push(...(check.charts || []));
      });
      charts.push(...(this.result.analysis.correlation?.charts || []));
      return charts.slice(0, 12);
    },
    chartItems() {
      return this.chartUrls.map((url) => {
        const lower = url.toLowerCase();
        const meta = chartHelp.find((item) => lower.includes(item.token)) || {
          title: "检测图表",
          description: "用于辅助查看数据质量与可疑风险线索。",
        };
        return { url, ...meta };
      });
    },
    sheetMergeText() {
      const used = this.result?.profile?.used_sheets || [];
      const skipped = this.result?.profile?.skipped_sheets || [];
      const strategy = this.result?.profile?.sheet_strategy || {};
      if (!used.length && !skipped.length) return "";
      const parts = [];
      if (strategy.mode === "separate") {
        parts.push(`系统识别到 ${used.length} 个非空工作表：${used.join("、")}。`);
        parts.push("这些工作表字段结构差异较大，系统已分工作表评价，再按有效行数加权汇总总分，避免把不同调查表强行合并。");
      } else if (used.length > 1) {
        parts.push(`系统识别到 ${used.length} 个非空工作表：${used.join("、")}。`);
        parts.push("这些工作表字段结构相近，已按行纵向合并评价；合并时保留工作表来源字段，并按列名对齐。");
      } else if (used.length === 1) {
        parts.push(`系统识别到 1 个可分析工作表：${used[0]}。`);
      }
      if (skipped.length) parts.push(`空工作表已忽略且不参与评分：${skipped.join("、")}。`);
      return parts.join("");
    },
    sheetAnalysisItems() {
      return this.result?.analysis?.sheet_analysis?.items || [];
    },
    datasetCheckItems() {
      return Object.entries(this.result?.analysis?.dataset_results || {}).map(([key, item]) => ({
        key,
        label: item.label,
        score: Math.round(item.score ?? 0),
        reasons: item.reasons || [],
        metrics: item.metrics || {},
      }));
    },
    previewRows() {
      return this.result?.preview || [];
    },
    previewColumns() {
      const seen = new Set();
      this.previewRows.forEach((row) => {
        Object.keys(row || {}).forEach((key) => seen.add(key));
      });
      return Array.from(seen);
    },
  },
  methods: {
    pct(value) {
      return `${Math.round((Number(value) || 0) * 10000) / 100}%`;
    },
    scoreColor(score) {
      const value = Number(score) || 0;
      if (value >= 70) return "linear-gradient(90deg, #16794f, #36d399)";
      if (value >= 50) return "linear-gradient(90deg, #a66f16, #e5b85f)";
      return "linear-gradient(90deg, #c2413a, #ff6b6b)";
    },
    indicatorMeta(key) {
      return this.indicatorCatalog.find((item) => item.key === key) || { label: key, short: key };
    },
    isIndicatorSelected(key) {
      return this.selectedIndicators.includes(key);
    },
    toggleIndicator(key) {
      if (!this.customIndicators) return;
      if (this.selectedIndicators.includes(key)) {
        if (this.selectedIndicators.length <= 1) return;
        this.selectedIndicators = this.selectedIndicators.filter((item) => item !== key);
      } else {
        this.selectedIndicators = [...this.selectedIndicators, key];
      }
    },
    resetIndicators() {
      this.selectedIndicators = [...defaultIndicators];
      this.customIndicators = false;
    },
    async handleUpload(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      const form = new FormData();
      form.append("file", file);
      form.append("scenario", this.scenario);
      form.append("custom_indicators", this.customIndicators ? "true" : "false");
      form.append("indicators", this.selectedIndicators.join(","));
      this.startProgress("正在上传文件...");
      await this.request(`${basePath()}/api/analyze`, {
        method: "POST",
        body: form,
      });
      event.target.value = "";
    },
    startProgress(text) {
      this.stopProgress();
      this.progress = 8;
      this.progressText = text;
      this.alertMessage = "";
      this.progressTimer = window.setInterval(() => {
        if (this.progress < 35) {
          this.progress += 7;
          this.progressText = "正在识别工作表和字段...";
        } else if (this.progress < 68) {
          this.progress += 5;
          this.progressText = "正在执行所选可信度指标...";
        } else if (this.progress < 92) {
          this.progress += 2;
          this.progressText = "正在生成图表、网页报告和 PDF 报告...";
        }
      }, 260);
    },
    stopProgress() {
      if (this.progressTimer) {
        window.clearInterval(this.progressTimer);
        this.progressTimer = null;
      }
    },
    async request(url, options = {}) {
      this.loading = true;
      this.error = "";
      try {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "请求失败");
        }
        this.result = data;
        if (data.stats) this.stats = data.stats;
        this.persistResult(data);
        if (!data.ok) {
          this.alertMessage = "未识别到可分析的数值列，请检查数据后重新提交。";
        }
        this.progress = 100;
        this.progressText = "分析完成";
        pushRoute(resultPath());
        this.$nextTick(() => {
          window.scrollTo({ top: 0, behavior: "smooth" });
        });
      } catch (exc) {
        this.error = exc.message || String(exc);
        this.progressText = "分析失败";
      } finally {
        this.loading = false;
        this.stopProgress();
        window.setTimeout(() => {
          if (!this.loading) this.progress = 0;
        }, 900);
      }
    },
    async loadStats() {
      try {
        const response = await fetch(`${basePath()}/api/stats`);
        if (response.ok) this.stats = await response.json();
      } catch (_) {
        this.stats = null;
      }
    },
    persistResult(data) {
      try {
        window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      } catch (_) {
        window.sessionStorage.removeItem(STORAGE_KEY);
      }
    },
    restoreResult() {
      try {
        const raw = window.sessionStorage.getItem(STORAGE_KEY);
        if (raw) this.result = JSON.parse(raw);
      } catch (_) {
        window.sessionStorage.removeItem(STORAGE_KEY);
      }
    },
    clearResult() {
      this.navOpen = false;
      this.result = null;
      this.error = "";
      this.alertMessage = "";
      this.progress = 0;
      this.progressText = "";
      this.stopProgress();
      try {
        window.sessionStorage.removeItem(STORAGE_KEY);
      } catch (_) {
        // 页面仍然可以返回上传入口，存储清理失败不阻断交互。
      }
      this.$nextTick(() => {
        pushRoute(uploadPath());
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    },
    clearAlert() {
      this.alertMessage = "";
    },
    previewValue(row, column) {
      const value = row?.[column];
      if (value === null || value === undefined || value === "") return "—";
      if (typeof value === "object") return JSON.stringify(value);
      return String(value);
    },
    displayColumnName(column) {
      return column === "__sheet__" ? "工作表来源" : column;
    },
    _setupRevealObserver() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      this._revealObs = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              this._revealObs.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.08, rootMargin: "0px 0px -18px 0px" }
      );
      this._observeRevealElements();
    },
    _observeRevealElements() {
      if (!this._revealObs) return;
      document.querySelectorAll(".reveal:not(.visible)").forEach((el) => this._revealObs.observe(el));
    },
  },
  mounted() {
    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch (_) {
      // 不影响页面正常使用。
    }
    if (window.location.pathname.endsWith("/result")) {
      replaceRoute(uploadPath());
    }
    window.addEventListener("popstate", () => {
      if (!window.location.pathname.endsWith("/result")) {
        this.result = null;
        this.error = "";
        this.alertMessage = "";
        this.progress = 0;
        this.progressText = "";
      }
    });
    this.loadStats();
    this._setupRevealObserver();
  },
  watch: {
    result() {
      this.$nextTick(() => this._observeRevealElements());
    },
  },
}).mount("#app");
