# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import contextlib
import io
import itertools
import distutils.log
import os
import re

import distlib.database
import distlib.metadata
import distlib.scripts
import distlib.wheel
import packaging.utils
import pip_shims
import six
import sys
import sysconfig
import vistir

from ..models.caches import CACHE_DIR
from ..models.environments import Environment
from ._pip_shims import (
    SETUPTOOLS_SHIM, VCS_SUPPORT, build_wheel as _build_wheel, unpack_url
)
from .utils import filter_sources


@vistir.path.ensure_mkdir_p(mode=0o775)
def _get_src_dir():
    src = os.environ.get("PIP_SRC")
    if src:
        return src
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        return os.path.join(virtual_env, "src")
    return os.path.join(os.getcwd(), "src")     # Match pip's behavior.


def _prepare_wheel_building_kwargs(ireq):
    download_dir = os.path.join(CACHE_DIR, "pkgs")
    vistir.mkdir_p(download_dir)

    wheel_download_dir = os.path.join(CACHE_DIR, "wheels")
    vistir.mkdir_p(wheel_download_dir)

    if ireq.source_dir is not None:
        src_dir = ireq.source_dir
    elif ireq.editable:
        src_dir = _get_src_dir()
    else:
        src_dir = vistir.path.create_tracked_tempdir(prefix='passa-src')

    # This logic matches pip's behavior, although I don't fully understand the
    # intention. I guess the idea is to build editables in-place, otherwise out
    # of the source tree?
    if ireq.editable:
        build_dir = src_dir
    else:
        build_dir = vistir.path.create_tracked_tempdir(prefix="passa-build")

    return {
        "build_dir": build_dir,
        "src_dir": src_dir,
        "download_dir": download_dir,
        "wheel_download_dir": wheel_download_dir,
    }


def _get_pip_index_urls(sources):
    index_urls = []
    trusted_hosts = []
    for source in sources:
        url = source.get("url")
        if not url:
            continue
        index_urls.append(url)
        if source.get("verify_ssl", True):
            continue
        host = six.moves.urllib.parse.urlparse(source["url"]).hostname
        trusted_hosts.append(host)
    return index_urls, trusted_hosts


class _PipCommand(pip_shims.Command):
    name = "PipCommand"


def _get_pip_session(trusted_hosts):
    cmd = _PipCommand()
    options, _ = cmd.parser.parse_args([])
    options.cache_dir = CACHE_DIR
    options.trusted_hosts = trusted_hosts
    return cmd._build_session(options)


@contextlib.contextmanager
def _get_finder(sources):
    index_urls, trusted_hosts = _get_pip_index_urls(sources)
    with contextlib.closing(_get_pip_session(trusted_hosts)) as session:
        finder = pip_shims.PackageFinder(
            find_links=[],
            index_urls=index_urls,
            trusted_hosts=trusted_hosts,
            allow_all_prereleases=True,
            session=session,
        )
        yield finder


def _get_wheel_cache():
    format_control = pip_shims.FormatControl(set(), set())
    wheel_cache = pip_shims.WheelCache(CACHE_DIR, format_control)
    return wheel_cache


def _convert_hashes(values):
    """Convert Pipfile.lock hash lines into InstallRequirement option format.

    The option format uses a str-list mapping. Keys are hash algorithms, and
    the list contains all values of that algorithm.
    """
    hashes = {}
    if not values:
        return hashes
    for value in values:
        try:
            name, value = value.split(":", 1)
        except ValueError:
            name = "sha256"
        if name not in hashes:
            hashes[name] = []
        hashes[name].append(value)
    return hashes


class WheelBuildError(RuntimeError):
    pass


