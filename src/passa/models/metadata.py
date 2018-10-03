# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import copy
import itertools

import packaging.markers
import packaging.specifiers
import vistir
import vistir.misc

from ..internals.markers import get_without_extra
from ..internals.specifiers import PySpecs


def dedup_markers(s):
    # TODO: Implement better logic.
    deduped = sorted(vistir.misc.dedup(s))
    return deduped


class MetaSet(object):
    """Representation of a "metadata set".

    This holds multiple metadata representaions. Each metadata representation
    includes a marker, and a specifier set of Python versions required.
    """
    def __init__(self):
        self.markerset = frozenset()
        self.pyspecset = PySpecs()

    def __repr__(self):
        return "MetaSet(markerset={0!r}, pyspecset={1!r})".format(
            ",".join(sorted(self.markerset)), str(self.pyspecset),
        )

    def __key(self):
        return (tuple(self.markerset), hash(self.pyspecset))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __len__(self):
        return len(self.markerset) + len(self.pyspecset)

    def __iter__(self):
        return itertools.chain(self.markerset, self.pyspecset)

    def __str__(self):
        pyspecs = PySpecs()
        markerset = set()
        for m in self.markerset:
            marker_specs = PySpecs.from_marker(packaging.markers.Marker(m))
            if marker_specs:
                pyspecs.add(marker_specs)
            else:
                markerset.add(m)
        if pyspecs:
            self.pyspecset.add(pyspecs)
            self.markerset = frozenset(markerset)
        return " and ".join(dedup_markers(itertools.chain(
            # Make sure to always use the same quotes so we can dedup properly.
            (
                "{0}".format(ms) if " or " in ms else ms
                for ms in (str(m).replace('"', "'") for m in self.markerset)
            ),
            (
                "{0}".format(str(spec)) for spec in self.pyspecset
            ),
        )))

    def __bool__(self):
        return bool(self.markerset or self.pyspecset)

    def __nonzero__(self):  # Python 2.
        return self.__bool__()

    def __or__(self, pair):
        marker, specset = pair
        markerset = set(self.markerset)
        specset = PySpecs(specset)
        if marker:
            marker_specs = PySpecs.from_marker(marker)
            if not marker_specs:
                markerset.add(str(marker))
            else:
                specset.add(marker_specs)
        metaset = MetaSet()
        metaset.markerset = frozenset(markerset)
        # TODO: Implement some logic to clean up dups like '3.0.*' and '3.0'.
        metaset.pyspecset = self.pyspecset | specset
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

    metasets = set()
    for parent, parent_metasets in all_parent_metasets:
        r = dependencies[parent][key]
        python = pythons[key]
        markers = None if r.editable else get_without_extra(r.markers)
        metaset = (
            markers,
            packaging.specifiers.SpecifierSet(python),
        )
        for parent_metaset in parent_metasets:
            child_metaset = parent_metaset | metaset
            metasets.add(child_metaset)
    return list(metasets)


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
            if metasets is None or len(metasets) == 0:
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
    _metasets = (dedup_markers(str(metaset) for metaset in metasets if metaset))
    metaset_string = " or ".join(meta for meta in list(_metasets))
    if not metaset_string:
        return metaset_string
    return str(packaging.markers.Marker(metaset_string))


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
