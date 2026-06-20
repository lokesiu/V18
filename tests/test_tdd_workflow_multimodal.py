"""TDD tests for multimodal, multimodal_router, dual_ai_orchestrator, events, stages."""
import pytest
import sys, os, base64
from unittest.mock import patch, MagicMock, AsyncMock
sys.path.insert(0, ".")

from core.fact_card import PipelineContext, FactCard, Party


# ══════════════════════════════════════════════════════════════════════
# workflow/events.py
# ══════════════════════════════════════════════════════════════════════
class TestEvents:
    def test_workflow_event_defaults(self):
        from core.workflow.events import WorkflowEvent
        e = WorkflowEvent(stage_name="test")
        assert e.stage_name == "test"
        assert e.status == "pending"
        assert e.is_ai is False

    def test_event_bus_emit(self):
        from core.workflow.events import EventBus, WorkflowEvent
        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))
        e = WorkflowEvent(stage_name="test", status="done")
        bus.emit(e)
        assert len(received) == 1
        assert received[0].status == "done"

    def test_event_bus_multiple_listeners(self):
        from core.workflow.events import EventBus, WorkflowEvent
        bus = EventBus()
        r1, r2 = [], []
        bus.subscribe(lambda e: r1.append(e))
        bus.subscribe(lambda e: r2.append(e))
        bus.emit(WorkflowEvent(stage_name="test"))
        assert len(r1) == 1
        assert len(r2) == 1

    def test_event_bus_listener_exception_swallowed(self):
        from core.workflow.events import EventBus, WorkflowEvent
        bus = EventBus()
        bus.subscribe(lambda e: 1/0)  # raises
        bus.subscribe(lambda e: None)
        # Should not raise
        bus.emit(WorkflowEvent(stage_name="test"))


# ══════════════════════════════════════════════════════════════════════
# workflow/stages.py
# ══════════════════════════════════════════════════════════════════════
class TestStages:
    def test_dual_ai_stages_count(self):
        from core.workflow.stages import DUAL_AI_STAGES
        assert len(DUAL_AI_STAGES) == 9

    def test_stage_names(self):
        from core.workflow.stages import DUAL_AI_STAGES
        names = [s.name for s in DUAL_AI_STAGES]
        assert "intake" in names
        assert "deepseek_extract" in names
        assert "mimo_critique" in names
        assert "render" in names
        assert "quality_gate" in names

    def test_ai_stages(self):
        from core.workflow.stages import DUAL_AI_STAGES
        ai_stages = [s for s in DUAL_AI_STAGES if s.requires_ai]
        assert len(ai_stages) >= 2
        for s in ai_stages:
            assert s.ai_provider in ("deepseek", "mimo")


