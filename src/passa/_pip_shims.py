"""Shims to make the pip interface more consistent accross versions.

There are currently two members:

* build_wheel abstracts the process to build a wheel out of a bunch parameters.
* unpack_url wraps the actual function in pip to accept modern parameters.
"""

import importlib

import packaging.version
import pip_shims


# HACK: Can we get pip_shims to support these in time?
def _import_module_of(obj):
    return importlib.import_module(obj.__module__)


WheelBuilder = _import_module_of(pip_shims.Wheel).WheelBuilder
unpack_url = _import_module_of(pip_shims.is_file_url).unpack_url

# HACK: Remove this after pip-shims updates. (sarugaku/pip-shims#6)
WheelCache = pip_shims.WheelCache
if not WheelCache:
    from pip.wheel import WheelCache


def _build_wheel_pre10(ireq, output_dir, finder, wheel_cache, kwargs):
    kwargs.update({"wheel_cache": wheel_cache, "session": finder.session})
    reqset = pip_shims.RequirementSet(**kwargs)
    builder = WheelBuilder(reqset, finder)
    return builder._build_one(ireq, output_dir)


def _build_wheel_10x(ireq, output_dir, finder, wheel_cache, kwargs):
    kwargs.update({"progress_bar": "off", "build_isolation": False})
    preparer = pip_shims.RequirementPreparer(**kwargs)
    builder = WheelBuilder(finder, preparer, wheel_cache)
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
        kwargs["req_tracker"] = req_tracker
        preparer = pip_shims.RequirementPreparer(**kwargs)
        builder = WheelBuilder(finder, preparer, wheel_cache)
        return builder._build_one(ireq, output_dir)


def _unpack_url_pre10(*args, **kwargs):
    """Shim for unpack_url in various pip versions.

    pip before 10.0 does not accept `progress_bar` here. Simply drop it.
    """
    kwargs.pop("progress_bar", None)
    return unpack_url(*args, **kwargs)


PIP_VERSION = packaging.version.parse(pip_shims.pip_version)

VERSION_10 = packaging.version.parse("10")
VERSION_18 = packaging.version.parse("18")


build_wheel = _build_wheel_modern


if PIP_VERSION < VERSION_10:
    build_wheel = _build_wheel_pre10
    unpack_url = _unpack_url_pre10
elif PIP_VERSION < VERSION_18:
    build_wheel = _build_wheel_10x
