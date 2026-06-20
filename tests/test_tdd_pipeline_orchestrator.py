"""TDD tests for pipeline orchestrator exception paths."""
import pytest
import sys, os
from unittest.mock import patch, MagicMock
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard


class TestPipelineOrchestrator:
    """Test run_pipeline exception handling branches."""

    def test_keyboard_interrupt(self, tmp_path):
        """KeyboardInterrupt should stop pipeline gracefully."""
        from core.pipeline import run_pipeline, PIPELINE_STEPS
        (tmp_path / "test.txt").write_text("内容" * 50, encoding="utf-8")

        original_steps = PIPELINE_STEPS.copy()
        try:
            # Make step 1 raise KeyboardInterrupt
            def bad_step(ctx):
                raise KeyboardInterrupt()
            PIPELINE_STEPS[0] = ("step1_intake", bad_step)

            ctx = PipelineContext(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                identity="被诉方（被告）",
                goal="应诉答辩",
            )
            ctx = run_pipeline(ctx)
            assert any("中断" in e for e in ctx.errors)
        finally:
            PIPELINE_STEPS[:] = original_steps

    def test_memory_error(self, tmp_path):
        """MemoryError should stop pipeline gracefully."""
        from core.pipeline import run_pipeline, PIPELINE_STEPS
        (tmp_path / "test.txt").write_text("内容" * 50, encoding="utf-8")

        original_steps = PIPELINE_STEPS.copy()
        try:
            def bad_step(ctx):
                raise MemoryError()
            PIPELINE_STEPS[0] = ("step1_intake", bad_step)

            ctx = PipelineContext(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                identity="被诉方（被告）",
                goal="应诉答辩",
            )
            ctx = run_pipeline(ctx)
            assert any("内存不足" in e for e in ctx.errors)
        finally:
            PIPELINE_STEPS[:] = original_steps

    def test_ai_provider_error(self, tmp_path):
        """AIProviderError should stop pipeline."""
        from core.pipeline import run_pipeline, PIPELINE_STEPS, AIProviderError
        (tmp_path / "test.txt").write_text("内容" * 50, encoding="utf-8")

        original_steps = PIPELINE_STEPS.copy()
        try:
            def bad_step(ctx):
                raise AIProviderError("API down")
            PIPELINE_STEPS[0] = ("step1_intake", bad_step)

            ctx = PipelineContext(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                identity="被诉方（被告）",
                goal="应诉答辩",
            )
            ctx = run_pipeline(ctx)
            assert any("AI" in e for e in ctx.errors)
        finally:
            PIPELINE_STEPS[:] = original_steps

    def test_critical_step_exception(self, tmp_path):
        """Exception in critical step should stop pipeline."""
        from core.pipeline import run_pipeline, PIPELINE_STEPS
        (tmp_path / "test.txt").write_text("内容" * 50, encoding="utf-8")

        original_steps = PIPELINE_STEPS.copy()
        try:
            def bad_step(ctx):
                raise RuntimeError("critical failure")
            # Step 1 is critical
            PIPELINE_STEPS[0] = ("step1_intake", bad_step)

            ctx = PipelineContext(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                identity="被诉方（被告）",
                goal="应诉答辩",
            )
            ctx = run_pipeline(ctx)
            assert any("未捕获异常" in e for e in ctx.errors)
        finally:
            PIPELINE_STEPS[:] = original_steps

    def test_non_critical_step_exception_continues(self, tmp_path):
        """Exception in non-critical step should continue pipeline."""
        from core.pipeline import run_pipeline, PIPELINE_STEPS
        (tmp_path / "test.txt").write_text("内容" * 50, encoding="utf-8")

        original_steps = PIPELINE_STEPS.copy()
        try:
            # Make step 7 (non-critical, index 6) raise
            def bad_step(ctx):
                raise RuntimeError("non-critical failure")
            PIPELINE_STEPS[6] = ("step7_render", bad_step)

            ctx = PipelineContext(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                identity="被诉方（被告）",
                goal="应诉答辩",
            )
            ctx = run_pipeline(ctx)
            # Pipeline should have errors and continue past the failed step
            assert len(ctx.errors) > 0
            assert len(ctx.logs) > 0
        finally:
            PIPELINE_STEPS[:] = original_steps

    def test_on_step_callback(self, tmp_path):
        """on_step callback should be called for each step."""
        from core.pipeline import run_pipeline
        (tmp_path / "test.txt").write_text("内容" * 50, encoding="utf-8")

        events = []
        def on_step(idx, name, event):
            events.append((idx, name, event))

        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(tmp_path / "out"),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )
        ctx = run_pipeline(ctx, on_step=on_step)

        # Should have start and done/failed events
        assert any(e[2] == "start" for e in events)
        assert any(e[2] in ("done", "failed") for e in events)

    def test_critical_step_errors_stop(self, tmp_path):
        """Errors accumulated in critical steps should stop pipeline."""
        from core.pipeline import run_pipeline, PIPELINE_STEPS
        (tmp_path / "test.txt").write_text("内容" * 50, encoding="utf-8")

        original_steps = PIPELINE_STEPS.copy()
        try:
            original_fn = PIPELINE_STEPS[0][1]
            def step_with_error(ctx):
                ctx.add_error("critical error")
                return ctx
            PIPELINE_STEPS[0] = ("step1_intake", step_with_error)

            ctx = PipelineContext(
                input_dir=str(tmp_path),
                output_dir=str(tmp_path / "out"),
                identity="被诉方（被告）",
                goal="应诉答辩",
            )
            ctx = run_pipeline(ctx)
            assert any("critical error" in e for e in ctx.errors)
        finally:
            PIPELINE_STEPS[:] = original_steps
