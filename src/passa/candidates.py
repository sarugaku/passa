import os
import sys

import packaging.specifiers
import packaging.version
import requirementslib

from ._pip import find_installation_candidates, get_vcs_ref


def _filter_matching_python_requirement(candidates):
    python_version = os.environ.get(
        "PASSA_PYTHON_VERSION",
        "{0[0]}.{0[1]}".format(sys.version_info),
    )
    if python_version == ":all:":
        python_version = None
    else:
        python_version = packaging.version.parse(python_version)
    for c in candidates:
        try:
            requires_python = c.requires_python
        except AttributeError:
            requires_python = c.location.requires_python
        if python_version is not None and requires_python:
            # Old specifications had people setting this to single digits
            # which is effectively the same as '>=digit,<digit+1'
            if requires_python.isdigit():
                requires_python = '>={0},<{1}'.format(
                    requires_python, int(requires_python) + 1,
                )
            try:
                specset = packaging.specifiers.SpecifierSet(requires_python)
            except packaging.specifiers.InvalidSpecifier:
                continue
            if not specset.contains(python_version):
                continue
        yield c


def _find_versions_from_pip(ireq, sources, allows_pre):
    icans = find_installation_candidates(ireq, sources)
    matching_icans = list(_filter_matching_python_requirement(icans))
    icans = matching_icans or icans
    versions = ireq.specifier.filter((c.version for c in icans), allows_pre)
    return versions


def _copy_requirement(requirement):
    name, data = next(iter(requirement.as_pipfile().items()))
    return requirementslib.Requirement.from_pipfile(name, data)


def _requirement_from_metadata(name, version, extras, index):
    # Markers are intentionally dropped here. They will be added to candidates
    # after resolution, so we can perform marker aggregation.
    r = requirementslib.Requirement.from_metadata(name, version, extras, None)
    r.index = index
    return r


def find_candidates(requirement, sources, allows_prereleases):
    # A non-named requirement has exactly one candidate that is itself. For
    # VCS, we also lock the requirement to an exact ref.
    if not requirement.is_named:
        candidate = _copy_requirement(requirement)
        if candidate.is_vcs:
            candidate.req.ref = get_vcs_ref(candidate)
        return [candidate]

    ireq = requirement.as_ireq()
    versions = _find_versions_from_pip(ireq, sources, allows_prereleases)
    if versions is None:
        raise RuntimeError("failed to find matches for {}".format(
            requirement.as_line(),
        ))

    name = requirement.normalized_name
    extras = requirement.extras
    index = requirement.index
    return [
        _requirement_from_metadata(name, version, extras, index)
        for version in sorted(versions)
    ]
