import importlib
import os

import packaging.version
import pip_shims
import six

from .caches import CACHE_DIR
from .utils import cheesy_temporary_directory, ensure_mkdir_p, mkdir_p


# HACK: Can we get pip_shims to support these in time?
def _import_module_of(obj):
    return importlib.import_module(obj.__module__)


WheelBuilder = _import_module_of(pip_shims.Wheel).WheelBuilder
unpack_url = _import_module_of(pip_shims.is_file_url).unpack_url


@ensure_mkdir_p(mode=0o775)
def _get_src_dir():
    src = os.environ.get("PIP_SRC")
    if src:
        return src
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        return os.path.join(virtual_env, "src")
    temp_src = cheesy_temporary_directory(prefix='passa-src')
    return temp_src


def _prepare_wheel_building_kwargs(ireq):
    download_dir = os.path.join(CACHE_DIR, "pkgs")
    mkdir_p(download_dir)

    wheel_download_dir = os.path.join(CACHE_DIR, "wheels")
    mkdir_p(wheel_download_dir)

    if ireq.source_dir is None:
        src_dir = _get_src_dir()
    else:
        src_dir = ireq.source_dir

    # This logic matches pip's behavior, although I don't fully understand the
    # intention. I guess the idea is to build editables in-place, otherwise out
    # of the source tree?
    if ireq.editable:
        build_dir = src_dir
    else:
        build_dir = cheesy_temporary_directory(prefix="passa-build")

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
    name = 'PipCommand'


def _get_pip_session(trusted_hosts):
    cmd = _PipCommand()
    options, _ = cmd.parser.parse_args([])
    options.cache_dir = CACHE_DIR
    options.trusted_hosts = trusted_hosts
    session = cmd._build_session(options)
    return session


def _get_finder_session(sources):
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


def _build_wheel_pre10(ireq, output_dir, finder, wheel_cache, kwargs):
    kwargs["wheel_cache"] = wheel_cache
    reqset = pip_shims.RequirementSet(**kwargs)
    builder = WheelBuilder(reqset, finder)
    return builder._build_one(ireq, output_dir)


def _build_wheel_10x(ireq, output_dir, finder, wheel_cache, kwargs):
    kwargs.update({"progress_bar": "off", "build_isolation": False})
    preparer = pip_shims.RequirementPreparer(**kwargs)
    builder = WheelBuilder(finder, preparer, wheel_cache)
    return builder._build_one(ireq, output_dir)


def _build_wheel_modern(ireq, output_dir, finder, wheel_cache, kwargs):
    kwargs.update({"progress_bar": "off", "build_isolation": False})
    with pip_shims.RequirementTracker() as req_tracker:
        kwargs["req_tracker"] = req_tracker
        preparer = pip_shims.RequirementPreparer(**kwargs)
        builder = WheelBuilder(finder, preparer, wheel_cache)
        return builder._build_one(ireq, output_dir)


def _build_wheel(*args):
    """Shim for wheel building in various pip versions.

    For all build functions, the arguments are:

    * ireq: The InstallRequirement object to build
    * output_dir: The directory to build the wheel in.
    * finder: pip's internal Finder object to find the source out of ireq.
    * kwargs: Various keyword arguments from `_prepare_wheel_building_kwargs`.
    """
    pip_version = packaging.version.parse(pip_shims.pip_version)
    if pip_version < packaging.version.parse("10"):
        return _build_wheel_pre10(*args)
    elif pip_version < packaging.version.parse("18"):
        return _build_wheel_10x(*args)
    return _build_wheel_modern(*args)


def build_wheel(ireq, sources):
    """Build a wheel file for the InstallRequirement object.

    An artifact is downloaded (or read from cache). If the artifact is not a
    wheel, build one out of it. The dynamically built wheel is ephemeral; do
    not depend on its existence after the returned wheel goes out of scope.

    Returns the wheel's path on disk, or None if the wheel cannot be built.
    """
    kwargs = _prepare_wheel_building_kwargs(ireq)
    finder, session = _get_finder_session(sources)

    # Not for upgrade, hash not required.
    ireq.populate_link(finder, False, False)

    # Ensure ireq.source_dir is set.
    # This is intentionally set to build_dir, not src_dir. Comments from pip:
    #   [...] if filesystem packages are not marked editable in a req, a non
    #   deterministic error occurs when the script attempts to unpack the
    #   build directory.
    # Also see comments in `_prepare_wheel_building_kwargs()` -- If the ireq
    # is editable, build_dir is actually src_dir, making the build in-place.
    ireq.ensure_has_source_dir(kwargs["build_dir"])

    # Ensure the remote artifact is downloaded locally. For wheels, it is
    # enough to just download because we'll use them directly. For an sdist,
    # we need to unpack so we can build it.
    if not pip_shims.is_file_url(ireq.link):
        if ireq.is_wheel:
            only_download = True
            download_dir = kwargs["wheel_download_dir"]
        else:
            only_download = False
            download_dir = kwargs["download_dir"]
        unpack_url(
            ireq.link, ireq.source_dir, download_dir,
            only_download=only_download, session=session,
            hashes=ireq.hashes(True), progress_bar=False,
        )

    # If this is a wheel, use the downloaded thing.
    if ireq.is_wheel:
        output_dir = kwargs["wheel_download_dir"]
        return os.path.join(output_dir, ireq.link.filename)

    # Othereise we need to build an ephemeral wheel.
    output_dir = cheesy_temporary_directory(prefix="ephem")
    format_control = pip_shims.FormatControl(set(), set())
    wheel_cache = pip_shims.WheelCache(CACHE_DIR, format_control)
    wheel_path = _build_wheel(ireq, output_dir, finder, wheel_cache, kwargs)
    return wheel_path


def _obtrain_ref(vcs_obj, src_dir, name, rev=None):
    target_dir = os.path.join(src_dir, name)
    target_rev = vcs_obj.make_rev_options(rev)
    if not os.path.exists(target_dir):
        vcs_obj.obtain(target_dir)
    if (not vcs_obj.is_commit_id_equal(target_dir, rev) and
            not vcs_obj.is_commit_id_equal(target_dir, target_rev)):
        vcs_obj.update(target_dir, target_rev)
    return vcs_obj.get_revision(target_dir)


def get_vcs_ref(requirement):
    backend = pip_shims.VcsSupport()._registry.get(requirement.vcs)
    vcs = backend(url=requirement.req.vcs_uri)
    src = _get_src_dir()
    name = requirement.normalized_name
    ref = _obtrain_ref(vcs, src, name, rev=requirement.req.ref)
    return ref


def find_installation_candidates(ireq, sources):
    finder, _ = _get_finder_session(sources)
    return finder.find_all_candidates(ireq.name)
