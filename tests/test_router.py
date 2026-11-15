"""Tests for Local Fast-Path Router (single-intent vs compound bypass)."""

import pytest
from javis.core.router import FastPathRouter


def test_fast_path_single_intent():
    router = FastPathRouter()
    
    # Single-intent time query
    res = router.route("กี่โมงแล้ว")
    assert res.matched is True
    assert "เวลา" in res.speech_response

    # Date query
    res = router.route("วันนี้วันอะไร")
    assert res.matched is True
    assert "วันนี้คือ" in res.speech_response

    # Battery query
    res = router.route("เช็คแบต")
    assert res.matched is True
    assert res.action == "get_battery"

    # System status query
    res = router.route("สถานะเครื่อง")
    assert res.matched is True
    assert res.action == "get_system_status"

    # Volume command
    res = router.route("ลดเสียง")
    assert res.matched is True
    assert res.action == "set_volume"

    # Web search
    res = router.route("ค้นหา ราคาบิตคอยน์")
    assert res.matched is True
    assert res.action == "search_web"


def test_fast_path_compound_bypass():
    router = FastPathRouter()

    # Compound query with conjunction "แล้ว"
    res = router.route("เปิด VS Code แล้วสรุปงานให้หน่อย")
    assert res.matched is False  # Must bypass to Tier 2 (Hermes)

    # Compound query with conjunction "และ"
    res = router.route("ปิดเพลงและดูสภาพอากาศ")
    assert res.matched is False  # Must bypass to Tier 2 (Hermes)

    # Long text query (> 35 characters)
    long_query = "ช่วยตรวจสอบข้อมูลสภาพการจราจรแถวอโศกและแจ้งเตือนถ้าฝนจะตก"
    assert router.is_compound(long_query) is True
    res = router.route(long_query)
    assert res.matched is False
