import contextlib

from requirementslib._compat import VcsSupport, Wheel
from resolvelib import Resolver

from .caches import HashCache
from .models import Hash, Lockfile
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


def _get_hash(cache, req):
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


def _is_derived_from(k, traces, packages):
    return k in packages or any(r[0] in packages for r in traces[k])


PIPFILE_SPEC_CURRENT = 6


def lock(pipfile):
    package_mapping = pipfile.dev_packages.copy()
    package_mapping.update(pipfile.packages)
    requirements = package_mapping.values()

    provider = RequirementsLibProvider(requirements)
    reporter = StdOutReporter(requirements)
    resolver = Resolver(provider, reporter)

    state = resolver.resolve(requirements)

    traces = _trace(state.graph)
    default = {
        k: v for k, v in state.mapping.items()
        if _is_derived_from(k, traces, pipfile.packages)
    }
    develop = {
        k: v for k, v in state.mapping.items()
        if _is_derived_from(k, traces, pipfile.dev_packages)
    }

    hash_cache = HashCache()
    hashes = {k: _get_hash(hash_cache, v) for k, v in state.mapping.items()}
    for mapping in [default, develop]:
        for k, v in mapping.items():
            v.hashes = [Hash.parse(v) for v in hashes.get(k, [])]

    return Lockfile(
        pipfile_spec=PIPFILE_SPEC_CURRENT,
        pipfile_hash=pipfile.get_hash(),
        requires=pipfile.requires.copy(),
        sources=pipfile.sources.copy(),
        default=default,
        develop=develop,
    )
