import itertools

import attr
import plette
import requirementslib

from .locking import lock


def _is_derived_from(k, traces, packages):
    return k in packages or any(r[0] in packages for r in traces[k])


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
        # This comprehension dance ensures we merge packages from both
        # sections, and definitions in the default section win.
        # TODO: Treat the same key with different extras as distinct.
        requirements = {
            name: requirementslib.Requirement.from_pipfile(name, package._data)
            for name, package in itertools.chain(
                self.pipfile.dev_packages.items(),
                self.pipfile.packages.items(),
            )
        }.values()

        state, traces = lock(requirements)

        # TODO: Consider extras when grouping.
        default = {
            k: v for k, v in state.mapping.items()
            if _is_derived_from(k, traces, self.pipfile.packages)
        }
        develop = {
            k: v for k, v in state.mapping.items()
            if _is_derived_from(k, traces, self.pipfile.dev_packages)
        }

        locked = plette.Lockfile.with_meta_from(self.pipfile)
        locked["default"] = {k: v.as_pipfile()[k] for k, v in default.items()}
        locked["develop"] = {k: v.as_pipfile()[k] for k, v in develop.items()}
        self.lockfile = locked
