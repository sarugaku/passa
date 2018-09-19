# -*- coding=utf-8 -*-

import base64
import contextlib
import distlib.scripts
import hashlib
import importlib
import json
import os
import re
import six
import sys
import sysconfig

import passa.internals._pip
from cached_property import cached_property

import vistir


class VirtualEnv(object):
    def __init__(self, venv_dir):
        self.venv_dir = vistir.compat.Path(venv_dir)

    @classmethod
    def from_project_path(cls, path):
        path = vistir.compat.Path(path)
        if path.name == 'Pipfile':
            pipfile_path = path
            path = path.parent
        else:
            pipfile_path = path / 'Pipfile'
        pipfile_location = cls.normalize_path(pipfile_path)
        venv_path = path / '.venv'
        if venv_path.exists():
            if not venv_path.is_dir():
                possible_path = vistir.compat.Path(venv_path.read_text().strip())
                if possible_path.exists():
                    return cls(possible_path.as_posix())
            else:
                if venv_path.joinpath('lib').exists():
                    return cls(venv_path.as_posix())
        sanitized = re.sub(r'[ $`!*@"\\\r\n\t]', "_", path.name)[0:42]
        hash_ = hashlib.sha256(pipfile_location.encode()).digest()[:6]
        encoded_hash = base64.urlsafe_b64encode(hash_).decode()
        hash_fragment = encoded_hash[:8]
        venv_name = "{0}-{1}".format(sanitized, hash_fragment)
        return cls(cls.get_workon_home().joinpath(venv_name).as_posix())

    @classmethod
    def normalize_path(cls, path):
        if not path:
            return
        if not path.is_absolute():
            try:
                path = path.resolve()
            except OSError:
                path = path.absolute()
        path = vistir.path.unicode_path("{0}".format(path))
        if os.name != "nt":
            return path

        drive, tail = os.path.splitdrive(path)
        # Only match (lower cased) local drives (e.g. 'c:'), not UNC mounts.
        if drive.islower() and len(drive) == 2 and drive[1] == ":":
            path = "{}{}".format(drive.upper(), tail)

        return vistir.path.unicode_path(path)

    @classmethod
    def get_workon_home(cls):
        workon_home = os.environ.get("WORKON_HOME")
        if not workon_home:
            if os.name == "nt":
                workon_home = "~/.virtualenvs"
            else:
                workon_home = os.path.join(
                    os.environ.get("XDG_DATA_HOME", "~/.local/share"), "virtualenvs"
                )
        return vistir.compat.Path(os.path.expandvars(workon_home)).expanduser()

    @cached_property
    def script_basedir(self):
        script_dir = os.path.basename(sysconfig.get_paths()["scripts"])
        return script_dir

    @property
    def python(self):
        return self.venv_dir.joinpath(self.script_basedir).joinpath("python").as_posix()

    @cached_property
    def sys_path(self):
        c = vistir.misc.run([self.python, "-c", "import json,sys; print(json.dumps(sys.path))"],
                            return_object=True, nospin=True)
        assert c.returncode == 0, "failed loading virtualenv path"
        path = json.loads(c.out.strip())
        return path

    @cached_property
    def system_paths(self):
        paths = {}
        six.moves.reload_module(sysconfig)
        paths = sysconfig.get_paths()
        return paths

    @cached_property
    def sys_prefix(self):
        c = self.run_py(["-c", "'import sys; print(sys.prefix)'"])
        sys_prefix = vistir.misc.to_text(c.out).strip()
        return sys_prefix

    @cached_property
    def paths(self):
        paths = {}
        with vistir.contextmanagers.temp_environ(), vistir.contextmanagers.temp_path():
            os.environ["PYTHONUSERBASE"] = vistir.compat.fs_str(self.venv_dir.as_posix())
            os.environ["PYTHONIOENCODING"] = vistir.compat.fs_str("utf-8")
            os.environ["PYTHONDONTWRITEBYTECODE"] = vistir.compat.fs_str("1")
            six.moves.reload_module(sysconfig)
            scheme, _, _ = sysconfig._get_default_scheme().partition('_')
            scheme = "{0}_user".format(scheme)
            paths = sysconfig.get_paths(scheme=scheme)
        return paths

    @property
    def scripts_dir(self):
        return self.paths["scripts"]

    @cached_property
    def passa_entry(self):
        import pkg_resources
        return pkg_resources.working_set.by_key['passa'].location

    def get_distributions(self):
        import pkg_resources
        six.moves.reload_module(pkg_resources)
        return pkg_resources.find_distributions(self.paths["purelib"], only=True)

    def get_working_set(self):
        working_set = None
        import pkg_resources
        passa_entry = self.passa_entry
        monkeypatch = self.monkeypatch_dist
        working_set = pkg_resources.WorkingSet(self.sys_path + [passa_entry, monkeypatch])
        return working_set

    @classmethod
    def filter_sources(cls, requirement, sources):
        if not sources or not requirement.index:
            return sources
        filtered_sources = [
            source for source in sources
            if source.get("name") == requirement.index
        ]
        return filtered_sources or sources

    @cached_property
    def python_version(self):
        with self.activated():
            six.moves.reload_module(sysconfig)
            py_version = sysconfig.get_python_version()
            return py_version

    @classmethod
    def safe_import(cls, name):
        module = None
        if name not in sys.modules:
            module = importlib.import_module(name)
        else:
            module = sys.modules[name]
        six.moves.reload_module(module)
        return module

    @cached_property
    def monkeypatch_dist(self):
        pkg_resources = self.safe_import("pkg_resources")
        monkey_patch = pkg_resources.get_distribution('recursive-monkey-patch').location
        return monkey_patch

    def get_setup_install_args(self, pkgname, setup_py, develop=False):
        headers = vistir.compat.Path(self.sys_prefix) / "include" / "site"
        headers = headers / "python{0}".format(self.python_version) / pkgname
        install_arg = "install" if not develop else "develop"
        return [
            self.python, "-u", "-c", SETUPTOOLS_SHIM % setup_py, install_arg,
            "--single-version-externally-managed", "root={0}".format(),
            "--install-headers={0}".format(headers.as_posix()),
            "--install-purelib={0}".format(self.paths["purelib"]),
            "--install-platlib={0}".format(self.paths["platlib"]),
            "--install-scripts={0}".format(self.scripts_dir),
            "--install-data={0}".format(self.paths["data"]),
        ]

    def install(self, req, editable=False, sources=[]):
        with self.activated():
            install_options = ["--prefix={0}".format(self.venv_dir),]
            six.moves.reload_module(passa.internals._pip)
            ireq = req.as_ireq()
            if editable:
                with vistir.contextmanagers.cd(ireq.setup_py_dir, ireq.setup_py):
                    c = self.run(
                        install_options + self.get_setup_install_args(
                            req.name, develop=editable
                        ), cwd=ireq.setup_py_dir
                    )
                    return c.returncode
            six.moves.reload_module(distlib.scripts)
            sources = self.filter_sources(req, sources)
            hashes = req.hashes
            wheel = passa.internals._pip.build_wheel(ireq, sources, hashes)
            wheel.install(self.paths, distlib.scripts.ScriptMaker(None, None))

    @contextlib.contextmanager
    def activated(self):
        original_path = sys.path
        original_prefix = sys.prefix
        original_user_base = os.environ.get("PYTHONUSERBASE", None)
        original_venv = os.environ.get("VIRTUAL_ENV", None)
        passa_path = vistir.compat.Path(__file__).absolute().parent.parent.as_posix()
        monkeypatch_dist = self.monkeypatch_dist
        with vistir.contextmanagers.temp_environ(), vistir.contextmanagers.temp_path():
            os.environ["PYTHONUSERBASE"] = vistir.compat.fs_str(self.venv_dir.as_posix())
            os.environ["PYTHONIOENCODING"] = vistir.compat.fs_str("utf-8")
            os.environ["PYTHONDONTWRITEBYTECODE"] = vistir.compat.fs_str("1")
            os.environ["VIRTUAL_ENV"] = vistir.compat.fs_str(self.venv_dir.as_posix())
            sys.path = self.sys_path
            sys.prefix = self.venv_dir
            import site
            # sys.path.append(passa_path)
            activate_this = os.path.join(self.scripts_dir, "activate_this.py")
            with open(activate_this, "r") as f:
                code = compile(f.read(), activate_this, "exec")
                exec(code, dict(__file__=activate_this))
            site.addsitedir(passa_path)
            site.addsitedir(monkeypatch_dist)
            pkg_resources = self.safe_import("pkg_resources")
            try:
                yield
            finally:
                print("Deactivating virtualenv...")
                del os.environ["VIRTUAL_ENV"]
                del os.environ["PYTHONUSERBASE"]
                if original_user_base:
                    os.environ["PYTHONUSERBASE"] = original_user_base
                if original_venv:
                    os.environ["VIRTUAL_ENV"] = original_venv
                sys.path = original_path
                sys.prefix = original_prefix
                six.moves.reload_module(pkg_resources)

    def run(self, cmd, cwd=os.curdir):
        c = None
        with self.activated():
            script = vistir.cmdparse.Script.parse(cmd)
            c = vistir.misc.run(script._parts, return_object=True, nospin=True, cwd=cwd)
        return c

    def run_py(self, cmd, cwd=os.curdir):
        c = None
        if isinstance(cmd, six.string_types):
            script = vistir.cmdparse.Script.parse("{0} {1}".format(self.python, cmd))
        else:
            script = vistir.cmdparse.Script.parse([self.python,] + list(cmd))
        with self.activated():
            c = vistir.misc.run(script._parts, return_object=True, nospin=True, cwd=cwd)
        return c

    def is_installed(self, pkgname):
        return any(d for d in self.get_distributions() if d.project_name == pkgname)

    def get_monkeypatched_pathset(self):
        import recursive_monkey_patch
        from pip_shims.shims import req_install
        req_uninstall_name = "{0}.req_uninstall".format(req_install.__package__)
        if req_uninstall_name not in sys.modules:
            req_uninstall = importlib.import_module(req_uninstall_name)
        else:
            req_uninstall = sys.modules[req_uninstall_name]
            six.moves.reload_module(req_uninstall)
        recursive_monkey_patch.monkey_patch(PatchedUninstaller, req_uninstall.UninstallPathSet)
        return req_uninstall.UninstallPathSet

    @contextlib.contextmanager
    def uninstall(self, pkgname, *args, **kwargs):
        auto_confirm = kwargs.pop("auto_confirm", True)
        verbose = kwargs.pop("verbose", False)
        with self.activated():
            pathset_base = self.get_monkeypatched_pathset()
            dist = next(
                iter(filter(lambda d: d.project_name == pkgname, self.get_working_set())),
                None
            )
            pathset = pathset_base.from_dist(dist)
            print(pathset.paths)
            if pathset is not None:
                pathset.remove(auto_confirm=auto_confirm, verbose=True)
            try:
                yield pathset
            except Exception as e:
                if pathset is not None:
                    pathset.rollback()
            else:
                if pathset is not None:
                    pathset.commit()
            if pathset is None:
                return


SETUPTOOLS_SHIM = (
    "import setuptools, tokenize;__file__=%r;"
    "f=getattr(tokenize, 'open', open)(__file__);"
    "code=f.read().replace('\\r\\n', '\\n');"
    "f.close();"
    "exec(compile(code, __file__, 'exec'))"
)


class PatchedUninstaller(object):
    def _permitted(self, path):
        return True