def build_wheel(ireq, sources, finder, hashes=None):
    """Build a wheel file for the InstallRequirement object.

    An artifact is downloaded (or read from cache). If the artifact is not a
    wheel, build one out of it. The dynamically built wheel is ephemeral; do
    not depend on its existence after the returned wheel goes out of scope.

    If `hashes` is truthy, it is assumed to be a list of hashes (as formatted
    in Pipfile.lock) to be checked against the download.

    Returns a `distlib.wheel.Wheel` instance. Raises a `WheelBuildError` (a
    `RuntimeError` subclass) if the wheel cannot be built.
    """
    kwargs = _prepare_wheel_building_kwargs(ireq)

    # Not for upgrade, hash not required. Hashes are not required here even
    # when we provide them, because pip skips local wheel cache if we set it
    # to True. Hashes are checked later if we need to download the file.
    ireq.populate_link(finder, False, False)

    # Ensure ireq.source_dir is set.
    # This is intentionally set to build_dir, not src_dir. Comments from pip:
    #   [...] if filesystem packages are not marked editable in a req, a non
    #   deterministic error occurs when the script attempts to unpack the
    #   build directory.
    # Also see comments in `_prepare_wheel_building_kwargs()` -- If the ireq
    # is editable, build_dir is actually src_dir, making the build in-place.
    ireq.ensure_has_source_dir(kwargs["build_dir"])

    # Ensure the source is fetched. For wheels, it is enough to just download
    # because we'll use them directly. For an sdist, we need to unpack so we
    # can build it.
    if not ireq.editable or not pip_shims.is_file_url(ireq.link):
        if ireq.is_wheel:
            only_download = True
            download_dir = kwargs["wheel_download_dir"]
        else:
            only_download = False
            download_dir = kwargs["download_dir"]
        ireq.options["hashes"] = _convert_hashes(hashes)
        unpack_url(
            ireq.link, ireq.source_dir, download_dir,
            only_download=only_download, session=finder.session,
            hashes=ireq.hashes(False), progress_bar="off",
        )

    if ireq.is_wheel:
        # If this is a wheel, use the downloaded thing.
        output_dir = kwargs["wheel_download_dir"]
        wheel_path = os.path.join(output_dir, ireq.link.filename)
    else:
        # Othereise we need to build an ephemeral wheel.
        wheel_path = _build_wheel(
            ireq, vistir.path.create_tracked_tempdir(prefix="ephem"),
            finder, _get_wheel_cache(), kwargs,
        )
        if wheel_path is None or not os.path.exists(wheel_path):
            raise WheelBuildError
    return distlib.wheel.Wheel(wheel_path)


def get_vcs_ref(requirement):
    return requirement.commit_hash


def find_installation_candidates(ireq, sources):
    candidates = []
    with _get_finder(sources) as finder:
        candidates = finder.find_all_candidates(ireq.name)
    return candidates


class RequirementUninstaller(object):
    """A context manager to remove a package for the inner block.

    This uses `UninstallPathSet` to control the workflow. If the inner block
    exits correctly, the uninstallation is committed, otherwise rolled back.
    """
    def __init__(self, ireq, auto_confirm, verbose, env=None):
        self.ireq = ireq
        self.pathset = None
        self.auto_confirm = auto_confirm
        self.verbose = verbose
        self.env = env if env else Environment()

    def check_permitted(self, pathset, path):
        if self.env.is_venv and self.env.is_installed(self.ireq.name):
            return True
        return pathset._permitted(path)

    def __enter__(self):
        self.pathset = self.ireq.uninstall(
            auto_confirm=self.auto_confirm,
            verbose=self.verbose,
        )
        self.pathset._permitted = self.check_permitted
        return self.pathset

    def __exit__(self, exc_type, exc_value, traceback):
        if self.pathset is None:
            return
        if exc_type is None:
            self.pathset.commit()
        else:
            self.pathset.rollback()


def uninstall(name, **kwargs):
    ireq = pip_shims.InstallRequirement.from_line(name)
    return RequirementUninstaller(ireq, **kwargs)


@contextlib.contextmanager
def _suppress_distutils_logs():
    """Hack to hide noise generated by `setup.py develop`.

    There isn't a good way to suppress them now, so let's monky-patch.
    See https://bugs.python.org/issue25392.
    """
    f = distutils.log.Log._log

    def _log(log, level, msg, args):
        if level >= distutils.log.ERROR:
            f(log, level, msg, args)

    distutils.log.Log._log = _log
    yield
    distutils.log.Log._log = f


