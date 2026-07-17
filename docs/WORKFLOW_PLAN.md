# 工作流能力扩展 — 架构方案

> 制定日期: 2026-04-02  
> 状态: 实施中  
> 关联分支: `workflow`

---

## 一、现状诊断

```
当前工作流模型（扁平单职能）:
用户意图 → LLM选择skill → skill.execute() → WorkflowInstance(HTTP服务) → 浏览器

痛点:
- 每个skill是孤岛，无法复合调用
- WorkflowInstance只支持"数据 → 单一HTML模板"
- 没有管道(pipeline)概念，LLM做不了 fetch→scrape→analyze→render→pdf 的链式决策
- 页面生成逻辑写死在skill里，无法复用
```

---

## 二、三种参考架构对比

### 架构 A：Claude Computer Use 风格（工具原子化 + LLM全程编排）

```
核心思想: 每个工具只做一件事，复杂任务由LLM自行组装工具序列

tool_call_loop:
  LLM → call scrape_page(url)
      → call extract_content(html, schema)
      → call render_workflow_page(title, data, template)
      → call export_pdf(workflow_name)
      → call notify_wecom(message, attachment)
  (每步结果返回给LLM，LLM决定下一步)

优点: 绝对灵活，LLM智能充分发挥
缺点: token消耗大，延迟高，对模型能力依赖强
适用: 探索性任务、非结构化需求
```

### 架构 B：LangGraph/工作流引擎风格（显式DAG + 状态机）

```
核心思想: 预定义pipeline模板，LLM只需选择pipeline和填参数

WorkflowPipeline("research"):
  Step1: web_search(query) → [urls]
  Step2: parallel(scrape_page(url) for url in urls[:3]) → [contents]
  Step3: llm_analyze(contents, instruction) → analysis
  Step4: render_page(title, analysis, data) → workflow_url
  Step5: export_pdf(workflow_url) → pdf_path  [optional]

LLM调用:
  run_workflow(name="research", query="...", with_pdf=true)

优点: 可预期、可重复、效率高
缺点: 需要预定义，灵活性受限
适用: 固定业务流（新闻/调研/监控）
```

### 架构 C：Open Interpreter 风格（代码执行作为核心原语）

```
核心思想: 给LLM一个"执行Python"的能力，工作流是LLM写的代码

skill: execute_python(code) → stdout
LLM可在代码里调用 requests, BeautifulSoup, jinja2, pdfkit 等

优点: 无限扩展，无需预定义每个workflow
缺点: 安全隔离难，调试困难，需要沙箱
适用: 有完整沙箱/权限控制的高级场景（当前不采用）
```

---

## 三、推荐方案：A+B混合架构

```
┌─────────────────────────────────────────────────────────────────┐
│      原子工具层 (Architecture A)    工作流模板层 (Architecture B)  │
│                                                                 │
│  scrape_page      ──┐                                           │
│  extract_content  ──┤  → WorkflowPipeline                      │
│  render_page      ──┤    research / monitor / report / compare  │
│  export_pdf       ──┤  → WorkflowEngine (DAG + State)           │
│  notify           ──┘                                           │
│                                                                 │
│  WorkflowManager (现有)                                         │
│  ├── WorkflowDashboard  http://127.0.0.1:9000  (总控台)         │
│  ├── NewsWorkflow       port 9101                               │
│  ├── ResearchWorkflow   port 9102                               │
│  └── MonitorWorkflow    port 9103                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、新增模块清单

### 模块 1：`WebScrapeSkill` — 页面抓取与提取
```
文件: skills/web_scrape_skill.py
触发词: "帮我看看这个页面" / "分析这个网址" / "抓取...内容"

参数:
  url: str          目标URL
  extract: str      "text" | "structured" | "links" | "tables"
  selector: str     可选CSS选择器

实现:
  - httpx + BeautifulSoup4 (轻量，无需Playwright)
  - playwright 模式用于JS渲染页面（可选，已在requirements.txt）

返回给LLM: 结构化文本/JSON，LLM可继续加工
```

### 模块 2：`PageGenerateSkill` — 智能页面生成
```
文件: skills/page_generate_skill.py
触发词: "生成一个页面" / "做成可视化" / "展示这些数据"

参数:
  title: str
  data: list[dict] | str      数据集或JSON字符串
  template: str               "timeline" | "report" | "table" | "cards"
  summary: str                可选AI摘要
  refresh_seconds: int        0=不自动刷新

模板系统:
  skills/templates/
    base.html         基础样式 (dark theme CSS变量)
    timeline.html     事件/新闻时间轴
    report.html       调研报告 (段落+摘要)
    table.html        可排序数据表
    cards.html        卡片网格

