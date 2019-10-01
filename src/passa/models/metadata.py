# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import copy
import operator

import packaging.markers
import packaging.specifiers
import vistir
import vistir.misc

from six.moves import reduce

from ..internals.markers import (
    get_without_extra, get_without_pyversion, get_contained_pyversions, Marker
)
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
        self.marker = Marker()
        self.pyspecset = PySpecs()

    def __repr__(self):
        return "MetaSet(marker={0!r}, pyspecset={1!r})".format(
            str(self.marker), str(self.pyspecset),
        )

    def __key(self):
        return (self.marker, hash(tuple(self.pyspecset)))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __lt__(self, other):
        return operator.lt(self.__key(), other.__key())

    def __str__(self):
        marker = self.marker
        if self.pyspecset:
            marker = marker & self.pyspecset
        return str(marker)

    def __bool__(self):
        return bool(self.marker or self.pyspecset)

    def __nonzero__(self):  # Python 2.
        return self.__bool__()

    @classmethod
    def from_tuple(cls, pair):
        marker, specset = pair
        pyspecs = PySpecs(specset)
        new_marker = Marker()
        if marker:
            # Returns a PySpec instance or None
            marker_pyversions = get_contained_pyversions(marker)
            if marker_pyversions:
                pyspecs.add(marker_pyversions)
            # The remainder of the marker, if there is any
            cleaned_marker = get_without_pyversion(marker)
            if cleaned_marker:
                new_marker = new_marker & cleaned_marker
        metaset = cls()
        metaset.marker = marker
        metaset.pyspecset = pyspecs
        return metaset

    def __or__(self, other):
        if not isinstance(other, type(self)):
            other = self.from_tuple(other)
        metaset = MetaSet()
        marker = Marker()
        specset = PySpecs()
        for meta in (self, other):
            if meta.marker:
                marker = marker | meta.marker
            if meta.pyspecset:
                specset = specset | meta.pyspecset
        metaset.marker = marker
        metaset.pyspecset = specset
        return metaset

    def __and__(self, other):
        if not isinstance(other, type(self)):
            other = self.from_tuple(other)
        metaset = MetaSet()
        marker = Marker()
        specset = PySpecs()
        for meta in (self, other):
            if meta.marker:
                marker = marker & meta.marker
            if meta.pyspecset:
                specset = specset & meta.pyspecset
        metaset.marker = marker
        metaset.pyspecset = specset
        return metaset


def _build_metasets(dependencies, pythons, key, trace, all_metasets):
    all_parent_metasets = {}
    for route in trace:
        parent = route[-1]
        if parent in all_parent_metasets:
            continue
        try:
            parent_metasets = all_metasets[parent]
        except KeyError:    # Parent not calculated yet. Wait for it.
            return
        all_parent_metasets[parent] = parent_metasets

    metasets = set()
    for parent, parent_metasets in all_parent_metasets.items():
        r = dependencies[parent][key]
        python = pythons[key]
        markers = None if r.editable else get_without_extra(r.markers)
        metaset = (
            markers,
            packaging.specifiers.SpecifierSet(python),
        )
        for parent_metaset in parent_metasets:
            # Use 'and' to connect markers inherited from parent.
            child_metaset = parent_metaset & metaset
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

    metasets = dedup_markers(metaset for metaset in metasets if metaset)
    # If there is an unconditional route, this needs to be unconditional.
    if not metasets:
        return ""
    # Use 'or' to combine markers from different parent.
    combined_metaset = str(MetaSet() | reduce(lambda x, y: x | y, metasets))
    if not combined_metaset:
        return ""
    # This extra str(Marker()) call helps simplify the expression.
    metaset_string = str(packaging.markers.Marker(combined_metaset))
    return metaset_string


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