class NoopInstaller(object):
    """An installer.

    This class is not designed to be instantiated by itself, but used as a
    common interface for subclassing.

    An installer has two methods, `prepare()` and `install()`. Neither takes
    arguments, and should be called in that order to prepare an installation
    operation, and to actually install things.
    """

    def prepare(self):
        pass

    def install(self):
        pass


dist_info_re = re.compile(r"""^(?P<namever>(?P<name>.+?)(-(?P<ver>.+?))?)
                                \.dist-info$""", re.VERBOSE)


def root_is_purelib(name, wheeldir):
    """
    Return True if the extracted wheel in wheeldir should go into purelib.
    """
    name_folded = name.replace("-", "_")
    for item in os.listdir(wheeldir):
        match = dist_info_re.match(item)
        if match and match.group('name') == name_folded:
            with open(os.path.join(wheeldir, item, 'WHEEL')) as wheel:
                for line in wheel:
                    line = line.lower().rstrip()
                    if line == "root-is-purelib: true":
                        return True
    return False


def get_entrypoints(filename):
    import pkg_resources
    if not os.path.exists(filename):
        return {}, {}

    # This is done because you can pass a string to entry_points wrappers which
    # means that they may or may not be valid INI files. The attempt here is to
    # strip leading and trailing whitespace in order to make them valid INI
    # files.
    with open(filename) as fp:
        data = io.StringIO()
        for line in fp:
            data.write(line.strip())
            data.write("\n")
        data.seek(0)

    # get the entry points and then the script names
    entry_points = pkg_resources.EntryPoint.parse_map(data)
    console = entry_points.get('console_scripts', {})
    gui = entry_points.get('gui_scripts', {})

    def _split_ep(s):
        """get the string representation of EntryPoint, remove space and split
        on '='"""
        return str(s).replace(" ", "").split("=")

    # convert the EntryPoint objects into strings with module:function
    console = dict(_split_ep(v) for v in console.values())
    gui = dict(_split_ep(v) for v in gui.values())
    return console, gui


class BaseInstaller(NoopInstaller):
    """Virtualenv-capable installer"""

    def __init__(self, requirement, sources=None, environment=None):
        self.ireq = requirement.as_ireq()
        self.sources = filter_sources(requirement, sources)
        self.hashes = requirement.hashes or None
        self.environment = environment if environment else Environment()
        self.built = None
        self.metadata = None
        self.is_wheel = False

    @property
    def src_dir(self):
        build_dir = os.environ.get("PASSA_BUILD_DIR", None)
        if not build_dir:
            build_dir = vistir.path.create_tracked_tempdir("passa-build-dir")
        return build_dir

    @property
    def setup_dir(self):
        if not self.built:
            return self.ireq.setup_py_dir
        return vistir.compat.Path(self.built.path).parent

    @property
    def installation_args(self):
        install_arg = "install" if not self.ireq.editable else "develop"
        setup_path = self.setup_dir.joinpath("setup.py")
        install_keys = ["headers", "purelib", "platlib", "scripts", "data"]
        install_args = [
            self.environment.python, "-u", "-c", SETUPTOOLS_SHIM % setup_path.as_posix(),
            install_arg, "--single-version-externally-managed", "--no-deps",
            "--prefix={0}".format(self.environment.paths["prefix"])
        ]
        for key in install_keys:
            install_args.append(
                "--install-{0}={1}".format(key, self.environment.paths[key])
            )
        return install_args

    def build_wheel(self):
        with _get_finder(self.sources) as finder:
            self.built = build_wheel(self.ireq, self.sources, finder, self.hashes)
            self.metadata = self.built.metadata
        self.is_wheel = True

    def build_sdist(self):
        with _get_finder(self.sources) as finder:
            self.ireq.populate_link(finder, False, False)
            self.ireq.ensure_has_source_dir(self.src_dir)
            self.built = get_sdist(self.ireq)
            self.metadata = read_sdist_metadata(self.ireq)

    def install_wheel(self):
        scripts = distlib.scripts.ScriptMaker(None, None)
        self.built.install(self.environment.paths, scripts)

    def install_sdist(self):
        with vistir.cd(self.setup_dir.as_posix()), _suppress_distutils_logs():
            c = self.environment.run(
                self.installation_args, return_object=True, block=True, nospin=True,
                combine_stderr=False, write_to_stdout=False
            )
            if c.returncode != 0:
                err_text = "{0!r}: {1!r}".format(c.err, c.out)
                raise RuntimeError("Failed to install package: {0!r}".format(err_text))
            return

    def prepare(self):
        pass

    def install(self):
        with self.environment.activated():
            self._install()


