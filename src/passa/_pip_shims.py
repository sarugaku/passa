# -*- coding=utf-8 -*-
from __future__ import absolute_import, unicode_literals
"""Shims to make the pip interface more consistent accross versions.

There are currently two members:

* build_wheel abstracts the process to build a wheel out of a bunch parameters.
* unpack_url wraps the actual function in pip to accept modern parameters.
"""

import pip_shims

SafeFileCache = pip_shims.SafeFileCache
vcs = pip_shims.VcsSupport()
FAVORITE_HASH = pip_shims.FAVORITE_HASH


def _build_wheel_pre10(ireq, output_dir, finder, wheel_cache, kwargs):
    kwargs.update({"wheel_cache": wheel_cache, "session": finder.session})
    reqset = pip_shims.RequirementSet(**kwargs)
    builder = pip_shims.WheelBuilder(reqset, finder)
    return builder._build_one(ireq, output_dir)


def _build_wheel_modern(ireq, output_dir, finder, wheel_cache, kwargs):
    """Build a wheel.

    * ireq: The InstallRequirement object to build
    * output_dir: The directory to build the wheel in.
    * finder: pip's internal Finder object to find the source out of ireq.
    * kwargs: Various keyword arguments from `_prepare_wheel_building_kwargs`.
    """
    kwargs.update({"progress_bar": "off", "build_isolation": False})
    with pip_shims.RequirementTracker() as req_tracker:
        if req_tracker:
            kwargs["req_tracker"] = req_tracker
        preparer = pip_shims.RequirementPreparer(**kwargs)
        builder = pip_shims.WheelBuilder(finder, preparer, wheel_cache)
        return builder._build_one(ireq, output_dir)


def _unpack_url_pre10(*args, **kwargs):
    """Shim for unpack_url in various pip versions.

    pip before 10.0 does not accept `progress_bar` here. Simply drop it.
    """
    kwargs.pop("progress_bar", None)
    return unpack_url(*args, **kwargs)


PIP_VERSION = pip_shims.utils._parse(pip_shims.pip_version)

VERSION_10 = pip_shims.utils._parse("10")
VERSION_18 = pip_shims.utils._parse("18")


build_wheel = _build_wheel_modern


if PIP_VERSION < VERSION_10:
    build_wheel = _build_wheel_pre10
    unpack_url = _unpack_url_pre10
