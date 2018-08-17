import copy

from packaging.markers import Marker

from .utils import identify_requirment


def _strip_extra(elements):
    """Remove the "extra == ..." operands from the list.

    This is not a comprehensive implementation, but relies on an important
    characteristic of metadata generation: The "extra == ..." operand is always
    associated with an "and" operator. This means that we can simply remove the
    operand and the "and" operator associated with it.
    """
    extra_indexes = []
    for i, element in enumerate(elements):
        if isinstance(element, list):
            cancelled = _strip_extra(element)
            if cancelled:
                extra_indexes.append(i)
        elif isinstance(element, tuple) and element[0].value == "extra":
            extra_indexes.append(i)
    for i in reversed(extra_indexes):
        del elements[i]
        if i > 0 and elements[i - 1] == "and":
            # Remove the "and" before it.
            del elements[i - 1]
        elif elements:
            # This shouldn't ever happen, but is included for completeness.
            # If there is not an "and" before this element, try to remove the
            # operator after it.
            del elements[0]
    return (not elements)


def get_without_extra(marker):
    """Build a new marker without the `extra == ...` part.

    The implementation relies very deep into packaging's internals, but I don't
    have a better way now (except implementing the whole thing myself).

    This could return `None` if the `extra == ...` part is the only one in the
    input marker.
    """
    if not marker:
        return None
    marker = Marker(str(marker))
    elements = marker._markers
    _strip_extra(elements)
    if elements:
        return marker
    return None


def _markerset(*markers):
    return frozenset(markers)


def _add_markersets(candidates, key, trace, all_markersets):
    markersets = set()
    for route in trace:
        parent = route[-1]
        try:
            parent_markersets = all_markersets[parent]
        except KeyError:    # Parent not calculated yet. Wait for it.
            return False
        r = candidates[parent][key]
        marker = get_without_extra(r.markers)
        if marker:
            markerset = _markerset(str(marker))
        else:
            markerset = _markerset()
        markersets.update({
            parent_markerset | markerset
            for parent_markerset in parent_markersets
        })
    try:
        current_markersets = all_markersets[key]
    except KeyError:
        all_markersets[key] = markersets
    else:
        all_markersets[key] = current_markersets | markersets
    return True


def _calculate_markersets_mapping(requirements, candidates, traces):
    all_markersets = {}

    # Populate markers from Pipfile.
    for r in requirements:
        if r.markers:
            markerset = _markerset(r.markers)
        else:
            markerset = _markerset()
        all_markersets[identify_requirment(r)] = {markerset}

    traces = copy.deepcopy(traces)
    del traces[None]
    while traces:
        successful_keys = set()
        for key, trace in traces.items():
            ok = _add_markersets(candidates, key, trace, all_markersets)
            if not ok:
                continue
            successful_keys.add(key)
        if not successful_keys:
            break   # No progress? Deadlocked. Give up.
        for key in successful_keys:
            del traces[key]

    return all_markersets


def set_markers(candidates, traces, requirements, dependencies, pythons):
    """Add markers to candidates based on the dependency tree.

    :param candidates: A key-candidate mapping. Candidates in the mapping will
        have their markers set.
    :param traces: A graph trace (produced by `traces.trace_graph`) providing
        information about dependency relationships between candidates.
    :param requirements: A collection of requirements that was originally
        provided to be resolved.
    :param dependencies: A key-collection mapping containing what dependencies
        each candidate in `candidates` requested.
    :param pythons: A key-str mapping containing Requires-Python information
        of each candidate.

    Keys in mappings and entries in the trace are identifiers of a package, as
    implemented by the `identify` method of the resolver's provider.

    The candidates are modified in-place.
    """
    markersets_mapping = _calculate_markersets_mapping(
        requirements, dependencies, traces,
    )
    for key, candidate in candidates.items():
        markersets = markersets_mapping[key]

        # If there is an unconditional route, this needs to be unconditional.
        if any(not s for s in markersets):
            candidate.markers = None
            continue

        # This extra str(Marker()) call helps simplify the expression.
        candidate.markers = str(Marker(" or ".join("({0})".format(
            " and ".join("({0})".format(marker) for marker in markerset)
        ) for markerset in markersets)))


def _markers_collect_extras(markers, collection):
    # Optimization: the marker element is usually appended at the end.
    for el in reversed(markers):
        if (isinstance(el, tuple) and
                el[0].value == "extra" and
                el[1].value == "=="):
            collection.add(el[2].value)
        elif isinstance(el, list):
            _markers_collect_extras(el, collection)


def get_contained_extras(marker):
    """Collect "extra == ..." operands from a marker.

    Returns a list of str. Each str is a speficied extra in this marker.
    """
    if not marker:
        return set()
    marker = Marker(str(marker))
    extras = set()
    _markers_collect_extras(marker._markers, extras)
    return extras


def _markers_contains_extra(markers):
    # Optimization: the marker element is usually appended at the end.
    for element in reversed(markers):
        if isinstance(element, tuple) and element[0].value == "extra":
            return True
        elif isinstance(element, list):
            if _markers_contains_extra(element):
                return True
    return False


def contains_extra(marker):
    """Check whehter a marker contains an "extra == ..." operand.
    """
    if not marker:
        return False
    marker = Marker(str(marker))
    return _markers_contains_extra(marker._markers)
