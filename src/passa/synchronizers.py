# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import os
import sys
import sysconfig

import distlib.scripts
import distlib.wheel
import requirementslib
import setuptools.dist
import vistir

from ._pip import build_wheel
from .utils import filter_sources


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
    with vistir.cd(ireq.setup_py_dir):
        # Access from Setuptools to make sure we have currect patches.
        setuptools.dist.distutils.core.run_setup(
            ireq.setup_py, ["develop", "--no-deps"],
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


def _install_requirement(requirement, sources, paths):
    if requirement.editable:
        _install_as_editable(requirement)
    else:
        _install_as_wheel(requirement, sources, paths)


class Synchronizer(object):
    """Helper class to install packages from a project's lock file.
    """
    def __init__(self, project):
        self.project = project
        self.paths = _build_paths()

    def __repr__(self):
        return "<{0} @ {1!r}>".format(type(self).__name__, self.project.root)

    def _get_packages(self, default, develop):
        # Don't need to worry about duplicates because only extras can differ.
        # Extras don't matter because they only affect dependencies, and we
        # don't install dependencies anyway!
        packages = {}
        if default:
            packages.update(self.project.lockfile.default)
        if develop:
            packages.update(self.project.lockfile.develop)
        return packages

    def install(self, default, develop):
        sources = self.project.lockfile.meta.sources._data
        for name, package in self._get_packages(default, develop).items():
            # TODO: Specify installation order? (pypa/pipenv#2274)
            requirement = requirementslib.Requirement.from_pipfile(
                name, package._data,
            )
            _install_requirement(requirement, sources, self.paths)
