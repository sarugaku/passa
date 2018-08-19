import io
import os

import attr
import plette
import six
import vistir


DEFAULT_NEWLINES = "\n"


def preferred_newlines(f):
    if isinstance(f.newlines, six.text_type):
        return f.newlines
    return DEFAULT_NEWLINES


@attr.s
class ProjectFile(object):
    """A file in the Pipfile project.
    """
    location = attr.ib()
    line_ending = attr.ib()
    model = attr.ib()

    @classmethod
    def read(cls, location, model_cls, non_exist_ok=False):
        if non_exist_ok and not os.path.exists(location):
            model = None
            line_ending = DEFAULT_NEWLINES
        else:
            with io.open(location, encoding="utf-8") as f:
                model = model_cls.load(f)
                line_ending = preferred_newlines(f)
        return cls(location=location, line_ending=line_ending, model=model)

    def write(self):
        kwargs = {"encocing": "utf-8", "newline": self.line_ending}
        with io.open(self.location, "w", **kwargs) as f:
            self.model.dump(f)
            f.write("\n")

    def dumps(self):
        strio = six.StringIO()
        self.model.dump(strio)
        return strio.getvalue()


@attr.s
class Project(object):

    root = attr.ib()
    _p = attr.ib(init=False)
    _l = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.root = root = os.path.abspath(self.root)
        self._p = ProjectFile.read(
            os.path.join(root, "Pipfile"),
            plette.Pipfile,
        )
        self._l = ProjectFile.read(
            os.path.join(root, "Pipfile.lock"),
            plette.Lockfile,
            non_exist_ok=True,
        )

    @property
    def pipfile(self):
        return self._p.model

    @property
    def pipfile_location(self):
        return self._p.location

    @property
    def lockfile(self):
        return self._l.model

    @property
    def lockfile_location(self):
        return self._l.location

    @lockfile.setter
    def lockfile(self, new):
        self._l.model = new

    def lock(self, force=False):
        from .locking import build_lockfile
        lockfile = self.lockfile
        if not force and lockfile and lockfile.is_up_to_date(self.pipfile):
            return False
        with vistir.cd(self.root):
            self.lockfile = build_lockfile(self.pipfile)
        return True
