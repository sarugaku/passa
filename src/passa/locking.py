import contextlib

from requirementslib._compat import VcsSupport, Wheel
from resolvelib import Resolver

from .caches import HashCache
from .providers import RequirementsLibProvider
from .reporters import StdOutReporter
from .traces import trace_graph


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


def _get_hashes(cache, req):
    ireq = req.as_ireq()
    if ireq.editable or not ireq.is_pinned:
        return set()

    vcs = VcsSupport()
    if (ireq.link and
            ireq.link.scheme in vcs.all_schemes and
            'ssh' in ireq.link.scheme):
        return set()

    matching_candidates = set()
    with _allow_all_wheels():
        matching_candidates = req.find_all_matches()

    return {
        cache.get_hash(candidate.location)
        for candidate in matching_candidates
    }


def lock(requirements):
    """Lock specified (abstract) requirements into (concrete) candidates.

    The locking procedure consists of four stages:

    * Resolve versions and dependency graph (powered by ResolveLib).
    * Walk the graph to determine "why" each candidate came to be, i.e. what
      top-level requirements result in a given candidate.
    * Populate hashes for resolved candidates.
    * Populate markers based on dependency specifications of each candidate,
      and the dependency graph.
    """
    provider = RequirementsLibProvider(requirements)
    reporter = StdOutReporter(requirements)
    resolver = Resolver(provider, reporter)

    state = resolver.resolve(requirements)
    traces = trace_graph(state.graph)

    hash_cache = HashCache()
    for r in state.mapping.values():
        r.hashes = _get_hashes(hash_cache, r)

    # TODO: Add markers.
    # THIS DOES NOT WORK YET. I think we need to expose more from resolvelib
    # to make the trace possible here. Need to find a good way to expose those
    # criteria information.
    # import packaging.markers
    # if ireq.markers and ireq.match_markers():
    #     markers = markers.add(ireq.markers)
    #     markers = packaging.markers.Marker(
    #         " or ".join(str(m) for m in markers),
    #     )
    #     ireq.req.markers = markers
    #     requirement = Requirement.from_ireq(ireq)

    return state, traces
