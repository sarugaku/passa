# -*- coding=utf-8 -*-
from contextlib import contextmanager
from requirementslib import Lockfile
from requirementslib._compat import VcsSupport, Wheel


def get_hashes(cache, resolver, state, key):
    if key.ireq.editable:
        return set()

    vcs = VcsSupport()
    if (key.ireq.link and key.ireq.link.scheme in vcs.all_schemes
            and 'ssh' in key.ireq.link.scheme):
        return set()

    if not key.ireq.pinned:
        raise TypeError("Expected pinned requirement, got {}".format(key))

    matching_candidates = set()
    with allow_all_wheels():
        matching_candidates = (
            resolver.provider.find_matches(key)
        )

    return {
        cache.get_hash(candidate.location) for candidate in matching_candidates
    }


def build_lockfile(pipfile, requirements):
    # hashes = resolved.get_hashes()
    # dev_names = [req.name for req in self.dev_packages.requirements]
    # req_names = [req.name for req in self.packages.requirements]
    # dev_reqs, reqs = [], []
    # for req, pin in resolved.pinned_deps.items():
    #     parent = None
    #     _current_dep = resolved.dep_dict[req]
    #     while True:
    #         if _current_dep.parent:
    #             parent = _current_dep.parent.name
    #             _current_dep = _current_dep.parent
    #         break
    #     requirement = None
    #     requirement = Requirement.from_line(format_requirement(pin))
    #     requirement.hashes = [Hash(value=v) for v in hashes.get(req, [])]
    #     if req in req_names:
    #         reqs.append(req)
    #     elif req in dev_names:
    #         dev_reqs.append(req)
    #     # If the requirement in question inherits from a dev requirement we still
    #     # need to add it to the dev dependencies
    #     if parent and parent in dev_names and req not in dev_names:
    #         dev_reqs.append(req)
    #     # If the requirement in question inherits from a non-dev requirement we
    #     # will still need to make sure it gets added to the non-dev section
    #     if parent and parent in req_names and req not in req_names:
    #         reqs.append(req)
    pass


@contextmanager
def allow_all_wheels(self):
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
