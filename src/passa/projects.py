import itertools

import attr
import plette
import requirementslib

from .locking import lock
from .utils import identify_requirment


def _get_derived_requirement_data(state, traces, names):
    if not names:
        return {}
    return {
        v.normalized_name: next(iter(v.as_pipfile().values()))
        for k, v in state.mapping.items()
        if k in names or any(r[0] in names for r in traces[k])
    }


@attr.s
class Project(object):
    """A Pipfile-powered project.

    This does not implement any IO, only performs in-memory model updates.
    """
    pipfile = attr.ib()
    lockfile = attr.ib()

    def is_lock_stale(self):
        return (
            self.lockfile is None or
            not self.lockfile.is_up_to_date(self.pipfile)
        )

    def lock(self):
        try:
            default_reqs = [
                requirementslib.Requirement.from_pipfile(name, package._data)
                for name, package in self.pipfile["packages"].items()
            ]
        except KeyError:
            default_reqs = []
        try:
            develop_reqs = [
                requirementslib.Requirement.from_pipfile(name, package._data)
                for name, package in self.pipfile["dev-packages"].items()
            ]
        except KeyError:
            develop_reqs = []

        # This comprehension dance ensures we merge packages from both
        # sections, and definitions in the default section win.
        requirements = {
            identify_requirment(r): r
            for r in itertools.chain(develop_reqs, default_reqs)
        }.values()

        state, traces = lock(requirements)

        locked = plette.Lockfile.with_meta_from(self.pipfile)
        locked["default"] = _get_derived_requirement_data(
            state, traces, set(identify_requirment(r) for r in default_reqs),
        )
        locked["develop"] = _get_derived_requirement_data(
            state, traces, set(identify_requirment(r) for r in develop_reqs),
        )
        self.lockfile = locked
