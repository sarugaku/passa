# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import os

import resolvelib

from .candidates import find_candidates
from .dependencies import get_dependencies
from .utils import identify_requirment


def _filter_sources(requirement, sources):
    if not sources or not requirement.index:
        return sources
    for s in sources:
        if s.get("name") == requirement.index:
            return [s]
    return sources


class RequirementsLibProvider(resolvelib.AbstractProvider):
    """Provider implementation to interface with `requirementslib.Requirement`.
    """
    def __init__(self, root_requirements, sources, allow_prereleases):
        self.sources = sources
        self.allow_prereleases = bool(allow_prereleases)
        self.invalid_candidates = set()

        # Remember dependencies of each pinned candidate. The resolver calls
        # `get_dependencies()` only when it wants to repin, so the last time
        # the dependencies we got when it is last called on a package, are
        # the set used by the resolver. We use this later to trace how a given
        # dependency is specified by a package.
        self.fetched_dependencies = {}

    def identify(self, dependency):
        return identify_requirment(dependency)

    def get_preference(self, resolution, candidates, information):
        return len(candidates)

    def find_matches(self, requirement):
        # TODO: Implement per-package prereleases flag. (pypa/pipenv#1696)
        allow_prereleases = self.allow_prereleases
        sources = _filter_sources(requirement, self.sources)
        candidates = find_candidates(requirement, sources, allow_prereleases)
        return candidates

    def is_satisfied_by(self, requirement, candidate):
        # A non-named requirement has exactly one candidate, as implemented in
        # `find_matches()`. It must match.
        if not requirement.is_named:
            return True

        # Optimization: Everything matches if there are no specifiers.
        if not requirement.specifiers:
            return True

        # We can't handle old version strings before PEP 440. Drop them all.
        # Practically this shouldn't be a problem if the user is specifying a
        # remotely reasonable dependency not from before 2013.
        candidate_line = candidate.as_line()
        if candidate_line in self.invalid_candidates:
            return False
        try:
            version = candidate.get_specifier().version
        except ValueError:
            print('ignoring invalid version {}'.format(candidate_line))
            self.invalid_candidates.add(candidate_line)
            return False

        return requirement.as_ireq().specifier.contains(version)

    def get_dependencies(self, candidate):
        sources = _filter_sources(candidate, self.sources)
        try:
            dependencies = get_dependencies(candidate, sources=sources)
        except Exception as e:
            if os.environ.get("PASSA_NO_SUPPRESS_EXCEPTIONS"):
                raise
            print('failed to get dependencies for {0!r}: {1}'.format(
                candidate.as_line(), e,
            ))
            return []
        self.fetched_dependencies[self.identify(candidate)] = {
            self.identify(r): r for r in dependencies
        }
        return dependencies
