# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import copy
import itertools

import packaging.markers
import packaging.specifiers
import vistir
import vistir.misc

from .markers import get_without_extra


def dedup_markers(s):
    # TODO: Implement better logic.
    deduped = sorted(vistir.misc.dedup(s))
    return deduped


def _merge_python_specifiers(*specsets):
    merged = set()
    for specset in specsets:
        for s in str(specset).split(","):
            s = s.strip()
            if not s:
                continue
            if s.endswith(".*"):
                s = s[:-2]
                merged.add(s)
                continue
            version = s.lstrip("><=!")
            if not version.isdigit():
                merged.add(s)
                continue
            number = int(version)
            operator = s[:-len(version)]
            if operator == "==":
                # "==3" => ">=3.0,<4.0".
                merged.add(">={}.0".format(number))
                merged.add("<{}.0".format(number + 1))
            else:
                # ">=3" => ">=3.0", "<4" => "<4.0", etc.
                merged.add("{}{}.0".format(operator, number))
    string = ",".join(merged)
    specset = packaging.specifiers.SpecifierSet(string)
    return specset


class MetaSet(object):
    """Representation of a "metadata set".

    This holds multiple metadata representaions. Each metadata representation
    includes a marker, and a specifier set of Python versions required.
    """
    def __init__(self):
        self.markerset = frozenset()
        self.pyspecset = packaging.specifiers.SpecifierSet()

    def __repr__(self):
        return "MetaSet(markerset={0!r}, pyspecset={1!r})".format(
            ",".join(sorted(self.markerset)), str(self.pyspecset),
        )

    def __str__(self):
        return " and ".join(dedup_markers(itertools.chain(
            # Make sure to always use the same quotes so we can dedup properly.
            (
                "({0})".format(ms) if " or " in ms else ms
                for ms in (str(m).replace('"', "'") for m in self.markerset)
            ),
            (
                "python_version {0[0]} '{0[1]}'".format(spec._spec)
                for spec in self.pyspecset._specs
            ),
        )))

    def __bool__(self):
        return bool(self.markerset or self.pyspecset)

    def __nonzero__(self):  # Python 2.
        return self.__bool__()

    def __or__(self, pair):
        marker, specset = pair
        markerset = set(self.markerset)
        if marker:
            markerset.add(str(marker))
        metaset = MetaSet()
        metaset.markerset = frozenset(markerset)
        metaset.pyspecset = _merge_python_specifiers(self.pyspecset, specset)
        return metaset


def _build_metasets(dependencies, pythons, key, trace, all_metasets):
    all_parent_metasets = []
    for route in trace:
        parent = route[-1]
        try:
            parent_metasets = all_metasets[parent]
        except KeyError:    # Parent not calculated yet. Wait for it.
            return
        all_parent_metasets.append((parent, parent_metasets))

    metaset_iters = []
    for parent, parent_metasets in all_parent_metasets:
        r = dependencies[parent][key]
        python = pythons[key]
        metaset = (
            get_without_extra(r.markers),
            packaging.specifiers.SpecifierSet(python),
        )
        metaset_iters.append(
            parent_metaset | metaset
            for parent_metaset in parent_metasets
        )
    return list(itertools.chain.from_iterable(metaset_iters))


def _calculate_metasets_mapping(dependencies, pythons, traces):
    all_metasets = {None: [MetaSet()]}

    del traces[None]
    while traces:
        new_metasets = {}
        for key, trace in traces.items():
            assert key not in all_metasets, key     # Sanity check for debug.
            metasets = _build_metasets(
                dependencies, pythons, key, trace, all_metasets,
            )
            if metasets is None:
                continue
            new_metasets[key] = metasets
        if not new_metasets:
            break   # No progress? Deadlocked. Give up.
        all_metasets.update(new_metasets)
        for key in new_metasets:
            del traces[key]

    return all_metasets


def _format_metasets(metasets):
    # If there is an unconditional route, this needs to be unconditional.
    if not metasets or not all(metasets):
        return None

    # This extra str(Marker()) call helps simplify the expression.
    return str(packaging.markers.Marker(" or ".join(
        "({0})".format(s) if " and " in s else s
        for s in dedup_markers(str(metaset) for metaset in metasets)
    )))


def set_metadata(candidates, traces, dependencies, pythons):
    """Add "metadata" to candidates based on the dependency tree.

    Metadata for a candidate includes markers and a specifier for Python
    version requirements.

    :param candidates: A key-candidate mapping. Candidates in the mapping will
        have their markers set.
    :param traces: A graph trace (produced by `traces.trace_graph`) providing
        information about dependency relationships between candidates.
    :param dependencies: A key-collection mapping containing what dependencies
        each candidate in `candidates` requested.
    :param pythons: A key-str mapping containing Requires-Python information
        of each candidate.

    Keys in mappings and entries in the trace are identifiers of a package, as
    implemented by the `identify` method of the resolver's provider.

    The candidates are modified in-place.
    """
    metasets_mapping = _calculate_metasets_mapping(
        dependencies, pythons, copy.deepcopy(traces),
    )
    for key, candidate in candidates.items():
        candidate.markers = _format_metasets(metasets_mapping[key])
