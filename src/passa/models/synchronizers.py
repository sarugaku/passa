# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals, print_function

import collections
import os
import sys

import pkg_resources

import packaging.markers
import packaging.version
import requirementslib

from ..internals._pip import uninstall, Installer


def _is_up_to_date(distro, version):
    # This is done in strings to avoid type mismatches caused by vendering.
    return str(version) == str(packaging.version.parse(distro.version))


GroupCollection = collections.namedtuple("GroupCollection", [
    "uptodate", "outdated", "noremove", "unneeded",
])


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


PROTECTED_FROM_CLEAN = {"setuptools", "pip", "wheel"}


class InstallManager(object):
    """A centrialized manager object to handle install and uninstall operations."""

    def __init__(self, sources=None):
        self.sources = sources

    def get_working_set(self):
        return pkg_resources.working_set

    def is_installation_local(self, name):
        """Check whether the distribution is in the current Python installation.

        This is used to distinguish packages seen by a virtual environment. A environment
        may be able to see global packages, but we don't want to mess with them.
        """
        loc = os.path.normcase(self.get_working_set().by_key[name].location)
        pre = os.path.normcase(sys.prefix)
        return os.path.commonprefix([loc, pre]) == pre

    def remove(self, name):
        if name is None or not self.is_installation_local(name):
            return False
        with uninstall(name, auto_confirm=True, verbose=False):
            return True

    def install(self, req):
        installer = Installer(req, sources=self.sources)
        try:
            installer.prepare()
        except Exception as e:
            if os.environ.get("PASSA_NO_SUPPRESS_EXCEPTIONS"):
                raise
            print("failed to prepare {0!r}: {1}".format(
                req.as_line(include_hashes=False), e,
            ))
            return False

        try:
            installer.install()
        except Exception as e:
            if os.environ.get("PASSA_NO_SUPPRESS_EXCEPTIONS"):
                raise
            print("failed to install {0!r}: {1}".format(
                req.as_line(include_hashes=False), e,
            ))
            return False
        return True

    def clean(self, names):
        cleaned = set()
        for name in names:
            if name in PROTECTED_FROM_CLEAN:
                continue
            if self.remove(name):
                cleaned.add(name)
        return cleaned


class Synchronizer(object):
    """Helper class to install packages from a project's lock file.
    """
    def __init__(self, project, default, develop, clean_unneeded, dry_run=False):
        self._root = project.root   # Only for repr.
        self.project = project
        self.packages = _get_packages(project.lockfile, default, develop)
        self.clean_unneeded = clean_unneeded
        self.dry_run = dry_run
        super(Synchronizer, self).__init__()
        sources = project.lockfile.meta.sources._data
        self.install_manager = InstallManager(sources)

    def __repr__(self):
        return "<{0} @ {1!r}>".format(type(self).__name__, self._root)

    def group_installed_names(self):
        """Group locally installed packages based on given specifications.

        Returns a 3-tuple of disjoint sets, all containing names of installed
        packages:

        * `uptodate`: These match the specifications.
        * `outdated`: These installations are specified, but don't match the
            specifications in `packages`.
        * `unneeded`: These are installed, but not specified in `packages`.
        """
        groupcoll = GroupCollection(set(), set(), set(), set())

        for dist in self.install_manager.get_working_set():
            name = dist.key
            try:
                package = self.packages[name]
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

    def sync(self):
        groupcoll = self.group_installed_names()

        installed = set()
        updated = set()
        cleaned = set()

        # TODO: Show a prompt to confirm cleaning. We will need to implement a
        # reporter pattern for this as well.
        if self.clean_unneeded:
            if not self.dry_run:
                names = self.install_manager.clean(groupcoll.unneeded)
            cleaned.update(names)

        # TODO: Specify installation order? (pypa/pipenv#2274)
        for name, package in self.packages.items():
            r = requirementslib.Requirement.from_pipfile(name, package)
            name = r.normalized_name
            if name in groupcoll.uptodate:
                continue
            markers = r.markers
            if markers and not packaging.markers.Marker(markers).evaluate():
                continue
            r.markers = None
            if not self.dry_run:
                if name in groupcoll.outdated:
                    self.install_manager.remove(name)
                success = self.install_manager.install(r)
                if not success:
                    continue

            if name in groupcoll.outdated or name in groupcoll.noremove:
                updated.add(name)
            else:
                installed.add(name)

        return installed, updated, cleaned

    def clean(self):
        groupcoll = self.group_installed_names()
        if not self.dry_run:
            return self.install_manager.clean(groupcoll.unneeded)
        else:
            return groupcoll.unneeded
