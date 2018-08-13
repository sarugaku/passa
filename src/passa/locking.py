import contextlib
import copy
import itertools

from pip_shims import Wheel
from plette import Lockfile
from requirementslib import Requirement
from resolvelib import Resolver

from .caches import HashCache
from .providers import RequirementsLibProvider
from .reporters import StdOutReporter
from .traces import trace_graph
from .utils import identify_requirment


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
    if req.is_vcs or ireq.editable or not ireq.is_pinned:
        return set()

    matching_candidates = set()
    with _allow_all_wheels():
        matching_candidates = req.find_all_matches()

    return {
        cache.get_hash(candidate.location)
        for candidate in matching_candidates
    }


def _markerset(*markers):
    return frozenset(markers)


def _add_markersets(specs, key, trace, all_markersets):
    markersets = set()
    for route in trace:
        parent = route[-1]
        try:
            parent_markersets = all_markersets[parent]
        except KeyError:    # Parent not calculated yet. Wait for it.
            return False
        r = specs[parent][key]
        if r.markers:
            markerset = _markerset(r.markers)
        else:
            markerset = _markerset()
        markersets.update({
            parent_markerset | markerset
            for parent_markerset in parent_markersets
        })
    try:
        current_markersets = all_markersets[key]
    except KeyError:
        all_markersets[key] = markersets
    else:
        all_markersets[key] = current_markersets | markersets
    return True


def _calculate_markersets_mapping(specs, requirements, state, traces):
    all_markersets = {}

    # Populate markers from Pipfile.
    for r in requirements:
        if r.markers:
            markerset = _markerset(r.markers)
        else:
            markerset = _markerset()
        all_markersets[identify_requirment(r)] = {markerset}

    traces = copy.deepcopy(traces)
    del traces[None]
    while traces:
        successful_keys = set()
        for key, trace in traces.items():
            ok = _add_markersets(specs, key, trace, all_markersets)
            if not ok:
                continue
            successful_keys.add(key)
        if not successful_keys:
            break   # No progress? Deadlocked. Give up.
        for key in successful_keys:
            del traces[key]

    return all_markersets


def resolve_requirements(requirements):
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

    markersets_mapping = _calculate_markersets_mapping(
        provider.fetched_dependencies, requirements, state, traces,
    )
    print('RESULT', markersets_mapping)
    # for k, r in state.mapping.items():
    #     markers = [
    #         " and ".join("({0})".format(p) for p in route if p)
    #         for routes in marker_routes[k]
    #         for route in routes
    #     ]
    #     if any(not m for m in markers):
    #         # Needs to be unconditional if there is an unconditional route.
    #         pass
    #     r.markers =

    return state, traces


def _get_derived_requirement_data(state, traces, names):
    if not names:
        return {}
    return {
        v.normalized_name: next(iter(v.as_pipfile().values()))
        for k, v in state.mapping.items()
        if k in names or any(r[0] in names for r in traces[k])
    }


def build_lockfile(pipfile):
    default_reqs = [
        Requirement.from_pipfile(name, package._data)
        for name, package in pipfile.get("packages", {}).items()
    ]
    develop_reqs = [
        Requirement.from_pipfile(name, package._data)
        for name, package in pipfile.get("dev-packages", {}).items()
    ]

    # This comprehension dance ensures we merge packages from both
    # sections, and definitions in the default section win.
    requirements = {
        identify_requirment(r): r
        for r in itertools.chain(develop_reqs, default_reqs)
    }.values()

    state, traces = resolve_requirements(requirements)

    lockfile = Lockfile.with_meta_from(pipfile)
    lockfile["default"] = _get_derived_requirement_data(
        state, traces, set(identify_requirment(r) for r in default_reqs),
    )
    lockfile["develop"] = _get_derived_requirement_data(
        state, traces, set(identify_requirment(r) for r in develop_reqs),
    )
    return lockfile


def are_in_sync(pipfile, lockfile):
    return lockfile and lockfile.is_up_to_date(pipfile)
