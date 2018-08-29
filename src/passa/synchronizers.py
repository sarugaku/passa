# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import collections
import contextlib
import os
import sys
import sysconfig

import pkg_resources

import packaging.markers
import packaging.version
import requirementslib

from ._pip import uninstall_requirement, EditableInstaller, WheelInstaller


def _is_installation_local(name):
    """Check whether the distribution is in the current Python installation.

    This is used to distinguish packages seen by a virtual environment. A venv
    may be able to see global packages, but we don't want to mess with them.
    """
    location = pkg_resources.working_set.by_key[name].location
    return os.path.commonprefix([location, sys.prefix]) == sys.prefix


def _is_up_to_date(distro, version):
    # This is done in strings to avoid type mismatches caused by vendering.
    return str(version) == str(packaging.version.parse(distro.version))


GroupCollection = collections.namedtuple("GroupCollection", [
    "uptodate", "outdated", "noremove", "unneeded",
])


def _group_installed_names(packages):
    """Group locally installed packages based on given specifications.

    `packages` is a name-package mapping that are used as baseline to
    determine how the installed package should be grouped.

    Returns a 3-tuple of disjoint sets, all containing names of installed
    packages:

    * `uptodate`: These match the specifications.
    * `outdated`: These installations are specified, but don't match the
        specifications in `packages`.
    * `unneeded`: These are installed, but not specified in `packages`.
    """
    groupcoll = GroupCollection(set(), set(), set(), set())

    for distro in pkg_resources.working_set:
        name = distro.key
        try:
            package = packages[name]
        except KeyError:
            groupcoll.unneeded.add(name)
            continue

        r = requirementslib.Requirement.from_pipfile(name, package)
        if not r.is_named:
            # Always mark non-named. I think pip does something similar?
            groupcoll.outdated.add(name)
        elif not _is_up_to_date(distro, r.get_version()):
            groupcoll.outdated.add(name)
        else:
            groupcoll.uptodate.add(name)

    return groupcoll


@contextlib.contextmanager
def _remove_package(name):
    if name is None or not _is_installation_local(name):
        yield
        return
    r = requirementslib.Requirement.from_line(name)
    with uninstall_requirement(r.as_ireq(), auto_confirm=True, verbose=False):
        yield


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


class Synchronizer(object):
    """Helper class to install packages from a project's lock file.
    """
    def __init__(self, project, default, develop, clean_unneeded):
        self._root = project.root   # Only for repr.
        self.packages = _get_packages(project.lockfile, default, develop)
        self.sources = project.lockfile.meta.sources._data
        self.paths = _build_paths()
        self.clean_unneeded = clean_unneeded

    def __repr__(self):
        return "<{0} @ {1!r}>".format(type(self).__name__, self._root)

    def sync(self):
        groupcoll = _group_installed_names(self.packages)

        installed = set()
        updated = set()
        cleaned = set()

        # TODO: Show a prompt to confirm cleaning. We will need to implement a
        # reporter pattern for this as well.
        if self.clean_unneeded:
            cleaned.update(groupcoll.unneeded)
            for name in cleaned:
                with _remove_package(name):
                    pass

        # TODO: Specify installation order? (pypa/pipenv#2274)
        for name, package in self.packages.items():
            r = requirementslib.Requirement.from_pipfile(name, package)
            name = r.normalized_name
            if name in groupcoll.uptodate:
                continue
            markers = r.markers
            if markers and not packaging.markers.Marker(markers).evaluate():
                continue
            if name in groupcoll.outdated:
                name_to_remove = name
            else:
                name_to_remove = None
            if r.editable:
                installer = EditableInstaller(r)
            else:
                installer = WheelInstaller(r, self.sources, self.paths)
            try:
                installer.prepare()
                with _remove_package(name_to_remove):
                    installer.install()
            except Exception as e:
                if os.environ.get("PASSA_NO_SUPPRESS_EXCEPTIONS"):
                    raise
                print("failed to install {0!r}: {1}".format(
                    r.as_line(include_hashes=False), e,
                ))
            if name in groupcoll.outdated or name in groupcoll.noremove:
                updated.add(name)
            else:
                installed.add(name)

        return installed, updated, cleaned
