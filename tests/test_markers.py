from packaging.markers import Marker

from passa.markers import get_without_extra


def test_strip_marker_extra_noop():
    marker = get_without_extra(
        Marker('os_name == "nt" or sys_platform == "Windows"'),
    )
    assert str(marker) == 'os_name == "nt" or sys_platform == "Windows"'


def test_strip_marker_none():
    marker = get_without_extra(None)
    assert marker is None


def test_strip_marker_extra_only():
    marker = get_without_extra(Marker('extra == "sock"'))
    assert marker is None


def test_strip_marker_extra_simple():
    marker = get_without_extra(Marker('os_name == "nt" and extra == "sock"'))
    assert str(marker) == 'os_name == "nt"'


def test_strip_marker_extra_nested():
    marker = get_without_extra(Marker(
        '(os_name == "nt" or sys_platform == "Windows") '
        'and extra == "sock"',
    ))
    assert str(marker) == 'os_name == "nt" or sys_platform == "Windows"'


def test_strip_marker_extra_crazy():
    marker = get_without_extra(Marker(
        '(os_name == "nt" or sys_platform == "Windows" and extra == "huh") '
        'and extra == "sock"',
    ))
    assert str(marker) == 'os_name == "nt" or sys_platform == "Windows"'
