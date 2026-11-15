"""Test Life & Study Manager Integration and Fast-Path Routing."""

import pytest
from unittest.mock import patch, MagicMock
from javis.core.router import FastPathRouter
from javis.integrations.life_manager import LifeManagerClient


def test_life_manager_open_route():
    router = FastPathRouter()
    
    with patch("javis.integrations.life_manager.LifeManagerClient.open_web_app", return_value=True):
        res1 = router.route("เปิด Life Manager")
        assert res1.matched is True
        assert res1.action == "open_life_manager"
        assert "เปิดระบบจัดการชีวิตและการเรียน" in res1.speech_response

        res2 = router.route("เปิดระบบการเรียน")
        assert res2.matched is True
        assert res2.action == "open_life_manager"

        res3 = router.route("เปิดตารางเรียน")
        assert res3.matched is True
        assert res3.action == "open_life_manager"


def test_life_manager_briefing_route():
    router = FastPathRouter()
    mock_briefing = "สวัสดีครับ วันนี้มีภารกิจค้างทำ 0 งาน, การบ้านรอส่ง 6 งาน"

    with patch("javis.integrations.life_manager.LifeManagerClient.get_briefing", return_value=mock_briefing):
        res = router.route("บรีฟงานวันนี้")
        assert res.matched is True
        assert res.action == "life_briefing"
        assert res.speech_response == mock_briefing

        res2 = router.route("มีงานค้างไหม")
        assert res2.matched is True
        assert res2.action == "life_briefing"
        assert res2.speech_response == mock_briefing


def test_life_manager_client_api():
    client = LifeManagerClient()
    # Test real API call directly (with quick timeout)
    briefing = client.get_briefing(timeout_sec=5.0)
    assert briefing is not None
    assert "สวัสดีครับ" in briefing or "ภารกิจ" in briefing