返回: http://127.0.0.1:{port}
```

### 模块 3：`PDFExportSkill` — PDF导出
```
文件: skills/pdf_export_skill.py
触发词: "导出PDF" / "保存成PDF" / "生成报告"

参数:
  source: str   "workflow:{name}" | "url:{url}"
  filename: str 可选文件名

实现: weasyprint (纯Python HTML→PDF)
导出路径: data/exports/{timestamp}_{filename}.pdf

返回: 文件绝对路径
```

### 模块 4：`WorkflowDashboardSkill` — 总控台
```
文件: skills/workflow_dashboard_skill.py
端口: 9000 (系统启动时自动开启)
触发词: "查看工作流" / "我的工作流" / "关闭..."

功能:
  - 卡片式列出所有running workflows
  - 每个workflow: 名称/端口/最后刷新/状态/数据量
  - 操作按钮: 打开/刷新/导出PDF/停止
```

### 模块 5：`ResearchWorkflowSkill` — 调研全流程 Pipeline (Phase 2)
```
文件: skills/research_workflow_skill.py
内置Pipeline:
  1. web_search(query, n=5)          → urls[]
  2. parallel scrape(url)            → contents[]
  3. llm_synthesize(contents)        → structured_report
  4. render_page("research", report) → workflow_url
  5. [可选] export_pdf               → pdf_path
```

### 模块 6：`MonitorWorkflowSkill` — 持续监控 (Phase 2)
```
文件: skills/monitor_workflow_skill.py
参数:
  target: str     URL或搜索词
  interval: int   检查间隔(分钟)
  condition: str  "any_change" | "keyword_appear:{kw}"
  notify: str     "wecom" | "console"
```

---

## 五、WorkflowInstance 增强

新增HTTP端点:
```
GET  /export/pdf    → 触发weasyprint导出，返回文件路径
GET  /export/json   → 当前数据原始JSON
POST /api/refresh   → 手动触发刷新
GET  /api/history   → 历史快照列表（如果开启）
```

新增方法:
```python
def export_pdf(self, output_path: str) -> str
def get_snapshot(self) -> dict
def add_endpoint(self, path: str, handler: Callable)
```

---

## 六、Jinja2 模板架构

```
skills/templates/
  base.html          dark theme CSS变量，头部/底部/刷新逻辑
  timeline.html      时间轴（复用新闻模板思路）
  report.html        调研报告
  table.html         可排序表格
  cards.html         卡片网格
```

---

## 七、依赖变化

| 包 | 用途 | 状态 |
|----|------|------|
| `httpx` | 异步HTTP抓取 | 新增 |
| `beautifulsoup4` | HTML解析 | 新增 |
| `jinja2` | 模板引擎 | 新增 |
| `weasyprint` | HTML→PDF | 新增 |
| `playwright` | JS渲染页面抓取 | 已有 |

---

## 八、分阶段实施路线图

### Phase 1 — 原子工具 ✅ 实施中
- [ ] 安装依赖: httpx, beautifulsoup4, jinja2, weasyprint
- [ ] Jinja2 HTML模板 (base + timeline + report + table + cards)
- [ ] `WebScrapeSkill`
- [ ] `PageGenerateSkill`
- [ ] WorkflowInstance 增强 (/export/json, /api/refresh, /export/pdf)
- [ ] `WorkflowDashboardSkill` (端口9000)
- [ ] `PDFExportSkill`
- [ ] 注册所有新skill到agent.py

### Phase 2 — Pipeline 编排 (待实施)
- [ ] `WorkflowPipeline` 核心引擎 (DAG + State)
- [ ] `ResearchWorkflowSkill` 完整调研pipeline
- [ ] `MonitorWorkflowSkill` 持续监控

---

## 九、用户交互示例（实现后）

```
用户: "帮我调研一下2026年国内AI芯片竞争格局，生成一份带PDF的报告"

Agent链路:
  → run_workflow(name="research", query="...", depth="standard", with_pdf=true)
  → Pipeline: search(5) → scrape(5) → llm综合 → render_page → export_pdf
  
  回复: "调研完成！在线报告: http://127.0.0.1:9102
         PDF: data/exports/research_AI芯片_20260402.pdf"

用户: "把XPPen官网的支持页面帮我整理成表格页面"

Agent链路:
  → scrape_page(url="...", extract="tables")
  → render_page(template="table", title="XPPen支持", data=...)
  → 返回 http://127.0.0.1:9103

用户: "查看我所有工作流"
  → 打开 http://127.0.0.1:9000 (Dashboard)
```
