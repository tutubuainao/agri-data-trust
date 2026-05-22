<?php
define('WP_USE_THEMES', false);
require '/www/wwwroot/39.106.238.181/wp-load.php';

$preview_url = content_url('/uploads/2026/05/agri-trust-preview.png');
$agri_url = home_url('/agri-trust/');
$method_url = home_url('/agri-trust/methodology');
$bio_url = get_permalink(51) ?: home_url('/index.php/%e4%b8%aa%e4%ba%ba%e7%ae%80%e4%bb%8b/');
$ppt_url = get_permalink(17) ?: home_url('/');

$css = <<<CSS
body.home .entry-title,
body.page-id-59 .entry-title {
  display: none !important;
}
body.home .site-content .ast-container,
body.page-id-59 .site-content .ast-container {
  max-width: 100% !important;
  padding-left: 0 !important;
  padding-right: 0 !important;
}
body.home .content-area.primary,
body.page-id-59 .content-area.primary {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}
body.home .ast-separate-container .ast-article-single,
body.page-id-59 .ast-separate-container .ast-article-single,
body.home .entry-content,
body.page-id-59 .entry-content {
  padding: 0 !important;
  margin: 0 !important;
}
.portfolio-home {
  --ph-ink: #111827;
  --ph-muted: #5f6f66;
  --ph-line: #d9e1dc;
  --ph-green: #14532d;
  --ph-green-soft: #eaf6ef;
  --ph-gold: #a66f16;
  --ph-bg: #f5f8f5;
  --ph-card: #ffffff;
  color: var(--ph-ink);
  background: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}
