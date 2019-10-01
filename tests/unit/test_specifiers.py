import pytest

from packaging.specifiers import SpecifierSet

from passa.internals.specifiers import cleanup_pyspecs, PySpecs


@pytest.mark.parametrize("spec, cleaned", [
    # == and ~= don't matter.
    ("~=3.0", [("~=", "3.0")]),
    ("==2.7", [("==", "2.7")]),

    # >= and < should be kept.
    (">=3.0", [(">=", "3.0")]),
    ("<3.5", [("<", "3.5")]),

    # > and <= should be converted to >= and <.
    (">3.0", [(">=", "3.1")]),
    (">=2.7,<=3.3", [(">=", "2.7"), ("<", "3.4")]),
    (">2.6,!=3.0,!=3.1,!=3.2", [(">=", "2.7"), ("not in", "3.0, 3.1, 3.2")]),

    # The result should be dedup-ed.
    (
        ">2.6,>=2.7,<=3.3,<3.4,!=3.0,!=3.1,!=3.2",
        [(">=", "2.7"), ("<", "3.4"), ("not in", "3.0, 3.1, 3.2")],
    ),
])
def test_cleanup_pyspecs(spec, cleaned):
    cleaned_specifierset = frozenset(s for s in cleaned)
    assert cleanup_pyspecs(SpecifierSet(spec)) == cleaned_specifierset


@pytest.mark.parametrize("left, right, result", [
    ("", ">=3.6", ">=3.6"),
    (">=2.7,!=3.0,!=3.1,!=3.2,!=3.3", ">=3.6", "!=3.0,!=3.1,!=3.2,!=3.3,>=3.6"),
    ("<3.0", ">=3.3", "<3.0,>=3.3"),
    ("==3.7", ">=3.6", "==3.7,>=3.6")
])
def test_pyspecs_and_operator(left, right, result):
    left = PySpecs(SpecifierSet(left))
    right = PySpecs(SpecifierSet(right))
    rv = left & right
    assert str(rv.specifierset) == result


@pytest.mark.parametrize("left, right, result", [
    ("", ">=3.6", ">=3.6"),
    (">=2.7,!=3.0,!=3.1,!=3.2,!=3.3", ">=3.6", "!=3.0,!=3.1,!=3.2,!=3.3,>=2.7"),
    ("==2.7", ">=3.4", "!=3.0,!=3.1,!=3.2,!=3.3,>=2.7"),
    (">=2.6,<3.0", ">=3.3,<3.6", "!=3.0,!=3.1,!=3.2,<3.6,>=2.6"),
    ("~=3.0", ">=2.7", ">=2.7")
])
def test_pyspecs_or_operator(left, right, result):
    left = PySpecs(SpecifierSet(left))
    right = PySpecs(SpecifierSet(right))
    rv = left | right
    assert str(rv.specifierset) == result


@pytest.mark.parametrize("spec, marker", [
    ("", ""),
    (">=3.3,<3.7", 'python_version < "3.7" and python_version >= "3.3"')
])
def test_pyspecs_to_marker(spec, marker):
    pyspec = PySpecs(SpecifierSet(spec))
    assert str(pyspec) == marker
