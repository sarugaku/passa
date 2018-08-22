import pytest

from packaging.specifiers import Specifier, SpecifierSet

from passa.markers import cleanup_specs


@pytest.mark.parametrize("spec, cleaned", [
    (">=3.0", {">=3.0"}),
    (">3.0", {">=3.1"}),
    ("~=3.0", {"~=3.0"}),
    (">=2.7,<3.4", {">=2.7", "<=3.3"}),
    (">=2.7,!=3.0,!=3.1,!=3.2", {">=2.7", "!=3.0", "!=3.1", "!=3.2"}),
])
def test_cleanup_specs(spec, cleaned):
    cleaned = {Specifier(s) for s in cleaned}
    assert cleanup_specs(SpecifierSet(spec)) == cleaned