.portfolio-home,
.portfolio-home * {
  box-sizing: border-box;
  letter-spacing: 0;
}
.portfolio-home a {
  color: inherit;
}
.ph-container {
  width: min(1180px, calc(100% - 44px));
  margin: 0 auto;
}
.ph-hero {
  display: flex;
  align-items: center;
  background: linear-gradient(180deg, #ffffff 0%, #f4f8f5 100%);
  border-bottom: 1px solid var(--ph-line);
}
.ph-hero-grid {
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
  gap: 42px;
  align-items: center;
  padding: 34px 0 54px;
}
.ph-eyebrow {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid #bfd4c6;
  border-radius: 999px;
  color: var(--ph-green);
  background: var(--ph-green-soft);
  font-weight: 760;
  font-size: 0.92rem;
}
.ph-hero h1 {
  margin: 20px 0 0;
  font-size: clamp(2.45rem, 4.8vw, 4.35rem);
  line-height: 1.06;
  font-weight: 880;
}
.ph-lead {
  max-width: 720px;
  margin: 22px 0 0;
  color: var(--ph-muted);
  font-size: 1.1rem;
  line-height: 1.86;
}
.ph-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}
.ph-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: 0 18px;
  border-radius: 8px;
  text-decoration: none !important;
  font-weight: 780;
  border: 1px solid transparent;
}
.ph-button-primary {
  color: #ffffff !important;
  background: var(--ph-green);
  box-shadow: 0 14px 28px rgba(20, 83, 45, 0.16);
}
.ph-button-secondary {
  color: #153323 !important;
  background: #ffffff;
  border-color: #bdd0c4;
}
.ph-product {
  position: relative;
  border: 1px solid #cedbd3;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 24px 70px rgba(15, 36, 26, 0.12);
  padding: 14px;
}
.ph-product-top {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 28px;
  padding: 0 4px 10px;
}
.ph-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #d3ded7;
}
.ph-dot:nth-child(1) { background: #ef9a9a; }
.ph-dot:nth-child(2) { background: #f0c36a; }
.ph-dot:nth-child(3) { background: #6fcf97; }
.ph-product img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 8px;
  border: 1px solid #e1e7e3;
}
.ph-score-card {
  position: absolute;
  right: 28px;
  bottom: 28px;
  width: min(260px, 46%);
  border: 1px solid rgba(255, 255, 255, 0.66);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  padding: 16px;
  box-shadow: 0 18px 42px rgba(15, 36, 26, 0.15);
}
.ph-score-card span {
  color: var(--ph-muted);
  font-size: 0.86rem;
}
.ph-score-card strong {
  display: block;
  margin-top: 4px;
  color: var(--ph-green);
  font-size: 2rem;
  line-height: 1;
}
.ph-section {
  padding: 72px 0;
}
.ph-section-soft {
  background: var(--ph-bg);
  border-top: 1px solid var(--ph-line);
}
.ph-section-head {
  max-width: 780px;
  margin-bottom: 30px;
}
.ph-section-head h2 {
  margin: 0;
  font-size: clamp(1.78rem, 3vw, 2.55rem);
  line-height: 1.18;
  font-weight: 840;
}
.ph-section-head p {
  margin: 12px 0 0;
  color: var(--ph-muted);
  line-height: 1.78;
  font-size: 1.04rem;
}
.ph-project-grid {
  display: grid;
  grid-template-columns: 1.08fr 0.92fr;
  gap: 22px;
  align-items: stretch;
}
.ph-panel,
.ph-next-card {
  border: 1px solid var(--ph-line);
  border-radius: 12px;
  background: #ffffff;
  padding: 28px;
  text-decoration: none !important;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
}
.ph-next-card[href]:hover {
  transform: translateY(-3px);
  border-color: #b9cdbf;
  box-shadow: 0 18px 40px rgba(17, 24, 39, 0.08);
}
.ph-panel h3,
.ph-next-card h3 {
  margin: 0 0 10px;
  font-size: 1.45rem;
  line-height: 1.3;
}
.ph-panel p,
.ph-next-card p {
  margin: 0;
  color: var(--ph-muted);
  line-height: 1.76;
}
.ph-feature-list {
  display: grid;
  gap: 12px;
  margin-top: 22px;
}
.ph-feature-list div {
  display: grid;
  grid-template-columns: 34px 1fr;
  gap: 12px;
  align-items: start;
}
.ph-feature-list b {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  color: var(--ph-green);
  background: var(--ph-green-soft);
}
.ph-feature-list span {
  color: var(--ph-muted);
  line-height: 1.68;
}
.ph-tech {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}
.ph-tech span {
  padding: 8px 12px;
  border: 1px solid #cbd9d0;
  border-radius: 999px;
  background: #ffffff;
  color: #254235;
  font-weight: 700;
  font-size: 0.92rem;
}
.ph-next-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}
.ph-next-card {
  min-height: 210px;
}
.ph-next-card small {
  display: inline-flex;
  margin-bottom: 12px;
  color: var(--ph-green);
  font-weight: 800;
}
.ph-final {
  background: #101d17;
  color: #ffffff;
  padding: 56px 0;
}
.ph-final .ph-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.ph-final h2 {
  margin: 0;
  color: #ffffff;
  font-size: 2rem;
}
.ph-final p {
  margin: 10px 0 0;
  color: #cddbd2;
}
@media (max-width: 920px) {
  .ph-container {
    width: min(100% - 36px, 1180px);
  }
  .ph-hero-grid,
  .ph-project-grid,
  .ph-next-grid {
    grid-template-columns: 1fr;
  }
  .ph-hero-grid {
    padding: 22px 0 36px;
  }
  .ph-score-card {
    position: static;
    width: 100%;
    margin-top: 12px;
  }
  .ph-final .ph-container {
    display: block;
  }
  .ph-final .ph-actions {
    margin-top: 22px;
  }
}
CSS;

$content = <<<HTML
<main class="portfolio-home">
  <section class="ph-hero">
    <div class="ph-container ph-hero-grid">
      <div>
        <span class="ph-eyebrow">个人作品集 · 可运行数据项目</span>
        <h1>农业数据可信度分析与数据质量评估</h1>
        <p class="ph-lead">这是一个以项目展示为核心的主页。当前重点项目是农业原始数据可信度检测系统：用户上传 CSV 或 Excel 后，系统会给出可信度评分、风险解释、图表和 HTML 报告。</p>
        <div class="ph-actions">
          <a class="ph-button ph-button-primary" href="$agri_url" target="_blank" rel="noopener">进入在线检测系统</a>
          <a class="ph-button ph-button-secondary" href="$method_url" target="_blank" rel="noopener">查看评分标准与实现原理</a>
        </div>
      </div>
      <div class="ph-product" aria-label="农业数据可信度检测系统界面预览">
        <div class="ph-product-top"><i class="ph-dot"></i><i class="ph-dot"></i><i class="ph-dot"></i></div>
        <img src="$preview_url" alt="农业数据可信度检测系统界面预览">
        <div class="ph-score-card">
          <span>示例可信度评分</span>
          <strong>82/100</strong>
        </div>
      </div>
    </div>
  </section>

  <section class="ph-section">
    <div class="ph-container">
      <div class="ph-project-grid">
        <article class="ph-panel">
          <div class="ph-section-head">
            <h2>当前重点项目</h2>
            <p>这个区域用于展示当前最重要的可运行项目。后续如果加入新的项目，可以继续向下扩展项目卡片，而不是把入口堆在页面顶部。</p>
          </div>
          <h3>农业原始数据可信度检测系统 MVP</h3>
          <p>系统自动识别时间列和数值列，对平滑度、时间序列自然性、数字规律、异常点分布和多变量相关性进行检测。它不会判断数据一定为假，只输出可信度评分和可疑风险，方便人工复核。</p>
          <div class="ph-actions">
            <a class="ph-button ph-button-primary" href="$agri_url" target="_blank" rel="noopener">打开项目</a>
            <a class="ph-button ph-button-secondary" href="$method_url" target="_blank" rel="noopener">评分标准</a>
          </div>
          <div class="ph-tech">
            <span>Python</span><span>FastAPI</span><span>Vue</span><span>pandas</span><span>scikit-learn</span><span>statsmodels</span>
          </div>
        </article>
        <aside class="ph-panel">
          <h3>项目能力点</h3>
          <div class="ph-feature-list">
            <div><b>1</b><span>文件粗筛：跳过文本列、日期辅助列和常量列，避免不同 CSV 列结构导致系统不可用。</span></div>
            <div><b>2</b><span>可解释评分：每个指标都有原因解释，不做“数据一定是假”的绝对判断。</span></div>
            <div><b>3</b><span>线上部署：项目部署在阿里云，WordPress 主页负责展示入口，FastAPI 子应用负责真实交互。</span></div>
          </div>
        </aside>
      </div>
    </div>
  </section>

  <section class="ph-section ph-section-soft">
    <div class="ph-container">
      <div class="ph-section-head">
        <h2>后续项目框架</h2>
        <p>主页会作为个人作品集入口继续扩展。未来新增项目时，可以按“项目说明、可运行入口、技术栈、结果展示”的方式加入下面区域。</p>
      </div>
      <div class="ph-next-grid">
        <article class="ph-next-card">
          <small>数据质量方向</small>
          <h3>传感器漂移检测</h3>
          <p>后续可加入时间漂移、采样完整性和跨设备一致性检测。</p>
        </article>
        <a class="ph-next-card" href="$ppt_url" target="_blank" rel="noopener">
          <small>统计建模方向</small>
          <h3>PPT放映测试</h3>
          <p>打开已有的 WordPress 页面，用于展示课程内容、概率统计实验或后续整理的演示材料。</p>
        </a>
        <article class="ph-next-card">
          <small>简历展示方向</small>
          <h3>项目经历整理</h3>
          <p>个人简介保留在右上角导航，主页主体专注展示可运行项目。</p>
        </article>
      </div>
    </div>
  </section>

  <section class="ph-final">
    <div class="ph-container">
      <div>
        <h2>从主页进入真实可运行项目</h2>
        <p>农业数据可信度检测系统会持续迭代，后续项目也会按统一框架扩展。</p>
      </div>
      <div class="ph-actions">
        <a class="ph-button ph-button-primary" href="$agri_url" target="_blank" rel="noopener">新标签页打开检测系统</a>
      </div>
    </div>
  </section>
</main>
HTML;

$elementor_content = $content;
$content = "<!-- wp:html -->\n" . $content . "\n<!-- /wp:html -->";

$existing = get_page_by_path('portfolio-home', OBJECT, 'page');
$post_data = [
    'post_title' => '首页',
    'post_name' => 'portfolio-home',
    'post_status' => 'publish',
    'post_type' => 'page',
    'post_content' => $content,
    'comment_status' => 'closed',
    'ping_status' => 'closed',
];

if ($existing) {
    $post_data['ID'] = $existing->ID;
    $page_id = wp_update_post(wp_slash($post_data), true);
} else {
    $page_id = wp_insert_post(wp_slash($post_data), true);
}

if (is_wp_error($page_id)) {
    fwrite(STDERR, $page_id->get_error_message() . PHP_EOL);
    exit(1);
}

$css = str_replace('body.page-id-59', 'body.page-id-' . $page_id, $css);
wp_update_custom_css_post($css);

update_post_meta($page_id, '_wp_page_template', 'default');
update_post_meta($page_id, '_elementor_edit_mode', 'builder');
update_post_meta($page_id, '_elementor_template_type', 'wp-page');
update_post_meta($page_id, '_elementor_version', defined('ELEMENTOR_VERSION') ? ELEMENTOR_VERSION : '3.32.1');
update_post_meta($page_id, '_elementor_data', wp_slash(wp_json_encode([
    [
        'id' => 'phhome01',
        'elType' => 'container',
        'settings' => [],
        'elements' => [
            [
                'id' => 'phhtml01',
                'elType' => 'widget',
                'settings' => [
                    'html' => $elementor_content,
                ],
                'elements' => [],
                'widgetType' => 'html',
            ],
        ],
        'isInner' => false,
    ],
])));
if (class_exists('\Elementor\Plugin')) {
    \Elementor\Plugin::instance()->files_manager->clear_cache();
}
update_option('show_on_front', 'page');
update_option('page_on_front', $page_id);

$locations = get_nav_menu_locations();
$menu_id = $locations['primary'] ?? 0;
if (!$menu_id) {
    $menu_id = wp_create_nav_menu('页面菜单');
}

foreach (wp_get_nav_menu_items($menu_id) ?: [] as $item) {
    wp_delete_post($item->ID, true);
}

function ph_add_menu_page($menu_id, $title, $page_id, $position) {
    wp_update_nav_menu_item($menu_id, 0, [
        'menu-item-title' => $title,
        'menu-item-object-id' => $page_id,
        'menu-item-object' => 'page',
        'menu-item-type' => 'post_type',
        'menu-item-status' => 'publish',
        'menu-item-position' => $position,
    ]);
}

function ph_add_menu_url($menu_id, $title, $url, $position, $target = '') {
    wp_update_nav_menu_item($menu_id, 0, [
        'menu-item-title' => $title,
        'menu-item-url' => $url,
        'menu-item-type' => 'custom',
        'menu-item-status' => 'publish',
        'menu-item-position' => $position,
        'menu-item-target' => $target,
    ]);
}

ph_add_menu_page($menu_id, '首页', $page_id, 1);
ph_add_menu_url($menu_id, '在线检测系统', $agri_url, 2, '_blank');
ph_add_menu_url($menu_id, '个人简介', $bio_url, 3);

$registered_locations = array_keys(get_registered_nav_menus());
foreach ($registered_locations as $location) {
    if (in_array($location, ['primary', 'mobile_menu'], true)) {
        $locations[$location] = $menu_id;
    }
}
set_theme_mod('nav_menu_locations', $locations);

flush_rewrite_rules(false);

echo json_encode([
    'page_id' => $page_id,
    'front_url' => home_url('/'),
    'agri_url' => $agri_url,
    'method_url' => $method_url,
    'ppt_url' => $ppt_url,
    'preview_url' => $preview_url,
], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT) . PHP_EOL;
