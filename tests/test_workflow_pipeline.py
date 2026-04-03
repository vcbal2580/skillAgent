from skills.workflow_pipeline import PipelineStep, WorkflowPipeline
import time


def test_pipeline_runs_with_dependencies():
    def step_a(ctx):
        return 2

    def step_b(ctx):
        return ctx["a"] + 3

    def step_c(ctx):
        return ctx["b"] * 2

    pipeline = WorkflowPipeline(
        name="demo",
        steps=[
            PipelineStep(name="a", fn=step_a),
            PipelineStep(name="b", fn=step_b, depends_on=["a"]),
            PipelineStep(name="c", fn=step_c, depends_on=["b"]),
        ],
    )

    result = pipeline.run()
    assert result["a"] == 2
    assert result["b"] == 5
    assert result["c"] == 10


def test_pipeline_detects_unresolved_dependency():
    pipeline = WorkflowPipeline(
        name="broken",
        steps=[
            PipelineStep(name="x", fn=lambda ctx: 1, depends_on=["missing"]),
        ],
    )

    try:
        pipeline.run()
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "cannot progress" in str(e)


def test_pipeline_parallel_steps_share_same_wave():
    events = []

    def step_a(ctx):
        time.sleep(0.05)
        events.append("a")
        return 1

    def step_b(ctx):
        time.sleep(0.05)
        events.append("b")
        return 2

    def step_c(ctx):
        return ctx["a"] + ctx["b"]

    pipeline = WorkflowPipeline(
        name="parallel",
        steps=[
            PipelineStep(name="a", fn=step_a, run_in_parallel=True),
            PipelineStep(name="b", fn=step_b, run_in_parallel=True),
            PipelineStep(name="c", fn=step_c, depends_on=["a", "b"]),
        ],
    )

    result = pipeline.run()
    assert sorted(events) == ["a", "b"]
    assert result["c"] == 3


def test_pipeline_retries_failed_step_once():
    state = {"count": 0}

    def flaky(ctx):
        state["count"] += 1
        if state["count"] == 1:
            raise ValueError("temporary")
        return 42

    pipeline = WorkflowPipeline(
        name="retry",
        steps=[PipelineStep(name="flaky", fn=flaky, retry_count=1)],
    )

    result = pipeline.run()
    assert result["flaky"] == 42
    assert result["_pipeline_meta"]["flaky"]["attempts"] == 2
    assert result["_pipeline_meta"]["flaky"]["status"] == "ok"


def test_pipeline_timeout_marks_failure():
    def slow(ctx):
        time.sleep(0.1)
        return "done"

    pipeline = WorkflowPipeline(
        name="timeout",
        steps=[PipelineStep(name="slow", fn=slow, timeout_seconds=0.01)],
    )

    try:
        pipeline.run()
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "timed out" in str(e)
