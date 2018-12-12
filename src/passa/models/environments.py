# -*- coding=utf-8 -*-

import contextlib
import importlib
import json
import os
import site
import sys

from distutils.sysconfig import get_python_lib
from functools import partial
from sysconfig import get_paths

import pkg_resources
import six

from cached_property import cached_property

import vistir


BASE_WORKING_SET = pkg_resources.WorkingSet(sys.path)
run = partial(vistir.misc.run, write_to_stdout=False, nospin=True, block=True)


class Environment(object):
    def __init__(self, prefix=None, is_venv=False, base_working_set=None):
        self.base_working_set = base_working_set if base_working_set else BASE_WORKING_SET
        self._modules = {'pkg_resources': pkg_resources}
        self.extra_dists = []
        prefix = prefix if prefix else sys.prefix
        prefix = vistir.path.normalize_path(prefix)
        sys_prefix = vistir.path.normalize_path(sys.prefix)
        prefix = prefix if prefix else sys_prefix
        self.is_venv = is_venv or prefix != sys_prefix
        self.prefix = vistir.compat.Path(prefix)
        self.sys_paths = get_paths()
        super(Environment, self).__init__()

    def safe_import(self, name):
        """Helper utility for reimporting previously imported modules while inside the env"""
        module = None
        if name not in self._modules:
            self._modules[name] = importlib.import_module(name)
        module = self._modules[name]
        if not module:
            dist = next(iter(
                dist for dist in self.base_working_set if dist.project_name == name
            ), None)
            if dist:
                dist.activate()
            module = importlib.import_module(name)
        if name in sys.modules:
            try:
                six.moves.reload_module(module)
                six.moves.reload_module(sys.modules[name])
            except TypeError:
                del sys.modules[name]
                sys.modules[name] = self._modules[name]
        return module

    @classmethod
    def resolve_dist(cls, dist, working_set):
        """Given a local distribution and a working set, returns all dependencies from the set.

        :param dist: A single distribution to find the dependencies of
        :type dist: :class:`pkg_resources.Distribution`
        :param working_set: A working set to search for all packages
        :type working_set: :class:`pkg_resources.WorkingSet`
        :return: A set of distributions which the package depends on, including the package
        :rtype: set(:class:`pkg_resources.Distribution`)
        """

        deps = set()
        deps.add(dist)
        try:
            reqs = dist.requires()
        except (AttributeError, OSError, IOError):  # The METADATA file can't be found
            return deps
        for req in reqs:
            dist = working_set.find(req)
            deps |= cls.resolve_dist(dist, working_set)
        return deps

    def add_dist(self, dist_name):
        dist = pkg_resources.get_distribution(pkg_resources.Requirement(dist_name))
        extras = self.resolve_dist(dist, self.base_working_set)
        if extras:
            self.extra_dists.extend(extras)

    @cached_property
    def python_version(self):
        with self.activated():
            sysconfig = self.safe_import("sysconfig")
            py_version = sysconfig.get_python_version()
            return py_version

    @property
    def python_info(self):
        include_dir = self.prefix / "include"
        python_path = next(iter(list(include_dir.iterdir())), None)
        if python_path and python_path.name.startswith("python"):
            python_version = python_path.name.replace("python", "")
            py_version_short, abiflags = python_version[:3], python_version[3:]
            return {"py_version_short": py_version_short, "abiflags": abiflags}
        return {}

    @cached_property
    def base_paths(self):
        """
        Returns the context appropriate paths for the environment.

        :return: A dictionary of environment specific paths to be used for installation operations
        :rtype: dict

        .. note:: The implementation of this is borrowed from a combination of pip and
           virtualenv and is likely to change at some point in the future.

        >>> from pipenv.core import project
        >>> from pipenv.environment import Environment
        >>> env = Environment(prefix=project.virtualenv_location, is_venv=True, sources=project.sources)
        >>> import pprint
        >>> pprint.pprint(env.base_paths)
        {'PATH': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW/bin::/bin:/usr/bin',
        'PYTHONPATH': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW/lib/python3.7/site-packages',
        'data': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW',
        'include': '/home/hawk/.pyenv/versions/3.7.1/include/python3.7m',
        'libdir': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW/lib/python3.7/site-packages',
        'platinclude': '/home/hawk/.pyenv/versions/3.7.1/include/python3.7m',
        'platlib': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW/lib/python3.7/site-packages',
        'platstdlib': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW/lib/python3.7',
        'prefix': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW',
        'purelib': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW/lib/python3.7/site-packages',
        'scripts': '/home/hawk/.virtualenvs/pipenv-MfOPs1lW/bin',
        'stdlib': '/home/hawk/.pyenv/versions/3.7.1/lib/python3.7'}
        """

        prefix = self.prefix.as_posix()
        install_scheme = 'nt' if (os.name == 'nt') else 'posix_prefix'
        paths = get_paths(install_scheme, vars={
            'base': prefix,
            'platbase': prefix,
        })
        paths["PATH"] = paths["scripts"] + os.pathsep + os.defpath
        if "prefix" not in paths:
            paths["prefix"] = prefix
        purelib = get_python_lib(plat_specific=0, prefix=prefix)
        platlib = get_python_lib(plat_specific=1, prefix=prefix)
        if purelib == platlib:
            lib_dirs = purelib
        else:
            lib_dirs = purelib + os.pathsep + platlib
        paths["libdir"] = purelib
        paths["purelib"] = purelib
        paths["platlib"] = platlib
        paths['PYTHONPATH'] = lib_dirs
        paths["libdirs"] = lib_dirs
        return paths

    @cached_property
    def script_basedir(self):
        """Path to the environment scripts dir"""
        script_dir = self.base_paths["scripts"]
        return script_dir

    @property
    def python(self):
        """Path to the environment python"""
        py = vistir.compat.Path(self.base_paths["scripts"]).joinpath("python").as_posix()
        if not py:
            return vistir.compat.Path(sys.executable).as_posix()
        return py

    @cached_property
    def sys_path(self):
        """
        The system path inside the environment

        :return: The :data:`sys.path` from the environment
        :rtype: list
        """

        current_executable = vistir.compat.Path(sys.executable).as_posix()
        if not self.python or self.python == current_executable:
            return sys.path
        elif any([sys.prefix == self.prefix, not self.is_venv]):
            return sys.path
        cmd_args = [self.python, "-c", "import json, sys; print(json.dumps(sys.path))"]
        path, _ = run(cmd_args, return_object=False, combine_stderr=False)
        path = json.loads(path.strip())
        return path

    @cached_property
    def sys_prefix(self):
        """
        The prefix run inside the context of the environment

        :return: The python prefix inside the environment
        :rtype: :data:`sys.prefix`
        """

        command = [self.python, "-c" "import sys; print(sys.prefix)"]
        c = run(command, return_object=True)
        sys_prefix = vistir.compat.Path(vistir.misc.to_text(c.out).strip()).as_posix()
        return sys_prefix

    @property
    def scripts_dir(self):
        return self.paths["scripts"]

    @property
    def libdir(self):
        purelib = self.paths.get("purelib", None)
        if purelib and os.path.exists(purelib):
            return "purelib", purelib
        return "platlib", self.paths["platlib"]

    @cached_property
    def paths(self):
        paths = {}
        with vistir.contextmanagers.temp_environ(), vistir.contextmanagers.temp_path():
            os.environ["PYTHONIOENCODING"] = vistir.compat.fs_str("utf-8")
            os.environ["PYTHONDONTWRITEBYTECODE"] = vistir.compat.fs_str("1")
            paths = self.base_paths
            os.environ["PATH"] = paths["PATH"]
            os.environ["PYTHONPATH"] = paths["PYTHONPATH"]
            if "headers" not in paths:
                paths["headers"] = paths["include"]
        return paths

    def get_distributions(self):
        """Retrives the distributions installed on the library path of the environment

        :return: A set of distributions found on the library path
        :rtype: iterator
        """

        pkg_resources = self.safe_import("pkg_resources")
        return pkg_resources.find_distributions(self.paths["PYTHONPATH"], only=True)

    def find_egg(self, egg_dist):
        """Find an egg by name in the given environment"""

        site_packages = self.libdir[1]
        search_filename = "{0}.egg-link".format(egg_dist.project_name)
        try:
            user_site = site.getusersitepackages()
        except AttributeError:
            user_site = site.USER_SITE
        search_locations = [site_packages, user_site]
        for site_directory in search_locations:
            egg = os.path.join(site_directory, search_filename)
            if os.path.isfile(egg):
                return egg

    def locate_dist(self, dist):
        """
        Given a distribution, try to find a corresponding egg link first.

        If the egg - link doesn 't exist, return the supplied distribution."""

        location = self.find_egg(dist)
        return location or dist.location

    def dist_is_in_project(self, dist):
        """Determine whether the supplied distribution is in the environment."""

        prefix = vistir.path.normalize_path(self.base_paths["prefix"])
        location = self.locate_dist(dist)
        if not location:
            return False
        return vistir.path.normalize_path(location).startswith(prefix)

    def get_installed_packages(self):
        """
        Returns all of the installed packages in a given environment"""

        workingset = self.get_working_set()
        packages = [pkg for pkg in workingset if self.dist_is_in_project(pkg)]
        return packages

    def get_working_set(self):
        """Retrieve the working set of installed packages for the environment.

        :return: The working set for the environment
        :rtype: :class:`pkg_resources.WorkingSet`
        """

        working_set = None
        import pkg_resources
        working_set = pkg_resources.WorkingSet(self.sys_path)
        return working_set

    def is_installed(self, pkgname):
        """Given a package name, returns whether it is installed in the environment

        :param str pkgname: The name of a package
        :return: Whether the supplied package is installed in the environment
        :rtype: bool
        """

        return any(d for d in self.get_distributions() if d.project_name == pkgname)

    def run(self, cmd, cwd=os.curdir):
        """Run a command with :class:`~subprocess.Popen` in the context of the environment

        :param cmd: A command to run in the environment
        :type cmd: str or list
        :param str cwd: The working directory in which to execute the command, defaults to :data:`os.curdir`
        :return: A finished command object
        :rtype: :class:`~subprocess.Popen`
        """

        c = None
        with self.activated():
            script = vistir.cmdparse.Script.parse(cmd)
            c = run(script._parts, return_object=True, cwd=cwd)
        return c

    def run_py(self, cmd, cwd=os.curdir):
        """Run a python command in the enviornment context.

        :param cmd: A command to run in the environment - runs with `python -c`
        :type cmd: str or list
        :param str cwd: The working directory in which to execute the command, defaults to :data:`os.curdir`
        :return: A finished command object
        :rtype: :class:`~subprocess.Popen`
        """

        c = None
        if isinstance(cmd, six.string_types):
            script = vistir.cmdparse.Script.parse("{0} -c {1}".format(self.python, cmd))
        else:
            script = vistir.cmdparse.Script.parse([self.python, "-c"] + list(cmd))
        with self.activated():
            c = run(script._parts, return_object=True, cwd=cwd)
        return c

    def run_activate_this(self):
        """Runs the environment's inline activation script"""
        if self.is_venv:
            activate_this = os.path.join(self.scripts_dir, "activate_this.py")
            if not os.path.isfile(activate_this):
                raise OSError("No such file: {0!s}".format(activate_this))
            with open(activate_this, "r") as f:
                code = compile(f.read(), activate_this, "exec")
                exec(code, dict(__file__=activate_this))

    @contextlib.contextmanager
    def activated(self, include_extras=True, extra_dists=None):
        """Helper context manager to activate the environment.

        This context manager will set the following variables for the duration
        of its activation:

            * sys.prefix
            * sys.path
            * os.environ["VIRTUAL_ENV"]
            * os.environ["PATH"]

        In addition, it will make any distributions passed into `extra_dists` available
        on `sys.path` while inside the context manager, as well as making `passa` itself
        available.

        The environment's `prefix` as well as `scripts_dir` properties are both prepended
        to `os.environ["PATH"]` to ensure that calls to `~Environment.run()` use the
        environment's path preferentially.
        """

        if not extra_dists:
            extra_dists = []
        original_prefix = sys.prefix
        parent_path = vistir.compat.Path(__file__).absolute().parent.parent.as_posix()
        prefix = self.prefix.as_posix()
        with vistir.contextmanagers.temp_environ(), vistir.contextmanagers.temp_path():
            os.environ["PATH"] = os.pathsep.join([
                vistir.compat.fs_str(self.scripts_dir),
                vistir.compat.fs_str(self.prefix.as_posix()),
                os.environ.get("PATH", os.defpath)
            ])
            os.environ["PYTHONIOENCODING"] = vistir.compat.fs_str("utf-8")
            os.environ["PYTHONDONTWRITEBYTECODE"] = vistir.compat.fs_str("1")
            os.environ["PYTHONPATH"] = self.base_paths["PYTHONPATH"]
            if self.is_venv:
                os.environ["VIRTUAL_ENV"] = vistir.compat.fs_str(prefix)
            sys.path = self.sys_path
            sys.prefix = self.sys_prefix
            pkg_resources = self.safe_import("pkg_resources")
            site = self.safe_import("site")
            site.addsitedir(self.libdir[1])
            if include_extras:
                site.addsitedir(parent_path)
                extra_dists = list(self.extra_dists) + extra_dists
                for extra_dist in extra_dists:
                    if extra_dist not in self.get_working_set():
                        extra_dist.activate(self.sys_path)
            try:
                yield
            finally:
                sys.prefix = original_prefix
                six.moves.reload_module(pkg_resources)

    @contextlib.contextmanager
    def uninstall(self, pkgname, *args, **kwargs):
        """A context manager which allows uninstallation of packages from the environment

        :param str pkgname: The name of a package to uninstall

        >>> env = Environment("/path/to/env/root")
        >>> with env.uninstall("pytz", auto_confirm=True, verbose=False) as uninstaller:
                cleaned = uninstaller.paths
        >>> if cleaned:
                print("uninstalled packages: %s" % cleaned)
        """

        auto_confirm = kwargs.pop("auto_confirm", True)
        verbose = kwargs.pop("verbose", False)
        with self.activated():
            monkey_patch = next(iter(
                dist for dist in self.base_working_set
                if dist.project_name == "recursive-monkey-patch"
            ), None)
            if monkey_patch:
                monkey_patch.activate()
            pip_shims = self.safe_import("pip_shims")
            pathset_base = pip_shims.UninstallPathSet
            import recursive_monkey_patch
            recursive_monkey_patch.monkey_patch(
                PatchedUninstaller, pathset_base
            )
            dist = next(
                iter(filter(lambda d: d.project_name == pkgname, self.get_working_set())),
                None
            )
            pathset = pathset_base.from_dist(dist)
            if pathset is not None:
                pathset.remove(auto_confirm=auto_confirm, verbose=verbose)
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


class PatchedUninstaller(object):
    def _permitted(self, path):
        return True
