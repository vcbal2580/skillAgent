"""
Work CV skill - analyze work documents and generate timeline/CV markdown files.

Input documents are expected under docs/original_work by default.
Outputs are written under docs/cv with both dated and latest files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from skills.base import BaseSkill
from skills.document_skill import extract_document


_TEXT_SUFFIXES = {".md", ".txt", ".rst", ".csv", ".json", ".yaml", ".yml"}
_DOC_SUFFIXES = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".eml"}
_DATE_RE = re.compile(
    r"(?P<start>\d{4}[./-]\d{1,2})(?:\s*(?:~|～|-|—|至|到)\s*(?P<end>\d{4}[./-]\d{1,2}|至今|今|现在|present|Present))?"
)
_BULLET_RE = re.compile(r"^[\-\*•]\s+")
_HEADING_RE = re.compile(r"^#{1,6}\s+")


@dataclass
class WorkEvent:
    start_date: date
    start_label: str
    end_label: str
    summary: str
    source_file: str


class WorkCVSkill(BaseSkill):
    name = "work_cv_manage"
    description = (
        "分析工作项目文档并生成时间轴与简历文档。"
        "默认读取 docs/original_work，输出到 docs/cv。"
        "可用于按时间轴总结经历，并生成最新简历文件。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["analyze", "generate_latest_cv", "list_files"],
                "description": "执行动作：analyze=生成时间轴，generate_latest_cv=生成最新简历，list_files=列出输入文件",
            },
            "source_dir": {
                "type": "string",
                "description": "工作原始文档目录，默认 docs/original_work",
                "default": "docs/original_work",
            },
            "output_dir": {
                "type": "string",
                "description": "输出目录，默认 docs/cv",
                "default": "docs/cv",
            },
            "save_date": {
                "type": "string",
                "description": "输出日期标签，格式 YYYYMMDD；默认使用当天日期",
            },
            "target_role": {
                "type": "string",
                "description": "目标岗位，用于简历抬头和简介（可选）",
            },
            "jd_text": {
                "type": "string",
                "description": "用户提供的 JD 文本。会据此筛选并组合相关项目经历，生成更贴合岗位的简历。",
            },
        },
        "required": ["action"],
    }

    def execute(
        self,
        action: str,
        source_dir: str = "docs/original_work",
        output_dir: str = "docs/cv",
        save_date: str | None = None,
        target_role: str = "",
        jd_text: str = "",
    ) -> str:
        source_path = Path(source_dir)
        output_path = Path(output_dir)
        stamp = self._normalize_stamp(save_date)

        if action == "list_files":
            files = self._iter_source_files(source_path)
            if not files:
                return f"未在目录中找到可解析文档: {source_path}"
            lines = [f"- {f.as_posix()}" for f in files]
            return "已发现以下工作文档：\n" + "\n".join(lines)

        events, source_files = self._collect_events(source_path)
        if not source_files:
            return (
                f"未找到可解析的输入文档。请先将工作材料放入 {source_path.as_posix()}，"
                "支持 md/txt/rst/pdf/docx/xlsx/xls/eml。"
            )

        if action == "analyze":
            timeline_md = self._build_timeline_markdown(events, source_files)
            timeline_file = output_path / f"timeline_{stamp}.md"
            self._write_text(timeline_file, timeline_md)
            return (
                f"已完成工作经历时间轴分析。\n"
                f"- 输入文件数: {len(source_files)}\n"
                f"- 识别事件数: {len(events)}\n"
                f"- 时间轴文件: {timeline_file.as_posix()}"
            )

        if action == "generate_latest_cv":
            timeline_md = self._build_timeline_markdown(events, source_files)
            timeline_file = output_path / f"timeline_{stamp}.md"
            self._write_text(timeline_file, timeline_md)

            matched_events = self._rank_events_for_jd(events, jd_text)
            detailed_cv_md = self._build_cv_markdown(
                matched_events,
                target_role=target_role,
                jd_text=jd_text,
                concise=False,
            )
            concise_cv_md = self._build_cv_markdown(
                matched_events,
                target_role=target_role,
                jd_text=jd_text,
                concise=True,
            )

            dated_cv_file = output_path / f"cv_detailed_{stamp}.md"
            concise_cv_file = output_path / f"cv_brief_{stamp}.md"
            latest_cv_file = output_path / "latest_cv.md"
            latest_brief_file = output_path / "latest_cv_brief.md"
            self._write_text(dated_cv_file, detailed_cv_md)
            self._write_text(concise_cv_file, concise_cv_md)
            self._write_text(latest_cv_file, detailed_cv_md)
            self._write_text(latest_brief_file, concise_cv_md)

            return (
                f"已生成最新工作简历与时间轴。\n"
                f"- 输入文件数: {len(source_files)}\n"
                f"- 识别事件数: {len(events)}\n"
                f"- JD 匹配事件数: {len(matched_events)}\n"
                f"- 时间轴文件: {timeline_file.as_posix()}\n"
                f"- 详细简历: {dated_cv_file.as_posix()}\n"
                f"- 精炼简历: {concise_cv_file.as_posix()}\n"
                f"- 最新详细简历: {latest_cv_file.as_posix()}\n"
                f"- 最新精炼简历: {latest_brief_file.as_posix()}"
            )

        return f"不支持的 action: {action}"

    def _normalize_stamp(self, stamp: str | None) -> str:
        if stamp:
            text = stamp.strip()
            if re.fullmatch(r"\d{8}", text):
                return text
        return datetime.now().strftime("%Y%m%d")

    def _iter_source_files(self, source_dir: Path) -> list[Path]:
        if not source_dir.exists() or not source_dir.is_dir():
            return []
        files: list[Path] = []
        for p in sorted(source_dir.rglob("*")):
            if not p.is_file():
                continue
            suffix = p.suffix.lower()
            if suffix in _TEXT_SUFFIXES or suffix in _DOC_SUFFIXES:
                files.append(p)
        return files

    def _read_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in _TEXT_SUFFIXES:
            for enc in ("utf-8", "utf-8-sig", "gbk"):
                try:
                    return path.read_text(encoding=enc)
                except Exception:
                    continue
            return ""

        if suffix in _DOC_SUFFIXES:
            text = extract_document(str(path))
            if text.startswith("[Error]"):
                return ""
            return text

        return ""

    def _collect_events(self, source_dir: Path) -> tuple[list[WorkEvent], list[Path]]:
        files = self._iter_source_files(source_dir)
        all_events: list[WorkEvent] = []

        for f in files:
            text = self._read_text(f)
            if not text.strip():
                continue
            events = self._extract_events_from_text(text, f.name)
            if not events:
                fallback = self._fallback_event_from_text(text, f.name)
                if fallback:
                    all_events.append(fallback)
                continue
            all_events.extend(events)

        all_events.sort(key=lambda x: x.start_date, reverse=True)
        return all_events, files

    def _extract_events_from_text(self, text: str, source_name: str) -> list[WorkEvent]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        events: list[WorkEvent] = []
        current_heading = ""

        i = 0
        while i < len(lines):
            line = lines[i]
            if _HEADING_RE.match(line):
                current_heading = _HEADING_RE.sub("", line).strip()
                i += 1
                continue

            m = _DATE_RE.search(line)
            if not m:
                i += 1
                continue

            start_label, start_dt = self._normalize_ym(m.group("start"))
            end_raw = m.group("end") or ""
            end_label = self._normalize_end(end_raw)

            desc = line[m.end():].strip(" -:：|，,。")
            details: list[str] = []
            j = i + 1
            while j < len(lines) and len(details) < 3:
                nxt = lines[j]
                if _DATE_RE.search(nxt) or _HEADING_RE.match(nxt):
                    break
                if _BULLET_RE.match(nxt):
                    details.append(_BULLET_RE.sub("", nxt).strip())
                j += 1

            pieces = []
            if current_heading:
                pieces.append(current_heading)
            if desc:
                pieces.append(desc)
            if details:
                pieces.append("；".join(details))
            summary = " - ".join([p for p in pieces if p]).strip()
            if not summary:
                summary = "工作经历条目（原文未提供明确描述）"

            events.append(
                WorkEvent(
                    start_date=start_dt,
                    start_label=start_label,
                    end_label=end_label,
                    summary=summary,
                    source_file=source_name,
                )
            )
            i = j if j > i else i + 1

        return events

    def _fallback_event_from_text(self, text: str, source_name: str) -> WorkEvent | None:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return None
        bullets = []
        for ln in lines:
            if _BULLET_RE.match(ln):
                bullets.append(_BULLET_RE.sub("", ln).strip())
            if len(bullets) >= 3:
                break

        if not bullets:
            bullets = [ln for ln in lines[:3] if len(ln) <= 120]

        summary = "；".join(bullets[:3]).strip()
        if not summary:
            return None

        return WorkEvent(
            start_date=date.today(),
            start_label=date.today().strftime("%Y-%m"),
            end_label="待补充",
            summary=f"文档要点（未识别到时间段）: {summary}",
            source_file=source_name,
        )

    def _normalize_ym(self, raw: str) -> tuple[str, date]:
        clean = raw.replace(".", "-").replace("/", "-")
        year_str, month_str = clean.split("-", 1)
        year = int(year_str)
        month = int(month_str)
        month = 1 if month < 1 else (12 if month > 12 else month)
        dt = date(year, month, 1)
        return f"{year:04d}-{month:02d}", dt

    def _normalize_end(self, raw: str) -> str:
        text = (raw or "").strip()
        if not text:
            return "待补充"
        if text.lower() in {"present"} or text in {"今", "至今", "现在"}:
            return "至今"
        try:
            label, _ = self._normalize_ym(text)
            return label
        except Exception:
            return text

    def _build_timeline_markdown(self, events: list[WorkEvent], source_files: list[Path]) -> str:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "# 工作经历时间轴",
            "",
            f"- 生成时间: {generated_at}",
            f"- 输入文档数: {len(source_files)}",
            f"- 识别事件数: {len(events)}",
            "",
            "## 时间轴明细（按开始时间倒序）",
            "",
        ]

        if not events:
            lines.append("- 未识别到有效事件，请补充包含时间段的经历描述。")
        else:
            for ev in events:
                lines.append(f"### {ev.start_label} ~ {ev.end_label}")
                lines.append(f"- {ev.summary}")
                lines.append(f"- 来源: {ev.source_file}")
                lines.append("")

        lines.append("## 输入文档清单")
        lines.append("")
        for src in source_files:
            lines.append(f"- {src.as_posix()}")

        return "\n".join(lines).strip() + "\n"

    def _tokenize_jd(self, jd_text: str) -> list[str]:
        if not jd_text.strip():
            return []
        tokens = re.findall(r"[A-Za-z0-9_\-+/]{2,}|[\u4e00-\u9fff]{2,}", jd_text.lower())
        stop_words = {
            "and", "the", "for", "with", "from", "that", "this", "into", "will", "must",
            "岗位", "要求", "经验", "能力", "负责", "熟悉", "优先", "具有", "以及", "相关",
        }
        return [token for token in tokens if token not in stop_words]

    def _rank_events_for_jd(self, events: list[WorkEvent], jd_text: str) -> list[WorkEvent]:
        jd_tokens = self._tokenize_jd(jd_text)
        if not jd_tokens:
            return events[:]

        scored: list[tuple[int, WorkEvent]] = []
        for event in events:
            haystack = f"{event.summary} {jd_text}".lower()
            score = 0
            for token in jd_tokens:
                if len(token) >= 2 and token in haystack:
                    score += 2 if len(token) > 3 else 1
            scored.append((score, event))

        scored.sort(key=lambda item: (item[0], item[1].start_date), reverse=True)
        selected = [event for score, event in scored if score > 0]
        if not selected:
            return events[:]
        return selected[:12]

    def _extract_skill_keywords(self, events: list[WorkEvent], jd_text: str = "") -> list[str]:
        text = " ".join(ev.summary.lower() for ev in events)
        jd_text = jd_text.lower()
        mapping = {
            "Python": ["python", "fastapi", "flask", "django"],
            "LLM/AI": ["llm", "ai", "agent", "embedding", "prompt", "rag", "mcp"],
            "Data": ["sql", "mysql", "postgres", "redis", "vector", "chroma"],
            "Backend": ["api", "backend", "service", "microservice", "接口", "服务"],
            "DevOps": ["docker", "k8s", "ci", "cd", "deploy", "发布", "运维"],
            "Product Delivery": ["需求", "迭代", "交付", "项目", "方案", "落地"],
        }
        result = []
        for label, words in mapping.items():
            if any(w in text or w in jd_text for w in words):
                result.append(label)
        if not result:
            return ["项目分析", "需求拆解", "跨团队协作"]
        return result

    def _build_cv_markdown(
        self,
        events: list[WorkEvent],
        target_role: str = "",
        jd_text: str = "",
        concise: bool = False,
    ) -> str:
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        role_line = target_role.strip() if target_role.strip() else "（待补充目标岗位）"
        skills = self._extract_skill_keywords(events, jd_text=jd_text)
        jd_focus = self._tokenize_jd(jd_text)[:10]

        if concise:
            lines = [
                "# 精炼工作简历（JD 匹配版）",
                "",
                f"- 生成时间: {generated_at}",
                f"- 目标岗位: {role_line}",
            ]
            if jd_focus:
                lines.extend([
                    "- JD 关注点: " + "、".join(jd_focus),
                ])
            lines.extend([
                "",
                "## 个人简介",
                "",
                "围绕目标 JD 组织项目经历，优先突出与岗位最相关的技术栈、交付结果和协作能力。",
                "",
                "## 核心能力",
                "",
                "- " + "\n- ".join(skills[:5]),
                "",
                "## 代表经历",
                "",
            ])
            for ev in events[:6]:
                lines.append(f"- {self._make_bullet(ev, jd_text=jd_text, concise=True)}")
            lines.extend([
                "",
                "## 附注",
                "",
                "- 该版本适合直接投递或放入简历主文件，保留了 JD 相关的高信号信息。",
                "",
            ])
            return "\n".join(lines).strip() + "\n"

        jd_focus_str = "、".join(jd_focus) if jd_focus else "未提供"

        lines = [
            "# 详细工作简历（JD 匹配版）",
            "",
            f"- 生成时间: {generated_at}",
            f"- 目标岗位: {role_line}",
            f"- JD 关注点: {jd_focus_str}",
            "",
            "## 个人简介",
            "",
            "具备完整项目交付经验，能够围绕岗位 JD 对项目经历进行重组、提炼与表达增强，"
            "把技术能力、业务结果和协作价值组合成更贴合投递场景的简历内容。",
            "",
            "## 核心能力",
            "",
            "- " + "\n- ".join(skills),
            "",
            "## JD 对齐说明",
            "",
            self._build_jd_alignment_summary(jd_text, skills),
            "",
            "## 工作经历（按时间倒序）",
            "",
        ]

        if not events:
            lines.append("- 暂无可用工作经历条目，请先补充 docs/original_work 文档。")
        else:
            top_events = events[:12]
            for ev in top_events:
                lines.append(f"### {ev.start_label} ~ {ev.end_label}")
                lines.append(f"- {self._make_bullet(ev, jd_text=jd_text, concise=False)}")
                lines.append("")

        lines.extend([
            "## 代表项目要点",
            "",
        ])

        project_events = [
            ev for ev in events
            if any(k in ev.summary.lower() for k in ("项目", "system", "平台", "系统", "workflow", "agent"))
        ]

        if project_events:
            for ev in project_events[:5]:
                lines.append(f"- [{ev.start_label} ~ {ev.end_label}] {ev.summary}")
        else:
            lines.append("- 建议在原始文档中增加“项目背景-职责-结果”结构，便于自动提炼。")

        lines.extend([
            "",
            "## 附注",
            "",
            "- 本简历由工作文档自动生成，建议人工补充量化指标（如性能提升、交付周期、业务结果）。",
            "",
        ])

        return "\n".join(lines).strip() + "\n"

    def _build_jd_alignment_summary(self, jd_text: str, skills: list[str]) -> str:
        jd_tokens = self._tokenize_jd(jd_text)
        if not jd_tokens:
            return "- 未提供 JD，已按通用工作经历视角生成。"
        skill_text = "、".join(skills[:6]) if skills else "通用项目能力"
        focus = "、".join(jd_tokens[:8])
        return (
            f"- 已从 JD 提取关注点：{focus}。\n"
            f"- 输出内容会优先强调与这些关注点相关的项目组合、职责扩展与成果表达。\n"
            f"- 重点技能标签：{skill_text}。"
        )

    def _make_bullet(self, event: WorkEvent, jd_text: str = "", concise: bool = False) -> str:
        jd_tokens = self._tokenize_jd(jd_text)
        base = event.summary
        if jd_tokens:
            hit_tokens = [token for token in jd_tokens if token in event.summary.lower() or token in jd_text.lower()]
            if hit_tokens:
                base = self._enrich_summary(event.summary, hit_tokens, concise=concise)
        if concise:
            return base
        return base

    def _enrich_summary(self, summary: str, hit_tokens: list[str], concise: bool = False) -> str:
        focus = "、".join(dict.fromkeys(hit_tokens[:5]))
        if concise:
            return f"{summary}（匹配 JD 关键词：{focus}）"
        return (
            f"{summary}；结合 JD 关键词 {focus} 进行项目组合表达，"
            "突出岗位相关技术深度、交付结果和跨角色协作。"
        )

    def _write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
