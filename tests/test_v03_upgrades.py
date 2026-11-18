import json
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
async def test_mobile_companion_api_health_and_ask(tmp_path):
    orch = VoicePipelineOrchestrator()
    srv = MobileCompanionServer(orchestrator=orch, token="secret123")
    code_h, health = await srv.process_request("GET", "/v1/health", {}, b"")
    assert code_h == 200
    assert health["status"] == "ok"
    code_unauth, _ = await srv.process_request("POST", "/v1/ask", {}, b'{"query": "hello"}')
    assert code_unauth == 401

    headers = {"authorization": "Bearer secret123"}
    ask_payload = json.dumps({"query": "ตอนนี้กี่โมง"}).encode("utf-8")
    code_ask, ask_res = await srv.process_request("POST", "/v1/ask", headers, ask_payload)
    assert code_ask == 200
    assert "reply" in ask_res
    assert ask_res["requires_confirmation"] is False


@pytest.mark.asyncio
async def test_mobile_two_step_confirm(tmp_path):
    orch = VoicePipelineOrchestrator()
    srv = MobileCompanionServer(orchestrator=orch, token="secret123")
    headers = {"authorization": "Bearer secret123"}

    # 1. Sensitive action triggers confirmation request
    sens_payload = json.dumps({"query": "ลบไฟล์ขยะในระบบ"}).encode("utf-8")
    code, res = await srv.process_request("POST", "/v1/ask", headers, sens_payload)
    assert code == 200
    assert res["requires_confirmation"] is True
    confirm_id = res["confirm_id"]
    assert confirm_id

    # 2. Rejection via /v1/confirm
    cancel_payload = json.dumps({"confirm_id": confirm_id, "approved": False}).encode("utf-8")
    code_c, res_c = await srv.process_request("POST", "/v1/confirm", headers, cancel_payload)
    assert code_c == 200
    assert res_c["status"] == "cancelled"
    assert res_c["approved"] is False

    # 3. New sensitive action approved
    sens2_payload = json.dumps({"query": "ปิดเครื่องระบบ"}).encode("utf-8")
    code2, res2 = await srv.process_request("POST", "/v1/ask", headers, sens2_payload)
    confirm_id2 = res2["confirm_id"]
    approve_payload = json.dumps({"confirm_id": confirm_id2, "approved": True}).encode("utf-8")
    code_a, res_a = await srv.process_request("POST", "/v1/confirm", headers, approve_payload)
    assert code_a == 200
    assert res_a["status"] == "confirmed"
    assert res_a["approved"] is True
