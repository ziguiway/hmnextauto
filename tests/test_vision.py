# -*- coding: utf-8 -*-

import os


from hmnextauto._vision import find_image

def test_find_image_synthetic(tmp_path):
    result = find_image('E:\\code\\hmnextauto\\tests\\SnowShot_2026-04-24_14-00-59.png', 'E:\\code\\hmnextauto\\tests\\setting.png')
    assert result is not None
    assert result.score > 0.85
    assert result.x > 0
    assert result.y > 0
    assert result.w > 0
    assert result.h > 0
    assert result.center[0] > 0
    assert result.center[1] > 0
    