class SdistInstaller(BaseInstaller):
    """Installer for SDists"""
    def __init__(self, *args, **kwargs):
        super(SdistInstaller, self).__init__(*args, **kwargs)

    def prepare(self):
        try:
            self.build_wheel()
        except (WheelBuildError, distlib.metadata.MetadataConflictError):
            self.build_sdist()
            if not self.built or not self.metadata:
                raise

    def _install(self):
        if self.is_wheel:
            self.install_wheel()
        else:
            self.install_sdist()


class Installer(SdistInstaller):
    """Installer to handle editable.
    """
    def __init__(self, *args, **kwargs):
        super(Installer, self).__init__(*args, **kwargs)

    @property
    def src_dir(self):
        build_dir = os.environ.get("PIP_SRC", None)
        venv = os.environ.get("VIRTUAL_ENV", None)
        if venv:
            src_dir = os.path.join(venv, "src")
            if os.path.exists(src_dir):
                build_dir = src_dir
        if not build_dir:
            build_dir = vistir.path.create_tracked_tempdir("passa-build-dir")
        return build_dir


def _iter_egg_info_directories(root, name):
    name = packaging.utils.canonicalize_name(name)
    for parent, dirnames, filenames in os.walk(root):
        matched_indexes = []
        for i, dirname in enumerate(dirnames):
            if not dirname.lower().endswith("egg-info"):
                continue
            egg_info_name = packaging.utils.canonicalize_name(dirname[:-9])
            if egg_info_name != name:
                continue
            matched_indexes.append(i)
            yield os.path.join(parent, dirname)

        # Modify dirnames in-place to NOT look into egg-info directories.
        # This is a documented behavior in stdlib.
        for i in reversed(matched_indexes):
            del dirnames[i]


def _read_pkg_info(directory):
    path = os.path.join(directory, "PKG-INFO")
    try:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except (IOError, OSError):
        return None


def _find_egg_info(ireq):
    """Find this package's .egg-info directory.

    Due to how sdists are designed, the .egg-info directory cannot be reliably
    found without running setup.py to aggregate all configurations. This
    function instead uses some heuristics to locate the egg-info directory
    that most likely represents this package.

    The best .egg-info directory's path is returned as a string. None is
    returned if no matches can be found.
    """
    root = ireq.setup_py_dir

    directory_iterator = _iter_egg_info_directories(root, ireq.name)
    try:
        top_egg_info = next(directory_iterator)
    except StopIteration:   # No egg-info found. Wat.
        return None
    directory_iterator = itertools.chain([top_egg_info], directory_iterator)

    # Read the sdist's PKG-INFO to determine which egg_info is best.
    pkg_info = _read_pkg_info(root)

    # PKG-INFO not readable. Just return whatever comes first, I guess.
    if pkg_info is None:
        return top_egg_info

    # Walk the sdist to find the egg-info with matching PKG-INFO.
    for directory in directory_iterator:
        egg_pkg_info = _read_pkg_info(directory)
        if egg_pkg_info == pkg_info:
            return directory

    # Nothing matches...? Use the first one we found, I guess.
    return top_egg_info


def get_sdist(ireq):
    egg_info_dir = _find_egg_info(ireq)
    if not egg_info_dir:
        return None
    return distlib.database.EggInfoDistribution(egg_info_dir)


def read_sdist_metadata(ireq):
    sdist = get_sdist(ireq)
    if not sdist:
        return None
    return sdist.metadata
