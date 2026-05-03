# -*- coding: utf-8 -*-
"""Driver per-serial singleton: __del__ must not clear other devices' entries."""

from unittest.mock import MagicMock, patch

import pytest

from hmnextauto.driver import Driver


@pytest.fixture(autouse=True)
def _clean_driver_registry():
    Driver._instance.clear()
    yield
    Driver._instance.clear()


def _mock_hm_client():
    m = MagicMock()
    m.hdc = MagicMock()
    return m


@patch("hmnextauto.driver.HmClient")
@patch("hmnextauto.driver.list_devices", return_value=["AAA", "BBB"])
def test_close_one_driver_keeps_other_serial(mock_list, mock_hm_cls):
    """Closing one serial must not remove another from ``_instance``."""
    mock_hm_cls.side_effect = lambda serial: _mock_hm_client()

    da = Driver("AAA")
    db = Driver("BBB")
    assert set(Driver._instance.keys()) == {"AAA", "BBB"}
    assert Driver._instance["BBB"] is db

    da.close()

    assert "AAA" not in Driver._instance
    assert Driver._instance.get("BBB") is db
    assert Driver("BBB") is db


@patch("hmnextauto.driver.HmClient")
@patch("hmnextauto.driver.list_devices", return_value=["AAA", "BBB"])
def test_unregister_singleton_if_self_only_pops_own_slot(mock_list, mock_hm_cls):
    """``_unregister_singleton_if_self`` clears only this serial when slot matches."""
    mock_hm_cls.side_effect = lambda serial: _mock_hm_client()

    da = Driver("AAA")
    db = Driver("BBB")
    da._unregister_singleton_if_self()
    try:
        assert "AAA" not in Driver._instance
        assert Driver._instance["BBB"] is db
    finally:
        da._client.release()
        db.close()


@patch("hmnextauto.driver.HmClient")
@patch("hmnextauto.driver.list_devices", return_value=["AAA", "BBB"])
def test_close_removes_serial_and_new_driver_is_distinct(mock_list, mock_hm_cls):
    mock_hm_cls.side_effect = lambda serial: _mock_hm_client()

    da = Driver("AAA")
    id1 = id(da)
    da.close()

    assert "AAA" not in Driver._instance

    da2 = Driver("AAA")
    assert id(da2) != id1
    assert Driver._instance["AAA"] is da2


@patch("hmnextauto.driver.HmClient")
@patch("hmnextauto.driver.list_devices", return_value=["AAA"])
def test_double_close_idempotent(mock_list, mock_hm_cls):
    mock_hm_cls.side_effect = lambda serial: _mock_hm_client()

    da = Driver("AAA")
    da.close()
    da.close()
    assert "AAA" not in Driver._instance
