import pytest

from packaging.specifiers import Specifier, SpecifierSet

from passa.markers import cleanup_specs


@pytest.mark.parametrize("spec, cleaned", [
    (">=3.0", {">=3.0"}),
    (">3.0", {">=3.1"}),
    ("~=3.0", {"~=3.0"}),
    # <=3.3 should convert to <3.4
    (">=2.7,<=3.3", {">=2.7", "<3.4"}),
    # >2.6 should convert to >=2.7
    (">2.6,!=3.0,!=3.1,!=3.2", {">=2.7", "!=3.0", "!=3.1", "!=3.2"}),
    (">2.6,>=2.7,<=3.3,<3.4,!=3.0,!=3.1,!=3.2", {">=2.7", "<3.4", "!=3.0", "!=3.1", "!=3.2"}),
])
def test_cleanup_specs(spec, cleaned):
    # cleaned_specifierset = SpecifierSet(",".join(list(cleaned)))
    cleaned_specifierset = frozenset({Specifier(s) for s in cleaned})
    assert cleanup_specs(SpecifierSet(spec)) == cleaned_specifierset
