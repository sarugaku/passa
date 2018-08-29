# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import contextlib
import distutils.log
import os
import sys
import sysconfig

import distlib.scripts
import distlib.wheel
import packaging.markers
import packaging.utils
import packaging.version
import pkg_resources
import requirementslib
import setuptools.dist
import vistir

from ._pip import build_wheel
from .utils import filter_sources


def _distutils_log_wrapped(log, level, msg, args):
    if level < distutils.log.ERROR:
        return
    distutils.log.Log._log(log, level, msg, args)


@contextlib.contextmanager
def _suppress_distutils_logs():
    f = distutils.log.Log._log
    distutils.log.Log._log = _distutils_log_wrapped
    yield
    distutils.log.Log._log = f


def _build_paths():
    """Prepare paths for distlib.wheel.Wheel to install into.
    """
    paths = sysconfig.get_paths()
    return {
        "prefix": sys.prefix,
        "data": paths["data"],
        "scripts": paths["scripts"],
        "headers": paths["include"],
        "purelib": paths["purelib"],
        "platlib": paths["platlib"],
    }


def _install_as_editable(requirement):
    ireq = requirement.as_ireq()
    with vistir.cd(ireq.setup_py_dir), _suppress_distutils_logs():
        # Access from Setuptools to make sure we have currect patches.
        setuptools.dist.distutils.core.run_setup(
            ireq.setup_py, ["--quiet", "develop", "--no-deps"],
        )


def _install_as_wheel(requirement, sources, paths):
    ireq = requirement.as_ireq()
    sources = filter_sources(requirement, sources)
    hashes = requirement.hashes or None
    # TODO: Provide some sort of cache so we don't need to build each ephemeral
    # wheels twice if lock and sync is done in the same process.
    wheel_path = build_wheel(ireq, sources, hashes)
    if not wheel_path or not os.path.exists(wheel_path):
        raise RuntimeError("failed to build wheel from {}".format(ireq))
    wheel = distlib.wheel.Wheel(wheel_path)
    wheel.install(paths, distlib.scripts.ScriptMaker(None, None))


PROTECTED_FROM_CLEAN = {"setuptools", "pip"}


def _should_uninstall(name, distro, whitelist, for_sync):
    if name in PROTECTED_FROM_CLEAN:
        return False
    try:
        package = whitelist[name]
    except KeyError:
        return True
    if not for_sync:
        return False

    r = requirementslib.Requirement.from_pipfile(name, package)

    # Always remove and re-sync non-named requirements. pip does this?
    if not r.is_named:
        return True

    # Remove packages with unmatched version. The comparison is done is
    # strings to avoid type mismatching due to vendering.
    if str(r.get_version()) != str(packaging.version.parse(distro.version)):
        return True


def _is_installation_local(distro):
    """Check whether the distribution is in the current Python installation.

    This is used to distinguish packages seen by a virtual environment. A venv
    may be able to see global packages, but we don't want to mess with them.
    """
    return os.path.commonprefix([distro.location, sys.prefix]) == sys.prefix


def _group_installed_names(whitelist, for_sync):
    names_to_clean = set()
    names_kept = set()
    for distro in pkg_resources.working_set:
        name = packaging.utils.canonicalize_name(distro.project_name)
        if (_should_uninstall(name, distro, whitelist, for_sync) and
                _is_installation_local(distro)):
            names_to_clean.add(name)
        else:
            names_kept.add(name)
    return names_to_clean, names_kept


def _clean(whitelist, for_sync):
    names_to_clean, names_kept = _group_installed_names(whitelist, for_sync)

    # TODO: Show a prompt to confirm cleaning. We will need to implement a
    # reporter pattern for this as well.
    for name in names_to_clean:
        r = requirementslib.Requirement.from_line(name)
        r.as_ireq().uninstall(auto_confirm=True, verbose=False)
    return names_to_clean, names_kept


def _get_packages(lockfile, default, develop):
    # Don't need to worry about duplicates because only extras can differ.
    # Extras don't matter because they only affect dependencies, and we
    # don't install dependencies anyway!
    packages = {}
    if default:
        packages.update(lockfile.default._data)
    if develop:
        packages.update(lockfile.develop._data)
    return packages


class Synchronizer(object):
    """Helper class to install packages from a project's lock file.
    """
    def __init__(self, project, default, develop):
        self._root = project.root   # Only for repr.
        self.packages = _get_packages(project.lockfile, default, develop)
        self.sources = project.lockfile.meta.sources._data
        self.paths = _build_paths()

    def __repr__(self):
        return "<{0} @ {1!r}>".format(type(self).__name__, self._root)

    def sync(self):
        cleaned_names, installed_names = _clean(self.packages, for_sync=True)
        # TODO: Specify installation order? (pypa/pipenv#2274)

        installed = set()
        updated = set()
        skipped = set()
        for name, package in self.packages.items():
            if name in installed_names:
                continue
            r = requirementslib.Requirement.from_pipfile(name, package)
            if r.markers and not packaging.markers.Marker(r.markers).evaluate():
                skipped.add(r.normalized_name)
                continue
            if r.editable:
                _install_as_editable(r)
            else:
                _install_as_wheel(r, self.sources, self.paths)
            name = r.normalized_name
            if name in cleaned_names:
                updated.add(name)
                cleaned_names.remove(name)
            else:
                installed.add(name)

        return installed, updated, skipped, cleaned_names

    def clean(self):
        cleaned_names, kept_names = _clean(self.packages, for_sync=False)
        return cleaned_names, kept_names
