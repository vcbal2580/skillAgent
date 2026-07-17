"""Tests for work CV skill timeline and CV generation."""

from pathlib import Path
import tempfile
import unittest

from skills.work_cv_skill import WorkCVSkill


class TestWorkCVSkill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.source_dir = root / "docs" / "original_work"
        self.output_dir = root / "docs" / "cv"
        self.source_dir.mkdir(parents=True, exist_ok=True)

        (self.source_dir / "project_a.md").write_text(
            "# 项目A\n"
            "2023-03 ~ 2024-06 负责平台建设与核心接口设计\n"
            "- 主导接口规范\n"
            "- 推进性能优化\n",
            encoding="utf-8",
        )
        (self.source_dir / "project_b.md").write_text(
            "# 项目B\n"
            "2024-07 ~ 至今 负责 Agent 工作流能力建设\n"
            "- 设计可扩展技能架构\n",
            encoding="utf-8",
        )

        self.skill = WorkCVSkill()

    def tearDown(self):
        self.tmp.cleanup()

    def test_analyze_generates_dated_timeline(self):
        out = self.skill.execute(
            action="analyze",
            source_dir=str(self.source_dir),
            output_dir=str(self.output_dir),
            save_date="20260714",
        )
        self.assertIn("timeline_20260714.md", out)

        timeline_file = self.output_dir / "timeline_20260714.md"
        self.assertTrue(timeline_file.exists())
        content = timeline_file.read_text(encoding="utf-8")

        self.assertIn("2024-07 ~ 至今", content)
        self.assertIn("2023-03 ~ 2024-06", content)
        # Newer event should appear first.
        self.assertLess(content.index("2024-07 ~ 至今"), content.index("2023-03 ~ 2024-06"))

    def test_generate_latest_cv_writes_latest_and_dated(self):
        out = self.skill.execute(
            action="generate_latest_cv",
            source_dir=str(self.source_dir),
            output_dir=str(self.output_dir),
            save_date="20260714",
            target_role="Python 后端工程师",
            jd_text="需要 Python、FastAPI、接口设计、项目交付经验",
        )
        self.assertIn("latest_cv.md", out)
        self.assertIn("latest_cv_brief.md", out)

        dated_cv = self.output_dir / "cv_detailed_20260714.md"
        brief_cv = self.output_dir / "cv_brief_20260714.md"
        latest_cv = self.output_dir / "latest_cv.md"
        latest_brief = self.output_dir / "latest_cv_brief.md"
        timeline_file = self.output_dir / "timeline_20260714.md"

        self.assertTrue(dated_cv.exists())
        self.assertTrue(brief_cv.exists())
        self.assertTrue(latest_cv.exists())
        self.assertTrue(latest_brief.exists())
        self.assertTrue(timeline_file.exists())

        latest_text = latest_cv.read_text(encoding="utf-8")
        self.assertIn("目标岗位: Python 后端工程师", latest_text)
        self.assertIn("JD 对齐说明", latest_text)

        brief_text = latest_brief.read_text(encoding="utf-8")
        self.assertIn("精炼工作简历", brief_text)
        self.assertIn("JD 关注点", brief_text)
        self.assertNotIn("JD 对齐说明", brief_text)


if __name__ == "__main__":
    unittest.main()
