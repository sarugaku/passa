# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals, print_function

import collections
import contextlib
import os
import sys
import sysconfig

import distlib.wheel
import pkg_resources

import packaging.markers
import packaging.version
import requirementslib

from ..internals._pip import uninstall, Installer


def _is_installation_local(name, environment=None):
    """Check whether the distribution is in the current Python installation.

    This is used to distinguish packages seen by a virtual environment. A environment
    may be able to see global packages, but we don't want to mess with them.
    """
    if environment:
        return environment.is_installed(name)
    loc = os.path.normcase(pkg_resources.working_set.by_key[name].location)
    pre = os.path.normcase(sys.prefix)
    return os.path.commonprefix([loc, pre]) == pre


def _is_up_to_date(distro, version):
    # This is done in strings to avoid type mismatches caused by vendering.
    return str(version) == str(packaging.version.parse(distro.version))


GroupCollection = collections.namedtuple("GroupCollection", [
    "uptodate", "outdated", "noremove", "unneeded",
])


def _group_installed_names(packages, environment=None):
    """Group locally installed packages based on given specifications.

    `packages` is a name-package mapping that are used as baseline to
    determine how the installed package should be grouped.

    `environment` is the virtual environment object of the virtualenv being installed into.

    Returns a 3-tuple of disjoint sets, all containing names of installed
    packages:

    * `uptodate`: These match the specifications.
    * `outdated`: These installations are specified, but don't match the
        specifications in `packages`.
    * `unneeded`: These are installed, but not specified in `packages`.
    """
    groupcoll = GroupCollection(set(), set(), set(), set())

    if environment:
        working_set = environment.get_working_set()
    else:
        working_set = pkg_resources.working_set

    for dist in working_set:
        name = dist.key
        try:
            package = packages[name]
        except KeyError:
            groupcoll.unneeded.add(name)
            continue

        r = requirementslib.Requirement.from_pipfile(name, package)
        if not r.is_named:
            # Always mark non-named. I think pip does something similar?
            groupcoll.outdated.add(name)
        elif not _is_up_to_date(dist, r.get_version()):
            groupcoll.outdated.add(name)
        else:
            groupcoll.uptodate.add(name)

    return groupcoll


@contextlib.contextmanager
def _remove_package(name, environment=None):
    if name is None or not _is_installation_local(name, environment=environment):
        yield None
        return
    _uninstall = uninstall
    if environment:
        _uninstall = environment.uninstall
    with _uninstall(name, auto_confirm=True, verbose=False) as uninstaller:
        yield uninstaller


def _get_packages(lockfile, default, develop):
    # Don't need to worry about duplicates because only extras can differ.
    # Extras don't matter because they only affect dependencies, and we
    # don't install dependencies anyway!
    packages = {}
    if develop:
        packages.update(lockfile.develop._data)
    if default:
        packages.update(lockfile.default._data)
    return packages


def _build_paths(environment=None):
    """Prepare paths for distlib.wheel.Wheel to install into.
    """
    if environment:
        paths = environment.paths
    else:
        paths = sysconfig.get_paths()
    return {
        "prefix": sys.prefix if not environment else environment.prefix.as_posix(),
        "data": paths["data"],
        "scripts": paths["scripts"],
        "headers": paths["include"],
        "purelib": paths["purelib"],
        "platlib": paths["platlib"],
    }


PROTECTED_FROM_CLEAN = {"setuptools", "pip", "wheel"}


def _clean(names, environment=None):
    cleaned = set()
    for name in names:
        if name in PROTECTED_FROM_CLEAN:
            continue
        with _remove_package(name, environment=environment) as uninst:
            if uninst:
                cleaned.add(name)
    return cleaned


class Synchronizer(object):
    """Helper class to install packages from a project's lock file.
    """
    def __init__(self, project, default, develop, clean_unneeded, environment=None):
        self._root = project.root   # Only for repr.
        self.project = project
        self.packages = _get_packages(project.lockfile, default, develop)
        self.sources = project.lockfile.meta.sources._data
        self.clean_unneeded = clean_unneeded
        if not environment:
            self._environment = getattr(project, "environment", None)
        else:
            self._environment = environment
        super(Synchronizer, self).__init__()
        self.paths = _build_paths(environment=self.environment)

    @property
    def environment(self):
        if self._environment:
            return self._environment
        return self.project.environment

    def __repr__(self):
        return "<{0} @ {1!r}>".format(type(self).__name__, self._root)

    def sync(self):
        if not self.environment:
            return self._sync()
        with self.environment.activated():
            return self._sync()

    def _sync(self):
        groupcoll = _group_installed_names(self.packages, environment=self.environment)

        installed = set()
        updated = set()
        cleaned = set()

        # TODO: Show a prompt to confirm cleaning. We will need to implement a
        # reporter pattern for this as well.
        if self.clean_unneeded:
            names = _clean(groupcoll.unneeded, environment=self.environment)
            cleaned.update(names)

        # TODO: Specify installation order? (pypa/pipenv#2274)
        installers = []
        for name, package in self.packages.items():
            r = requirementslib.Requirement.from_pipfile(name, package)
            name = r.normalized_name
            if name in groupcoll.uptodate:
                continue
            markers = r.markers
            if markers and not packaging.markers.Marker(markers).evaluate():
                continue
            r.markers = None
            installer = Installer(r, sources=self.sources, environment=self.environment)
            try:
                installer.prepare()
            except Exception as e:
                if os.environ.get("PASSA_NO_SUPPRESS_EXCEPTIONS"):
                    raise
                print("failed to prepare {0!r}: {1}".format(
                    r.as_line(include_hashes=False), e,
                ))
            else:
                installers.append((name, installer))

        for name, installer in installers:
            if name in groupcoll.outdated:
                name_to_remove = name
            else:
                name_to_remove = None
            try:
                with _remove_package(name_to_remove, environment=self.environment):
                    installer.install()
            except Exception as e:
                if os.environ.get("PASSA_NO_SUPPRESS_EXCEPTIONS"):
                    raise
                print("failed to install {0!r}: {1}".format(
                    r.as_line(include_hashes=False), e,
                ))
                continue
            if name in groupcoll.outdated or name in groupcoll.noremove:
                updated.add(name)
            else:
                installed.add(name)

        return installed, updated, cleaned


class Cleaner(object):
    """Helper class to clean packages not in a project's lock file.
    """
    def __init__(self, project, default, develop, sync=True, verbose=False):
        self._root = project.root   # Only for repr.
        self.packages = _get_packages(project.lockfile, default, develop)
        self.sync = sync
        self.project = project

    def __repr__(self):
        return "<{0} @ {1!r}>".format(type(self).__name__, self._root)

    def print(self, packages):
        if not self.sync:
            message = "Would clean: {0}"
        else:
            message = "Cleaned: {0}"
        print(message.format(", ".join(sorted(set(packages)))))

    def clean(self):
        groupcoll = _group_installed_names(self.packages, environment=self.project.environment)
        cleaned = set()
        if self.sync:
            cleaned = _clean(groupcoll.unneeded, environment=self.project.environment)
        else:
            return groupcoll.unneeded
        return cleaned
