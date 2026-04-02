from skills.workflow_pipeline import PipelineStep, WorkflowPipeline


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
