# SkillAgent Skills Reference
<!-- AI-READABLE: Canonical skill catalog for tool selection and behavior understanding. -->

## How Skills Work

- Each skill is a Python class derived from BaseSkill.
- Skills are registered in Agent.register_default_skills().
- LLM sees each skill as an OpenAI function tool definition.
- Prompt overlays in prompts/zh.yaml and prompts/en.yaml can rewrite skill descriptions and parameter descriptions without changing Python code.

---

## Registered Skills (Current Version)

### 1) web_search

- Name: web_search
- File: skills/web_search.py
- Purpose: Search internet for real-time facts and latest information.
- Parameters:
  - query (string, required): Search query keywords.
  - max_results (integer, optional, default 5): Max number of search results.
- Notes:
  - Uses ddgs (DuckDuckGo Search) with no external paid API key.
  - Suitable for fact checking and fresh information.

### 2) knowledge_manage

- Name: knowledge_manage
- File: skills/knowledge_skill.py
- Purpose: Manage personal knowledge base entries.
- Parameters:
  - action (string, required): save | search | list | delete
  - content (string, optional by action): content/query/id depending on action
  - tags (string, optional): comma-separated tags for save
- Notes:
  - Backed by ChromaDB vector store.
  - Supports semantic retrieval.

### 3) get_datetime

- Name: get_datetime
- File: skills/datetime_skill.py
- Purpose: Return current date/time/week day/timestamp.
- Parameters:
  - timezone_offset (integer, optional, default 8): timezone offset in hours
- Notes:
  - Use this skill for precise time answers.

### 4) get_weather

- Name: get_weather
- File: skills/weather_skill.py
- Purpose: Query current weather and forecast.
- Parameters:
  - city (string, optional): city name
  - days (integer, optional): forecast days
- Notes:
  - Uses free public services (IP geolocation + geocoding + weather API).

### 5) fortune_divination

- Name: fortune_divination
- File: skills/divination_skill.py
- Purpose: Entertainment-only Chinese divination response.
- Parameters:
  - question (string, required)
  - year (integer, optional)
- Notes:
  - Should be used only when user explicitly asks.

### 6) tarot_career_reading

- Name: tarot_career_reading
- File: skills/tarot_career_skill.py
- Purpose: Entertainment-only tarot reading focused on career.
- Parameters:
  - question (string, required)
  - cards (integer, optional): 1 or 3

### 7) today_luck

- Name: today_luck
- File: skills/lucky_today_skill.py
- Purpose: Daily luck summary.
- Parameters:
  - name (string, optional)

### 8) huangli_today

- Name: huangli_today
- File: skills/almanac_skill.py
- Purpose: Chinese almanac style daily guidance.
- Parameters:
  - date (string, optional): YYYY-MM-DD

### 9) wecom_notify

- Name: wecom_notify
- File: skills/wecom_notify_skill.py
- Purpose: Send notifications to WeCom webhook/group bot.
- Parameters:
  - content (string, required)
  - msg_type (string, optional): text | markdown | news
  - mentioned_list (array/string, optional)

### 10) git_daily_summary

- Name: git_daily_summary
- File: skills/git_summary_skill.py
- Purpose: Summarize git commits daily/weekly.
- Parameters:
  - mode (string, optional): auto | today | week
- Notes:
  - Reads git_summary config, supports local repos and remote repo cache.

### 11) news_workflow

- Name: news_workflow
- File: skills/news_workflow_skill.py
- Purpose: Start/list/stop a live local news timeline workflow service.
- Parameters:
  - action (string, required): start | stop | list
  - topic (string, required for start)
  - refresh_minutes (integer, optional, default 60)
  - max_results (integer, optional, default 20)
  - workflow_name (string, optional for stop)
- Current behavior highlights:
  - Time-stratified retrieval using ddgs timelimit d/w/m.
  - Dedup by URL, newest-first sorting.
  - Age tagging: today | 3days | week | older.
  - AI summary output with layered detail by recency.
  - Built-in local HTML timeline UI with grouped sections.

---

## Internal / Support Components

### document_skill.py

- Not directly exposed as a general user tool in normal chat flow.
- Used by API endpoint /upload/document.
- Handles PDF, DOCX, XLSX/XLS, TXT, EML, and HTML extraction.

### workflow_service.py

- Provides WorkflowManager singleton and WorkflowInstance runtime.
- Enables any skill to spin up local background web services with periodic refresh.

### 12) work_cv_manage

- Name: work_cv_manage
- File: skills/work_cv_skill.py
- Purpose: Analyze work project source docs and generate timeline/CV markdown outputs.
- Parameters:
  - action (string, required): analyze | generate_latest_cv | list_files
  - source_dir (string, optional): input folder, default docs/original_work
  - output_dir (string, optional): output folder, default docs/cv
  - save_date (string, optional): output stamp in YYYYMMDD
  - target_role (string, optional): target role for CV header
- Output behavior:
  - Timeline: docs/cv/timeline_YYYYMMDD.md
  - CV snapshot: docs/cv/cv_YYYYMMDD.md
  - Latest CV: docs/cv/latest_cv.md