# ══════════════════════════════════════════════════════════════════════
# ai/multimodal.py — utility functions
# ══════════════════════════════════════════════════════════════════════
class TestMultimodal:
    def test_classify_file_text(self, tmp_path):
        from core.ai.multimodal import classify_file, FileCategory
        assert classify_file(str(tmp_path / "a.pdf")) == FileCategory.TEXT
        assert classify_file(str(tmp_path / "a.docx")) == FileCategory.TEXT
        assert classify_file(str(tmp_path / "a.txt")) == FileCategory.TEXT

    def test_classify_file_image(self, tmp_path):
        from core.ai.multimodal import classify_file, FileCategory
        assert classify_file(str(tmp_path / "a.jpg")) == FileCategory.IMAGE
        assert classify_file(str(tmp_path / "a.png")) == FileCategory.IMAGE

    def test_classify_file_audio(self, tmp_path):
        from core.ai.multimodal import classify_file, FileCategory
        assert classify_file(str(tmp_path / "a.mp3")) == FileCategory.AUDIO
        assert classify_file(str(tmp_path / "a.wav")) == FileCategory.AUDIO

    def test_classify_file_unknown(self, tmp_path):
        from core.ai.multimodal import classify_file, FileCategory
        assert classify_file(str(tmp_path / "a.xyz")) == FileCategory.UNKNOWN

    def test_classify_files(self, tmp_path):
        from core.ai.multimodal import classify_files, FileCategory
        paths = [str(tmp_path / "a.pdf"), str(tmp_path / "b.jpg"), str(tmp_path / "c.mp3")]
        result = classify_files(paths)
        assert len(result[FileCategory.TEXT]) == 1
        assert len(result[FileCategory.IMAGE]) == 1
        assert len(result[FileCategory.AUDIO]) == 1

    def test_encode_image_base64_valid(self, tmp_path):
        from core.ai.multimodal import encode_image_base64
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # fake JPEG header
        result = encode_image_base64(str(img))
        assert result is not None
        assert result.startswith("data:image/jpeg;base64,")

    def test_encode_image_base64_nonexistent(self):
        from core.ai.multimodal import encode_image_base64
        assert encode_image_base64("/nonexistent.jpg") is None

    def test_encode_image_base64_png(self, tmp_path):
        from core.ai.multimodal import encode_image_base64
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG" + b"\x00" * 100)
        result = encode_image_base64(str(img))
        assert result is not None
        assert "image/png" in result

    def test_build_vision_message(self, tmp_path):
        from core.ai.multimodal import build_vision_message
        img = tmp_path / "test.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 10)
        msg = build_vision_message([str(img)], "分析图片")
        assert msg["role"] == "user"
        assert isinstance(msg["content"], list)
        assert len(msg["content"]) >= 2  # text + image

    def test_build_vision_message_empty(self):
        from core.ai.multimodal import build_vision_message
        msg = build_vision_message([], "分析")
        assert len(msg["content"]) == 1  # text only


# ══════════════════════════════════════════════════════════════════════
# ai/multimodal_router.py
# ══════════════════════════════════════════════════════════════════════
class TestMultimodalRouter:
    def test_route_result(self):
        from core.ai.multimodal_router import RouteResult
        r = RouteResult(success=True, content="ok", mode_used="deepseek")
        assert r.success is True
        assert r.mimo_multimodal_used is False

    def test_route_mode_constants(self):
        from core.ai.multimodal_router import RouteMode
        assert RouteMode.PREVIEW == "preview"
        assert RouteMode.DEEPSEEK_ONLY == "deepseek"
        assert RouteMode.MIMO_ONLY == "mimo"
        assert RouteMode.DUAL_AI == "dual_ai"


