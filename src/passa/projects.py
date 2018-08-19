import io
import os

import attr
import packaging.utils
import plette
import six
import tomlkit
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
    def read(cls, location, model_cls, invalid_ok=False):
        try:
            with io.open(location, encoding="utf-8") as f:
                model = model_cls.load(f)
                line_ending = preferred_newlines(f)
        except Exception:
            if not invalid_ok:
                raise
            model = None
            line_ending = DEFAULT_NEWLINES
        return cls(location=location, line_ending=line_ending, model=model)

    def write(self):
        kwargs = {"encoding": "utf-8", "newline": self.line_ending}
        with io.open(self.location, "w", **kwargs) as f:
            self.model.dump(f)

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
            invalid_ok=True,
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

    def _get_pipfile_section(self, dev, insert=True):
        name = "dev-packages" if dev else "packages"
        try:
            section = self.pipfile[name]
        except KeyError:
            section = plette.models.PackageCollection(tomlkit.table())
            if insert:
                self.pipfile[name] = section
        return section

    def add_lines_to_pipfile(self, lines, develop):
        from requirementslib import Requirement
        section = self._get_pipfile_section(dev=develop)
        for line in lines:
            requirement = Requirement.from_line(line)
            key = requirement.normalized_name
            entry = next(iter(requirement.as_pipfile().values()))
            if isinstance(entry, dict):
                # HACK: TOMLKit prefers to expand tables by default, but we
                # always want inline tables here. Also tomlkit.inline_table
                # does not have `update()`.
                table = tomlkit.inline_table()
                for k, v in entry.items():
                    table[k] = v
                entry = table
            section[key] = entry

    def remove_keys_from_pipfile(self, keys, default, develop):
        keys_to_remove = {
            packaging.utils.canonicalize_name(key)
            for key in keys
        }
        sections = []
        if default:
            sections.append(self._get_pipfile_section(dev=False, insert=False))
        if develop:
            sections.append(self._get_pipfile_section(dev=True, insert=False))
        for section in sections:
            removals = set()
            for name in section:
                if packaging.utils.canonicalize_name(name) in keys_to_remove:
                    removals.add(name)
            for key in removals:
                del section._data[key]

    def lock(self):
        if self.lockfile and self.lockfile.is_up_to_date(self.pipfile):
            return False
        from .locking import build_lockfile
        with vistir.cd(self.root):
            self.lockfile = build_lockfile(self.pipfile, self.lockfile)
        return True
