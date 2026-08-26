# -*- coding: utf-8 -*-

import pytest
from unittest.mock import MagicMock, patch

from hmnextauto.driver import Driver
from hmnextauto._uiobject import UiObject
from hmnextauto.proto import ElementInfo, ComponentData, HypiumResponse


@pytest.fixture
def d():
    d = Driver("FMR0223C13000649")
    d.force_start_app("com.samples.test.uitest", "EntryAbility")
    yield d
    del d


def test_by_type(d):
    d(type="Button")


def test_by_combine(d):
    assert d(type="Button", text="showToast").exists()
    assert not d(type="Button", text="showToast1").exists()
    assert d(type="Button", index=3).exists()
    assert not d(type="Button", index=5).exists()


def test_wait(d):
    assert d(type="Button", text="showToast").wait(timeout=5.0) is True
    assert d(type="Button", text="no_such_button_xyz").wait(timeout=0.5) is False


def test_wait_gone(d):
    assert d(type="Button", text="no_such_button_xyz").wait_gone(timeout=0.2) is True
    assert d(type="Button", text="showToast").wait_gone(timeout=0.2) is False


def test_isBefore_isAfter(d):
    assert d(text="showToast", isAfter=True).text == "showDialog"
    # assert d(id="drag", isBefore=True).text == "showDialog"


def test_count(d):
    assert d(type="Button").count == 5
    assert len(d(type="Button")) == 5


def test_id(d):
    assert d(text="showToast").text == "showToast"


def test_info(d):
    info: ElementInfo = d(text="showToast").info
    mock = {
        "id": "",
        "key": "",
        "type": "Button",
        "text": "showToast",
        "description": "",
        "isSelected": False,
        "isChecked": False,
        "isEnabled": True,
        "isFocused": False,
        "isCheckable": False,
        "isClickable": True,
        "isLongClickable": False,
        "isScrollable": False,
        "bounds": {
            "left": 539,
            "top": 1282,
            "right": 832,
            "bottom": 1412
        },
        "boundsCenter": {
            "x": 685,
            "y": 1347
        }
    }
    assert info.to_dict() == mock


def test_click(d):
    d(text="showToast1").click_if_exists()
    d(text="showToast").click()
    d(type="Button", index=3).click()
    d.click(0.5, 0.2)


def test_double_click(d):
    d(text="unit_jsunit").double_click()
    assert d(id="swiper").exists()
    d.go_back()


def test_long_click(d):
    d(text="showToast").long_click()


def test_drag_to(d):
    d(id="drag").click()
    assert d(type="Text", index=6).text == "two"

    component: ComponentData = d(type="ListItem", index=1).find_component()
    d(type="ListItem").drag_to(component)
    assert d(type="Text", index=5).text == "two"


def test_input(d):
    d(text="showToast").input_text("abc")
    d(text="showToast").clear_text()


@patch("hmnextauto.utils.time.sleep")
def test_uiobject_clear_text_uses_driver_cleartext(mock_sleep):
    """No-device: selector clear_text uses Driver.clearText (full-clear), not Component.clearText."""
    client = MagicMock()
    client.invoke.side_effect = [
        HypiumResponse("On#1"),
        HypiumResponse(None),
    ]
    obj = UiObject(client, text="10.14")
    obj.clear_text()

    apis = [c.args[0] for c in client.invoke.call_args_list]
    assert "Driver.clearText" in apis
    assert "Component.clearText" not in apis
    client.invoke.assert_any_call(
        "Driver.clearText", this="Driver#0", args=["On#1"]
    )


def test_pinch(d):
    d(text="showToast").pinch_in()
    d(text="showToast").pinch_out()
