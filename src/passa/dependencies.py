import functools

import packaging.utils
import packaging.version
import requests
import requirementslib.models.cache
import requirementslib.models.utils

from .dependencies_pip import _get_dependencies_from_pip
from .markers import contains_extra


DEPENDENCY_CACHE = requirementslib.models.cache.DependencyCache()


def _cached(f, **kwargs):

    @functools.wraps(f)
    def wrapped(ireq):
        result = f(ireq, **kwargs)
        if (result is not None and
                requirementslib.models.utils.is_pinned_requirement(ireq)):
            DEPENDENCY_CACHE[ireq] = result
        return result

    return wrapped


def _get_dependencies_from_cache(ireq):
    """Retrieves dependencies for the requirement from the dependency cache.
    """
    if ireq.editable:
        return

    try:
        cached = DEPENDENCY_CACHE[ireq]
    except KeyError:
        return

    # Preserving sanity: Run through the cache and make sure every entry if
    # valid. If this fails, something is wrong with the cache. Drop it.
    ireq_name = packaging.utils.canonicalize_name(ireq.name)
    try:
        broken = False
        for line in cached:
            dep_req = requirementslib.Requirement.from_line(line)
            if contains_extra(dep_req.markers):
                broken = True   # The "extra =" marker breaks everything.
            elif dep_req.normalized_name == ireq_name:
                broken = True   # A package cannot depend on itself.
            if broken:
                break
    except Exception:
        broken = True

    if broken:
        del DEPENDENCY_CACHE[ireq]
        return

    return cached


def _get_dependencies_from_json(ireq, sources):
    """Retrieves dependencies for the given install requirement from the json api.

    :param ireq: A single InstallRequirement
    :type ireq: :class:`~pip._internal.req.req_install.InstallRequirement`
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str) or None
    """

    if ireq.editable:
        return

    # It is technically possible to parse extras out of the JSON API's
    # requirement format, but it is such a chore let's just use the simple API.
    if ireq.extras:
        return

    url_prefixes = [
        proc_url[:-7]   # Strip "/simple".
        for proc_url in (
            raw_url.rstrip("/")
            for raw_url in (source.get("url", "") for source in sources)
        )
        if proc_url.endswith("/simple")
    ]

    session = requests.session()
    version = str(ireq.specifier).lstrip("=")

    dependencies = None
    for prefix in url_prefixes:
        url = "{prefix}/pypi/{name}/{version}/json".format(
            prefix=prefix,
            name=packaging.utils.canonicalize_name(ireq.name),
            version=version,
        )
        try:
            response = session.get(url)
            response.raise_for_status()
            info = response.json()["info"]
            dependencies = [
                dep_req.as_line(include_hashes=False) for dep_req in (
                    requirementslib.Requirement.from_line(line)
                    for line in info.get("requires_dist", info["requires"])
                )
                if not contains_extra(dep_req.markers)
            ]
        except Exception:
            continue
        break
    return dependencies


def get_dependencies(requirement, sources):
    """Get all dependencies for a given install requirement.

    :param requirement: A requirement
    :param sources: Pipfile-formatted sources
    :type sources: list[dict]
    :return: A set of dependency lines for generating new InstallRequirements.
    :rtype: set(str)
    """
    getters = [
        _get_dependencies_from_cache,
        _cached(_get_dependencies_from_json, sources=sources),
        _cached(_get_dependencies_from_pip, sources=sources),
    ]
    ireq = requirement.as_ireq()
    errors = []
    for getter in getters:
        try:
            deps = getter(ireq)
        except Exception as e:
            errors.append(str(e).strip())
            continue
        if deps is not None:
            return set(deps)
    raise RuntimeError("failed to get dependencies for {}: {}".format(
        requirement.as_line(), "\n".join(errors),
    ))
