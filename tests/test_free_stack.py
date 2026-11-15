"""Contract tests for 100% Free Stack providers."""

import pytest
from javis.providers.free_stack import FreeTierLLMClient, FreeTierSTTClient


@pytest.mark.asyncio
async def test_free_llm_client_fallback_without_key():
    client = FreeTierLLMClient(api_key="")
    res = await client.generate_response("ทดสอบ")
    assert "ยังไม่ได้ตั้งค่า Free API Key" in res


@pytest.mark.asyncio
async def test_free_stt_client_fallback_without_key():
    client = FreeTierSTTClient(api_key="")
    res = await client.transcribe(b"fake_wav_data")
    assert res is None
