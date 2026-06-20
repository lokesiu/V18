"""Smoke tests for remaining untested modules (import + basic instantiation)."""
import pytest
import sys
sys.path.insert(0, ".")


class TestAIImports:
    """Verify AI modules import without crashing."""

    def test_import_ai_manifest(self):
        from core.ai import ai_manifest
        assert ai_manifest is not None

    def test_import_deepseek_client(self):
        from core.ai import deepseek_client
        assert deepseek_client is not None

    def test_import_mimo_client(self):
        from core.ai import mimo_client
        assert mimo_client is not None

    def test_import_multimodal(self):
        from core.ai import multimodal
        assert multimodal is not None

    def test_import_multimodal_router(self):
        from core.ai import multimodal_router
        assert multimodal_router is not None

    def test_import_provider_registry(self):
        from core.ai import provider_registry
        assert provider_registry is not None

    def test_import_unified_client(self):
        from core.ai import unified_client
        assert unified_client is not None


class TestWorkflowImports:
    """Verify workflow modules import without crashing."""

    def test_import_dual_ai_orchestrator(self):
        from core.workflow import dual_ai_orchestrator
        assert dual_ai_orchestrator is not None

    def test_import_events(self):
        from core.workflow import events
        assert events is not None

    def test_import_stages(self):
        from core.workflow import stages
        assert stages is not None


class TestContractImports:
    """Verify contract modules import without crashing."""

    def test_import_ai_provider(self):
        from core.contracts import ai_provider
        assert ai_provider is not None

    def test_import_workflow_stage(self):
        from core.contracts import workflow_stage
        assert workflow_stage is not None


class TestScenarioImports:
    """Verify scenario modules import without crashing."""

    def test_import_scenario_registry(self):
        from core.scenario import scenario_registry
        assert scenario_registry is not None


class TestStep3FactApiA:
    """Test step3_fact_api_a basic flow."""

    def test_import(self):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a
        assert callable(step3_fact_api_a)

    def test_no_fact_card(self):
        from core.pipeline.step3_fact_api_a import step3_fact_api_a
        from core.fact_card import PipelineContext
        ctx = PipelineContext()
        ctx = step3_fact_api_a(ctx)
        assert len(ctx.errors) > 0


class TestStep4StrategyApiB:
    """Test step4_strategy_api_b basic flow."""

    def test_import(self):
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b
        assert callable(step4_strategy_api_b)

    def test_no_fact_card(self):
        from core.pipeline.step4_strategy_api_b import step4_strategy_api_b
        from core.fact_card import PipelineContext
        ctx = PipelineContext()
        ctx = step4_strategy_api_b(ctx)
        assert len(ctx.errors) > 0


class TestUnifiedClient:
    """Test core.ai.unified_client basic functionality."""

    def test_import(self):
        from core.ai.unified_client import UnifiedAIClient, ProviderConfig
        assert callable(UnifiedAIClient)

    def test_provider_config(self):
        from core.ai.unified_client import ProviderConfig
        config = ProviderConfig(
            name="test",
            api_key="key",
            base_url="http://localhost",
            model="test-model",
        )
        assert config.name == "test"


class TestMultimodal:
    """Test core.ai.multimodal basic functionality."""

    def test_import(self):
        from core.ai.multimodal import encode_image_base64
        assert callable(encode_image_base64)

    def test_encode_nonexistent(self):
        from core.ai.multimodal import encode_image_base64
        result = encode_image_base64("/nonexistent/image.jpg")
        assert result is None or result == ""
