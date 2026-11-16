import pytest
from unittest.mock import AsyncMock
from javis.core.memory import MemoryStore
from javis.core.policy import ToolPolicyEngine
from javis.ui.mobile_api import MobileCompanionServer
from javis.core.daemon import VoicePipelineOrchestrator


def test_sqlite_memory_rolling_turns_and_audit(tmp_path):
    store = MemoryStore(db_path=str(tmp_path / "memory.db"), max_turns=2)
    store.add_turn("user", "q1")
    store.add_turn("assistant", "a1")
    store.add_turn("user", "q2")
    store.add_turn("assistant", "a2")
    store.add_turn("user", "q3")
    store.add_turn("assistant", "a3")
    recent = store.get_recent_turns()
    assert len(recent) == 4
    assert recent[0]["content"] == "q2"
    store.log_tool_execution("mute_volume", {"mute": True}, "SAFE", True, True, "Muted")
    logs = store.get_recent_audit_logs(limit=5)
    assert len(logs) == 1
    assert logs[0]["tool_name"] == "mute_volume"


@pytest.mark.asyncio
async def test_policy_engine_safe_vs_sensitive_zenity_gate(tmp_path):
    store = MemoryStore(db_path=str(tmp_path / "policy.db"))
    deny_confirm = AsyncMock(return_value=False)
    policy_deny = ToolPolicyEngine(memory=store, confirm_fn=deny_confirm)
    ok_safe, _ = await policy_deny.execute_tool("get_time", {})
    assert ok_safe is True
    ok_sens, _ = await policy_deny.execute_tool("life_log_action", {"type": "task", "detail": "physics"})
    assert ok_sens is False


@pytest.mark.asyncio
async def test_mobile_companion_api(tmp_path):
    orch = VoicePipelineOrchestrator()
    srv = MobileCompanionServer(orchestrator=orch, token="secret123")
    code_h, health = await srv.process_request("GET", "/v1/health", {}, b"")
    assert code_h == 200
    assert health["status"] == "ok"
    code_unauth, _ = await srv.process_request("POST", "/v1/ask", {}, b'{"query": "hello"}')
    assert code_unauth == 401
