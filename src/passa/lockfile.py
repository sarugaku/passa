# -*- coding=utf-8 -*-
from contextlib import contextmanager
from requirementslib import Lockfile
from requirementslib.models.pipfile import Hash
from requirementslib._compat import VcsSupport, Wheel


def get_hashes(r, state, cache):
    hashes = {}
    for dep in state.mapping:
        if dep not in hashes:
            hashes[dep] = get_hash(cache, state.mapping[dep])
    return hashes.copy()


def get_hash(cache, req):
    ireq = req.ireq
    if ireq.editable:
        return set()

    vcs = VcsSupport()
    if (ireq.link and ireq.link.scheme in vcs.all_schemes
            and 'ssh' in ireq.link.scheme):
        return set()

    if not ireq.is_pinned:
        raise TypeError("Expected pinned requirement, got {}".format(req.as_line()))

    matching_candidates = set()
    with allow_all_wheels():
        matching_candidates = (
            req.find_all_matches()
        )

    return {
        cache.get_hash(candidate.location) for candidate in matching_candidates
    }


def get_root_parent(r, state, dep):
    pass


def build_lockfile(r, state, hash_cache, pipfile=None):
    dev_names = [req.name for req in pipfile.dev_packages.requirements]
    req_names = [req.name for req in pipfile.packages.requirements]
    dev_reqs, reqs = [], []
    hashes = get_hashes(r, state, hash_cache)
    for dep in sorted(state.mapping):
        req = state.mapping[dep]
        req.hashes = [Hash(value=v) for v in hashes.get(dep, [])]
        parents = set()
        if any(name in dev_names for name in list(parents) + [req.normalized_name,]):
            dev_reqs.append(req)
        if any(name in req_names for name in list(parents) + [req.normalized_name,]):
            reqs.append(req)

    creation_dict = {
        "path": pipfile.path.parent / 'Pipfile.lock',
        "pipfile_hash": Hash(value=pipfile.get_hash()),
        "sources": [s for s in pipfile.sources],
        "dev_requirements": dev_reqs,
        "requirements": reqs,
    }
    if pipfile.requires.has_value():
        creation_dict['requires'] = pipfile.requires
    lockfile = Lockfile(**creation_dict)
    return lockfile


@contextmanager
def allow_all_wheels():
    """
    Monkey patches pip.Wheel to allow wheels from all platforms and Python versions.

    This also saves the candidate cache and set a new one, or else the results from the
    previous non-patched calls will interfere.
    """
    def _wheel_supported(self, tags=None):
        # Ignore current platform. Support everything.
        return True

    def _wheel_support_index_min(self, tags=None):
        # All wheels are equal priority for sorting.
        return 0

    original_wheel_supported = Wheel.supported
    original_support_index_min = Wheel.support_index_min

    Wheel.supported = _wheel_supported
    Wheel.support_index_min = _wheel_support_index_min

    try:
        yield
    finally:
        Wheel.supported = original_wheel_supported
        Wheel.support_index_min = original_support_index_min


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


def trace(graph):
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
        for root in graph.iter_children(None):
            if root == vertex:
                continue
            paths = []
            visited = set()     # Prevent cycles.
            _trace_visit_vertex(graph, root, vertex, visited, [], paths)
            if not paths:
                continue
            if vertex in result:
                result[vertex].extend(paths)
            else:
                result[vertex] = paths
    return result
