# -*- coding: utf-8 -*-
from unittest.mock import MagicMock

import pytest

from hmnextauto._scrollable import _swipe_in_bounds
from hmnextauto.proto import Bounds


def test_swipe_in_bounds_up_invokes_driver_swipe():
    uio = MagicMock()
    uio.bounds = Bounds(0, 0, 100, 200)
    uio._client = MagicMock()
    _swipe_in_bounds(uio, "up", speed=2000, extent=0.5)
    uio._client.invoke.assert_called_once()
    ca = uio._client.invoke.call_args
    assert ca[0][0] == "Driver.swipe"
    assert ca[1]["this"] == "Driver#0"
    args = ca[1]["args"]
    y1, y2 = args[1], args[3]
    assert y1 > y2  # finger moves upward
