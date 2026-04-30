# -*- coding: utf-8 -*-
"""
XPath 功能增强测试
测试: count, all(), first(), last()
"""

import pytest
import time
from hmnextauto.driver import Driver


@pytest.fixture
def d():
    """获取 Driver 实例"""
    d = Driver()
    yield d
    d.close()


def test_xpath_count(d):
    """测试 count 属性"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    count = d.xpath('//*[@clickable="true"]').count

    # 严格断言
    assert isinstance(count, int), "count must be int type"
    assert count > 0, "count should > 0 (settings page has clickable elements)"


def test_xpath_all(d):
    """测试 all() 方法"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    count = d.xpath('//*[@clickable="true"]').count
    elements = d.xpath('//*[@clickable="true"]').all()

    # 严格断言
    assert isinstance(elements, list), "all() must return list"
    assert len(elements) == count, "all() length should equal count"

    for i, el in enumerate(elements):
        assert hasattr(el, "bounds"), f"element {i} must have bounds"
        assert hasattr(el, "exists"), f"element {i} must have exists method"
        assert hasattr(el, "click"), f"element {i} must have click method"
        assert el.exists(), f"element {i} should exist"
        assert el.bounds is not None, f"element {i} bounds should not be None"


def test_xpath_first(d):
    """测试 first() 方法"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    elements = d.xpath('//*[@clickable="true"]').all()
    first_el = d.xpath('//*[@clickable="true"]').first()

    # 严格断言
    assert hasattr(first_el, "bounds"), "first() must have bounds"
    assert hasattr(first_el, "exists"), "first() must have exists method"
    assert first_el.exists(), "first() should return existing element"
    assert first_el.bounds is not None, "first() bounds should not be None"
    assert first_el.bounds == elements[0].bounds, "first() should equal all()[0]"


def test_xpath_last(d):
    """测试 last() 方法"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    elements = d.xpath('//*[@clickable="true"]').all()
    last_el = d.xpath('//*[@clickable="true"]').last()

    # 严格断言
    assert hasattr(last_el, "bounds"), "last() must have bounds"
    assert hasattr(last_el, "exists"), "last() must have exists method"
    assert last_el.exists(), "last() should return existing element"
    assert last_el.bounds is not None, "last() bounds should not be None"
    assert last_el.bounds == elements[-1].bounds, "last() should equal all()[-1]"


def test_xpath_first_last_different(d):
    """测试 first 和 last 不同"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    count = d.xpath('//*[@clickable="true"]').count
    first_el = d.xpath('//*[@clickable="true"]').first()
    last_el = d.xpath('//*[@clickable="true"]').last()

    if count > 1:
        assert first_el.bounds != last_el.bounds, "When count > 1, first and last should differ"


def test_xpath_no_match_count(d):
    """测试无匹配时的 count"""
    d.go_home()
    time.sleep(0.5)

    no_match_count = d.xpath('//*[@text="nonexistent_xyz"]').count
    assert no_match_count == 0, "No match count should be 0"


def test_xpath_no_match_all(d):
    """测试无匹配时的 all()"""
    d.go_home()
    time.sleep(0.5)

    no_match_all = d.xpath('//*[@text="nonexistent_xyz"]').all()

    assert isinstance(no_match_all, list), "No match all() should still return list"
    assert len(no_match_all) == 0, "No match all() should return empty list"


def test_xpath_no_match_first(d):
    """测试无匹配时的 first()"""
    d.go_home()
    time.sleep(0.5)

    no_match_first = d.xpath('//*[@text="nonexistent_xyz"]').first()

    assert hasattr(no_match_first, "exists"), "No match first() should have exists"
    assert not no_match_first.exists(), "No match first() should not exist"
    assert no_match_first.bounds is None, "No match first() bounds should be None"


def test_xpath_no_match_last(d):
    """测试无匹配时的 last()"""
    d.go_home()
    time.sleep(0.5)

    no_match_last = d.xpath('//*[@text="nonexistent_xyz"]').last()

    assert hasattr(no_match_last, "exists"), "No match last() should have exists"
    assert not no_match_last.exists(), "No match last() should not exist"
    assert no_match_last.bounds is None, "No match last() bounds should be None"


def test_xpath_info_is_dict(d):
    """测试 info 返回 dict"""
    d.go_home()
    time.sleep(0.5)

    d.start_app("com.huawei.hmos.settings")
    time.sleep(2)

    elements = d.xpath('//*[@clickable="true"]').all()

    for i, el in enumerate(elements[:5]):
        info = el.info
        assert isinstance(info, dict), f"element {i} info should be dict"


if __name__ == "__main__":
    d = Driver()

    print("=" * 60)
    print("XPath Enhancement Tests")
    print("=" * 60)

    print("\n1. count test")
    test_xpath_count(d)

    print("\n2. all() test")
    test_xpath_all(d)

    print("\n3. first() test")
    test_xpath_first(d)

    print("\n4. last() test")
    test_xpath_last(d)

    print("\n5. first/last different test")
    test_xpath_first_last_different(d)

    print("\n6. no match tests")
    test_xpath_no_match_count(d)
    test_xpath_no_match_all(d)
    test_xpath_no_match_first(d)
    test_xpath_no_match_last(d)

    print("\n7. info is dict test")
    test_xpath_info_is_dict(d)

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

    d.close()