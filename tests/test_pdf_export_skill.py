from pathlib import Path

from skills.pdf_export_skill import PDFExportSkill


class _DummyWf:
    def __init__(self):
        self.output = None

    def export_pdf(self, path):
        self.output = path
        Path(path).write_bytes(b"%PDF-1.4\n")
        return path


class _DummyManager:
    def __init__(self, wf=None):
        self._wf = wf

    def get_workflow(self, name):
        return self._wf


def test_pdf_export_from_workflow(monkeypatch, tmp_path):
    wf = _DummyWf()

    def _manager_factory():
        return _DummyManager(wf)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("skills.pdf_export_skill.WorkflowManager", _manager_factory)

    skill = PDFExportSkill()
    result = skill.execute(source="workflow:demo", filename="demo_report")

    assert result.startswith("PDF exported:")
    assert wf.output is not None
    assert Path(wf.output).name == "demo_report.pdf"


def test_pdf_export_invalid_source(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    skill = PDFExportSkill()
    result = skill.execute(source="bad:xxx")
    assert (
        result == "Invalid source. Use workflow:<name> or url:<http_url>"
        or result.startswith("weasyprint unavailable:")
    )
