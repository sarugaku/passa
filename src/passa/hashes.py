import contextlib

from pip_shims import Wheel


def _wheel_supported(self, tags=None):
    # Ignore current platform. Support everything.
    return True


def _wheel_support_index_min(self, tags=None):
    # All wheels are equal priority for sorting.
    return 0


@contextlib.contextmanager
def _allow_all_wheels():
    """Monkey patch pip.Wheel to allow all wheels

    The usual checks against platforms and Python versions are ignored to allow
    fetching all available entries in PyPI. This also saves the candidate cache
    and set a new one, or else the results from the previous non-patched calls
    will interfere.
    """
    original_wheel_supported = Wheel.supported
    original_support_index_min = Wheel.support_index_min

    Wheel.supported = _wheel_supported
    Wheel.support_index_min = _wheel_support_index_min
    yield
    Wheel.supported = original_wheel_supported
    Wheel.support_index_min = original_support_index_min


def get_hashes(cache, req):
    ireq = req.as_ireq()
    if req.is_vcs or ireq.editable or not ireq.is_pinned:
        return set()

    matching_candidates = set()
    with _allow_all_wheels():
        matching_candidates = req.find_all_matches()

    return {
        cache.get_hash(candidate.location)
        for candidate in matching_candidates
    }
