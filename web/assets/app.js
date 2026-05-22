const { createApp } = Vue;

const labels = {
  smoothness: ["平滑度检测", "平滑"],
  timeseries: ["时间序列自然性", "时序"],
  digit: ["小数位/数字规律", "数字"],
  outlier: ["异常点分布", "异常"],
  correlation: ["多变量相关性", "相关"],
};

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
    };
  },
  computed: {
    totalScore() {
      return this.result?.analysis?.total_score ?? "--";
    },
    riskLevel() {
      return this.result?.analysis?.risk_level ?? "等待分析";
    },
    riskClass() {
      const level = this.riskLevel;
      if (level.includes("高")) return "risk-high";
      if (level.includes("中")) return "risk-medium";
      if (level.includes("低")) return "risk-low";
      return "risk-idle";
    },
    scoreSubtitle() {
      if (!this.result) return "上传文件后自动生成评分";
      if (!this.result.ok) return "文件粗筛未发现可分析数值列";
      return "可信度评分越高，复核风险越低";
    },
    scoreStyle() {
      const score = Number(this.result?.analysis?.total_score || 0);
      const deg = Math.max(0, Math.min(100, score)) * 3.6;
      return { background: `conic-gradient(var(--risk-color) ${deg}deg, var(--bar-track) 0deg)` };
    },
    subScoreItems() {
      const scores = this.result?.analysis?.sub_scores || {};
      return Object.entries(labels).map(([key, [label, short]]) => ({
        key,
        label,
        short,
        score: Math.round(scores[key]?.score ?? 0),
        risk: scores[key]?.risk_level ?? "待检测",
      }));
    },
    chartUrls() {
      if (!this.result?.ok) return [];
      const charts = [];
      Object.values(this.result.analysis.column_results || {}).forEach((checks) => {
        Object.values(checks).forEach((check) => charts.push(...(check.charts || [])));
      });
      charts.push(...(this.result.analysis.correlation?.charts || []));
      return charts.slice(0, 12);
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
      this.startProgress("正在上传文件...");
      await this.request(`${basePath()}/api/analyze`, {
        method: "POST",
        body: form,
      });
      event.target.value = "";
    },
    async loadSample(kind) {
      this.startProgress("正在加载示例数据...");
      await this.request(`${basePath()}/api/sample/${kind}`);
    },
    startProgress(text) {
      this.stopProgress();
      this.progress = 8;
      this.progressText = text;
      this.progressTimer = window.setInterval(() => {
        if (this.progress < 35) {
          this.progress += 7;
          this.progressText = "正在识别 sheet 和字段...";
        } else if (this.progress < 68) {
          this.progress += 5;
          this.progressText = "正在执行五类可信度检测...";
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
  },
  mounted() {
    this.loadStats();
    this.loadSample("real");
  },
}).mount("#app");