# ══════════════════════════════════════════════════════════════════════
# dual_ai_orchestrator.py — mock clients
# ══════════════════════════════════════════════════════════════════════
class TestDualAIOrchestrator:
    def _make_mock_ds(self, success=True):
        """Create mock DeepSeek client."""
        from core.ai.deepseek_client import APIResponse
        ds = MagicMock()
        ds.is_configured = True
        ds.extract_facts.return_value = APIResponse(
            success=success,
            content='{"case_id":"C1","court":"法院","key_facts":["事实1"]}' if success else "",
            latency_ms=100,
            model="deepseek-chat",
            error=None if success else "timeout",
        )
        ds.generate_strategy.return_value = APIResponse(
            success=success,
            content='{"situation_assessment":"评估","sabcd_rating":"B","action_advice":[{"action":"做X","priority":"S","reasoning":"因为"}],"evidence_gap":[],"risk_warnings":[]}' if success else "",
            latency_ms=200,
            model="deepseek-chat",
            error=None if success else "timeout",
        )
        return ds

    def _make_mock_mm(self, success=True):
        """Create mock MiMo client."""
        from core.ai.mimo_client import APIResponse
        mm = MagicMock()
        mm.is_configured = True
        mm.critique_facts.return_value = APIResponse(
            success=success, content="ok", latency_ms=100, model="mimo",
        )
        mm.review_strategy.return_value = APIResponse(
            success=success, content="ok", latency_ms=100, model="mimo",
        )
        return mm

    def test_init(self):
        from core.workflow.dual_ai_orchestrator import DualAIOrchestrator
        orch = DualAIOrchestrator()
        assert orch.ds is None
        assert orch.mm is None

    def test_run_with_mock_clients(self, tmp_path):
        from core.workflow.dual_ai_orchestrator import DualAIOrchestrator
        from core.intake import run_intake

        # Create test input
        (tmp_path / "test.txt").write_text("原告张三诉被告李四借款合同纠纷" * 30, encoding="utf-8")
        out = tmp_path / "output"
        out.mkdir()

        ds = self._make_mock_ds()
        mm = self._make_mock_mm()

        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(out),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )

        orch = DualAIOrchestrator(deepseek_client=ds, mimo_client=mm)
        ctx = orch.run(ctx)

        assert ctx.fact_card is not None
        assert ctx.strategy_card is not None

    def test_run_skip_unconfigured_provider(self, tmp_path):
        """Unconfigured providers should be skipped."""
        from core.workflow.dual_ai_orchestrator import DualAIOrchestrator

        (tmp_path / "test.txt").write_text("内容" * 30, encoding="utf-8")
        out = tmp_path / "output"
        out.mkdir()

        ds = self._make_mock_ds()
        mm = MagicMock()
        mm.is_configured = False  # Not configured

        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(out),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )

        orch = DualAIOrchestrator(deepseek_client=ds, mimo_client=mm)
        ctx = orch.run(ctx)
        # Should complete without crashing
        assert ctx is not None

    def test_run_no_clients(self, tmp_path):
        """No clients at all → skip AI stages."""
        from core.workflow.dual_ai_orchestrator import DualAIOrchestrator

        (tmp_path / "test.txt").write_text("内容" * 30, encoding="utf-8")
        out = tmp_path / "output"
        out.mkdir()

        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(out),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )

        orch = DualAIOrchestrator(deepseek_client=None, mimo_client=None)
        ctx = orch.run(ctx)
        assert ctx is not None

    def test_run_ds_extract_failure(self, tmp_path):
        """DeepSeek extract failure should be handled."""
        from core.workflow.dual_ai_orchestrator import DualAIOrchestrator

        (tmp_path / "test.txt").write_text("内容" * 30, encoding="utf-8")
        out = tmp_path / "output"
        out.mkdir()

        ds = self._make_mock_ds(success=False)
        mm = self._make_mock_mm()

        ctx = PipelineContext(
            input_dir=str(tmp_path),
            output_dir=str(out),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )

        orch = DualAIOrchestrator(deepseek_client=ds, mimo_client=mm)
        ctx = orch.run(ctx)
        assert ctx is not None

    def test_run_intake_critical_breaks_on_failure(self, tmp_path):
        """Intake failure should break the pipeline."""
        from core.workflow.dual_ai_orchestrator import DualAIOrchestrator

        out = tmp_path / "output"
        out.mkdir()

        ctx = PipelineContext(
            input_dir=str(tmp_path / "nonexistent"),
            output_dir=str(out),
            identity="被诉方（被告）",
            goal="应诉答辩",
        )

        orch = DualAIOrchestrator()
        ctx = orch.run(ctx)
        # Should stop after intake failure
        assert len(ctx.errors) > 0 or ctx.fact_card is None


# ══════════════════════════════════════════════════════════════════════
# ai_manifest.py
# ══════════════════════════════════════════════════════════════════════
class TestDualAIManifest:
    def test_manifest_init(self):
        from core.ai.ai_manifest import DualAIManifest
        m = DualAIManifest()
        assert m is not None

    def test_manifest_lifecycle(self, tmp_path):
        from core.ai.ai_manifest import DualAIManifest
        m = DualAIManifest()
        m.start_stage("intake")
        m.end_stage("intake", True, 100, "model", None, None)
        m.skip_stage("mimo_critique", "not configured")
        m.finish()
        m.save(str(tmp_path))
        assert (tmp_path / "_internal" / "ai_run_manifest.json").exists()
