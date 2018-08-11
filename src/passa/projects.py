import attr

from .locking import lock


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
        self.lockfile = lock(self.pipfile)
