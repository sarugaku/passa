# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import os
import sys

import distlib.scripts
import distlib.wheel
import requirementslib
import setuptools.dist
import vistir

from ._pip import build_wheel
from .utils import filter_sources


def _build_paths():
    """Prepare paths for distlib.wheel.Wheel to install into.

    I reverse-engineered a lot for most of these. They could be terribly wrong.
    We'll find out.
    """
    prefix = os.environ.get("VIRTUAL_ENV")
    if not prefix:
        raise RuntimeError("virtual environment required for sync")
    if sys.platform == "win32":
        return {
            "prefix": prefix,
            "scripts": os.path.join(prefix, "Scripts"),
            "headers": os.path.join(prefix, "Include"),
            "data": prefix,     # ?
            "purelib": os.path.join(prefix, "Lib", "site-packages"),
            "platlib": os.path.join(prefix, "Lib", "site-packages"),
        }
    libpath = os.path.join(
        prefix, "lib",
        "python{0[0]}.{0[1]}".format(sys.version_info),
        "site-packages",
    )
    return {
        "prefix": prefix,
        "scripts": os.path.join(prefix, "bin"),
        "headers": os.path.join(prefix, "include"),
        "data": prefix,     # ?
        "purelib": libpath,
        "platlib": libpath,
    }


def _install_as_source(requirement):
    ireq = requirement.as_ireq()
    args = ["develop"] if requirement.editable else ["install"]
    with vistir.cd(ireq.setup_py_dir):
        setuptools.dist.distutils.core.run_setup(ireq.setup_py, args)


def _install_as_wheel(requirement, sources, paths):
    ireq = requirement.as_ireq()
    sources = filter_sources(requirement, sources)
    hashes = requirement.hashes or None
    wheel_path = build_wheel(ireq, sources, hashes)
    if not wheel_path or not os.path.exists(wheel_path):
        raise RuntimeError("failed to build wheel from {}".format(ireq))
    wheel = distlib.wheel.Wheel(wheel_path)
    wheel.install(paths, distlib.scripts.ScriptMaker(None, None))


def _install_section(section, sources, paths):
    for name, package in section.items():
        requirement = requirementslib.Requirement.from_pipfile(
            name, package._data,
        )
        if requirement.is_named:
            _install_as_wheel(requirement, sources, paths)
        else:
            _install_as_source(requirement)


class Synchronizer(object):
    """Helper class to install packages from a project's lock file.
    """
    def __init__(self, project):
        self.project = project
        self.paths = _build_paths()

    def __repr__(self):
        return "<{0} @ {1!r}>".format(type(self).__name__, self.project.root)

    def install(self, default, develop):
        lockfile = self.project.lockfile
        sources = lockfile.meta.sources._data
        # XXX: This could have problems if there are duplicate entries between
        # sections with different content (like extras)? We might need to
        # consolidate first, and then install.
        if default:
            _install_section(lockfile.default, sources, self.paths)
        if develop:
            _install_section(lockfile.develop, sources, self.paths)
