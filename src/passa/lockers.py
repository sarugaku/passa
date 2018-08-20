# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import itertools

import plette
import requirementslib
import resolvelib
import vistir

from .caches import HashCache
from .hashes import get_hashes
from .metadata import set_metadata
from .providers import EagerRequirementsLibProvider, RequirementsLibProvider
from .reporters import StdOutReporter
from .traces import trace_graph
from .utils import identify_requirment


def _get_requirements(pipfile, section_name):
    """Produce a mapping of identifier: requirement from the section.
    """
    return {identify_requirment(r): r for r in (
        requirementslib.Requirement.from_pipfile(name, package._data)
        for name, package in pipfile.get(section_name, {}).items()
    )}


def _iter_derived_entries(state, traces, names):
    """Produce a mapping containing all candidates derived from `names`.

    `name` should provide a collection of requirement identifications from
    a section (i.e. `packages` or `dev-packages`). This function uses `trace`
    to filter out candidates in the state that are present because of an entry
    in that collection.
    """
    if not names:
        return
    names = set(names)
    for name, requirement in state.mapping.items():
        routes = {trace[1] for trace in traces[name] if len(trace) > 1}
        if name not in names and not (names & routes):
            continue
        yield (
            requirement.normalized_name,
            next(iter(requirement.as_pipfile().values()))
        )


class Locker(object):
    """Helper class to produce a new lock file for a project.
    """
    def __init__(self, project):
        pipfile = project.pipfile
        lockfile = project.lockfile

        self.root = project.root
        self.default_requirements = _get_requirements(
            pipfile, "packages",
        )
        self.develop_requirements = _get_requirements(
            pipfile, "dev-packages",
        )

        # This comprehension dance ensures we merge packages from both
        # sections, and definitions in the default section win.
        self.requirements = {k: r for k, r in itertools.chain(
            self.develop_requirements.items(),
            self.default_requirements.items(),
        )}.values()

        self.sources = [s._data.copy() for s in pipfile.sources]
        self.allow_prereleases = bool(
            pipfile.get("pipenv", {}).get("allow_prereleases", False),
        )

        if lockfile:
            self.preferred_pins = _get_requirements(lockfile, "develop")
            self.preferred_pins.update(_get_requirements(lockfile, "default"))
        else:
            self.preferred_pins = {}

        def on_locking_success():
            project.lockfile = self.lockfile

        self.on_locking_success = on_locking_success
        self.lockfile = plette.Lockfile.with_meta_from(project.pipfile)

    def get_provider(self):
        return RequirementsLibProvider(
            self.requirements, self.sources, self.preferred_pins,
            self.allow_prereleases,
        )

    def get_reporter(self):
        # TODO: Build SpinnerReporter, and use this only in verbose mode.
        return StdOutReporter(self.requirements)

    def lock(self):
        """Lock specified (abstract) requirements into (concrete) candidates.

        The locking procedure consists of four stages:

        * Resolve versions and dependency graph (powered by ResolveLib).
        * Walk the graph to determine "why" each candidate came to be, i.e.
          what top-level requirements result in a given candidate.
        * Populate hashes for resolved candidates.
        * Populate markers based on dependency specifications of each
          candidate, and the dependency graph.
        """
        provider = self.get_provider()
        reporter = self.get_reporter()
        resolver = resolvelib.Resolver(provider, reporter)

        with vistir.cd(self.root):
            state = resolver.resolve(self.requirements)

        traces = trace_graph(state.graph)

        hash_cache = HashCache()
        for r in state.mapping.values():
            if not r.hashes:
                r.hashes = get_hashes(hash_cache, r)

        set_metadata(
            state.mapping, traces,
            provider.fetched_dependencies, provider.requires_pythons,
        )

        self.lockfile["default"] = dict(_iter_derived_entries(
            state, traces, self.default_requirements,
        ))
        self.lockfile["develop"] = dict(_iter_derived_entries(
            state, traces, self.develop_requirements,
        ))

        self.on_locking_success()


class EagerLocker(Locker):
    """A specialized locker to handle the "eager" upgrade strategy.

    See :class:`passa.providers.EagerRequirementsLibProvider` for more
    information.
    """
    def __init__(self, tracked_names, *args, **kwargs):
        super(EagerLocker, self).__init__(*args, **kwargs)
        self.tracked_names = tracked_names

    def get_provider(self):
        return EagerRequirementsLibProvider(
            self.tracked_names,
            self.requirements, self.sources, self.preferred_pins,
            self.allow_prereleases,
        )
