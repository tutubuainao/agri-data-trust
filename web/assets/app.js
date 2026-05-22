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
      loading: false,
      error: "",
    };
  },
  computed: {
    totalScore() {
      return this.result?.analysis?.total_score ?? "--";
    },
    riskLevel() {
      return this.result?.analysis?.risk_level ?? "等待分析";
    },
    scoreSubtitle() {
      if (!this.result) return "上传文件后自动生成评分";
      if (!this.result.ok) return "文件粗筛未发现可分析数值列";
      return "可信度评分越高，复核风险越低";
    },
    scoreStyle() {
      const score = Number(this.result?.analysis?.total_score || 0);
      const deg = Math.max(0, Math.min(100, score)) * 3.6;
      return { background: `conic-gradient(var(--green) ${deg}deg, var(--bar-track) 0deg)` };
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
      await this.request(`${basePath()}/api/analyze`, {
        method: "POST",
        body: form,
      });
      event.target.value = "";
    },
    async loadSample(kind) {
      await this.request(`${basePath()}/api/sample/${kind}`);
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
      } catch (exc) {
        this.error = exc.message || String(exc);
      } finally {
        this.loading = false;
      }
    },
  },
  mounted() {
    this.loadSample("real");
  },
}).mount("#app");
