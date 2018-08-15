import importlib
import os

import packaging.version
import pip_shims
import six

from .caches import CACHE_DIR
from .utils import cheesy_temporary_directory, mkdir_p


# HACK: Can we get pip_shims to support these in time?
def _import_module_of(obj):
    return importlib.import_module(obj.__module__)


WheelBuilder = _import_module_of(pip_shims.Wheel).WheelBuilder
unpack_url = _import_module_of(pip_shims.is_file_url).unpack_url


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
    name = 'PipCommand'


def _get_pip_options():
    cmd = _PipCommand()
    options, _ = cmd.parser.parse_args([])
    return options


def _get_pip_session(trusted_hosts):
    cmd = _PipCommand()
    options = _get_pip_options()
    options.cache_dir = CACHE_DIR
    options.trusted_hosts = trusted_hosts
    session = cmd._build_session(options)
    return session


def _get_internal_objects(sources):
    index_urls, trusted_hosts = _get_pip_index_urls(sources)
    session = _get_pip_session(trusted_hosts)
    finder = pip_shims.PackageFinder(
        find_links=[],
        index_urls=index_urls,
        trusted_hosts=trusted_hosts,
        allow_all_prereleases=True,
        session=session,
    )
    return finder, session


def _prepare_wheel_building_kwargs():
    format_control = pip_shims.FormatControl(set(), set())
    wheel_cache = pip_shims.WheelCache(CACHE_DIR, format_control)

    download_dir = os.path.join(CACHE_DIR, "pkgs")
    mkdir_p(download_dir)

    build_dir = cheesy_temporary_directory(prefix="build")
    src_dir = cheesy_temporary_directory(prefix="source")

    return {
        "wheel_cache": wheel_cache,
        "build_dir": build_dir,
        "src_dir": src_dir,
        "download_dir": download_dir,
        "wheel_download_dir": download_dir,
    }


def _build_wheel_pre10(ireq, output_dir, finder, session, kwargs):
    reqset = pip_shims.RequirementSet(**kwargs)
    builder = WheelBuilder(reqset, finder)
    return builder._build_one(ireq, output_dir)


def _build_wheel_10x(ireq, output_dir, finder, session, kwargs):
    kwargs.update({"progress_bar": "off", "build_isolation": False})
    wheel_cache = kwargs.pop("wheel_cache")
    preparer = pip_shims.RequirementPreparer(**kwargs)
    builder = WheelBuilder(finder, preparer, wheel_cache)
    return builder._build_one(ireq, output_dir)


def _build_wheel_modern(ireq, output_dir, finder, session, kwargs):
    kwargs.update({"progress_bar": "off", "build_isolation": False})
    wheel_cache = kwargs.pop("wheel_cache")
    with pip_shims.RequirementTracker() as req_tracker:
        kwargs["req_tracker"] = req_tracker
        preparer = pip_shims.RequirementPreparer(**kwargs)
        builder = WheelBuilder(finder, preparer, wheel_cache)
        return builder._build_one(ireq, output_dir)


def _build_wheel(*args):
    pip_version = packaging.version.parse(pip_shims.pip_version)
    if pip_version < packaging.version.parse("10"):
        return _build_wheel_pre10(*args)
    elif pip_version < packaging.version.parse("18"):
        return _build_wheel_10x(*args)
    return _build_wheel_modern(*args)


def _get_dependencies_from_pip(ireq, sources):
    """Retrieves dependencies for the requirement from pip internals.

    The current strategy is to build a wheel out of the ireq, and read metadata
    out of it.
    """
    kwargs = _prepare_wheel_building_kwargs()
    finder, session = _get_internal_objects(sources)

    ireq.populate_link(finder, False, False)
    ireq.ensure_has_source_dir(kwargs["src_dir"])
    unpack_url(
        ireq.link, ireq.source_dir, kwargs["download_dir"], False,
        session=session, hashes=ireq.hashes(True), progress_bar=False,
    )
    if ireq.is_wheel:
        output_dir = kwargs["download_dir"]
        path = os.path.join(output_dir, ireq.link.filename)
    else:
        output_dir = cheesy_temporary_directory(prefix="ephem")
        path = _build_wheel(ireq, output_dir, finder, session, kwargs)

    if not path or not os.path.exists(path):
        raise RuntimeError("failed to build wheel from {}".format(ireq))

    print(path)
