import contextlib

from plette.models import Hash
from requirementslib._compat import VcsSupport, Wheel
from resolvelib import Resolver

from .caches import HashCache
from .providers import RequirementsLibProvider
from .reporters import StdOutReporter


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


def _trace_visit_vertex(graph, current, target, visited, path, paths):
    if current == target:
        paths.append(path)
        return
    for v in graph.iter_children(current):
        if v == current or v in visited:
            continue
        next_path = path + [current]
        next_visited = visited | {current}
        _trace_visit_vertex(graph, v, target, next_visited, next_path, paths)


def _trace(graph):
    """Build a collection of "traces" for each package.

    A trace is a list of names that eventually leads to the package. For
    example, if A and B are root dependencies, A depends on C and D, B
    depends on C, and C depends on D, the return value would be like::

        {
            "A": [],
            "B": [],
            "C": [["A"], ["B"]],
            "D": [["B", "C"], ["A"]],
        }
    """
    result = {}
    for vertex in graph:
        result[vertex] = []
        for root in graph.iter_children(None):
            if root == vertex:
                continue
            paths = []
            _trace_visit_vertex(graph, root, vertex, set(), [], paths)
            result[vertex].extend(paths)
    return result


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
    traces = _trace(state.graph)

    hash_cache = HashCache()
    for r in state.mapping.values():
        r.hashes = [Hash.from_line(h) for h in _get_hashes(hash_cache, r)]

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
