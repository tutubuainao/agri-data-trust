const { createApp } = Vue;

const labels = {
  smoothness: ["平滑度检测", "平滑"],
  timeseries: ["时间序列自然性", "时序"],
  digit: ["小数位/数字规律", "数字"],
  outlier: ["异常点分布", "异常"],
  drift: ["传感器漂移", "漂移"],
  changepoint: ["变化点检测", "变点"],
  sampling: ["采样完整性", "采样"],
  physical: ["物理范围/单位", "物理"],
  correlation: ["多变量相关性", "相关"],
};

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
];

function basePath() {
  return window.location.pathname.startsWith("/agri-trust") ? "/agri-trust" : "";
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
      scenario: "auto",
      scenarioOptions: [
        { value: "auto", label: "自动识别", description: "通用农业规则，九类指标采用均衡默认权重" },
        { value: "greenhouse", label: "温室数据", description: "强化时序、漂移、变化点和采样完整性，适合连续传感器" },
        { value: "pest", label: "虫害调查", description: "强化计数/比例、物理规则、变化点和异常点，适合调查表" },
        { value: "yield", label: "产量调查", description: "强化物理范围、相关性、采样完整性和农艺非负规则" },
        { value: "residue", label: "农残检测", description: "强化物理范围、数字精度、异常点和浓度非负规则" },
      ],
    };
  },
  computed: {
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
    scoreSubtitle() {
      if (!this.result) return "请先上传 CSV、XLSX 或 XLS 文件";
      if (!this.result.ok) return "未识别到可分析的数值列，请检查数据后重新提交";
      return "可信度评分越高，复核风险越低";
    },
    scoreStyle() {
      const score = Number(this.result?.analysis?.total_score || 0);
      const deg = Math.max(0, Math.min(100, score)) * 3.6;
      return { background: `conic-gradient(var(--risk-color) ${deg}deg, var(--bar-track) 0deg)` };
    },
    subScoreItems() {
      const scores = this.result?.analysis?.sub_scores || {};
      const weights = this.result?.analysis?.weights || {};
      return Object.entries(labels).map(([key, [label, short]]) => ({
        key,
        label,
        short,
        score: Math.round(scores[key]?.score ?? 0),
        risk: scores[key]?.risk_level ?? "待检测",
        weight: weights[key] ?? null,
      }));
    },
    weightItems() {
      const weights = this.result?.analysis?.weights || {};
      return Object.entries(labels)
        .map(([key, [label]]) => ({ key, label, weight: weights[key] }))
        .filter((item) => item.weight !== undefined);
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
      if (!used.length && !skipped.length) return "";
      const parts = [];
      if (used.length > 1) {
        parts.push(`系统已将 ${used.length} 个非空 sheet 按行纵向合并：${used.join("、")}。`);
        parts.push("合并时保留 sheet 来源字段，并按列名对齐；某个 sheet 没有的字段会留空，再由粗筛和缺失值逻辑处理。");
      } else if (used.length === 1) {
        parts.push(`系统识别到 1 个可分析 sheet：${used[0]}。`);
      }
      if (skipped.length) parts.push(`空 sheet 已跳过：${skipped.join("、")}。`);
      return parts.join("");
    },
    selectedScenarioLabel() {
      return this.scenarioOptions.find((item) => item.value === this.scenario)?.label || "自动识别";
    },
    selectedScenarioDescription() {
      return this.scenarioOptions.find((item) => item.value === this.scenario)?.description || "";
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
    async handleUpload(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      const form = new FormData();
      form.append("file", file);
      form.append("scenario", this.scenario);
      this.startProgress("正在上传文件...");
      await this.request(`${basePath()}/api/analyze`, {
        method: "POST",
        body: form,
      });
      event.target.value = "";
    },
    async loadSample(kind) {
      this.startProgress("正在加载示例数据...");
      await this.request(`${basePath()}/api/sample/${kind}?scenario=${encodeURIComponent(this.scenario)}`);
    },
    startProgress(text) {
      this.stopProgress();
      this.progress = 8;
      this.progressText = text;
      this.alertMessage = "";
      this.progressTimer = window.setInterval(() => {
        if (this.progress < 35) {
          this.progress += 7;
          this.progressText = "正在识别 sheet 和字段...";
        } else if (this.progress < 68) {
          this.progress += 5;
          this.progressText = "正在执行九类可信度检测...";
        } else if (this.progress < 92) {
          this.progress += 2;
          this.progressText = "正在生成图表和报告...";
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
    clearAlert() {
      this.alertMessage = "";
    },
    previewValue(row, column) {
      const value = row?.[column];
      if (value === null || value === undefined || value === "") return "—";
      if (typeof value === "object") return JSON.stringify(value);
      return String(value);
    },
  },
  mounted() {
    this.restoreResult();
    this.loadStats();
  },
}).mount("#app");
