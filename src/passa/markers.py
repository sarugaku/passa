import copy

from packaging.markers import Marker

from .utils import identify_requirment


def _strip_extra(elements):
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
        if i > 0:
            # If this is not the beginning of the expression, remove the
            # operator before it.
            del elements[i - 1]
        elif i < len(elements):
            # Otherwise remove the operator after it, if there is one. Note
            # that this is [i] because the array has been shifted.
            del elements[i]
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


def _add_markersets(specs, key, trace, all_markersets):
    markersets = set()
    for route in trace:
        parent = route[-1]
        try:
            parent_markersets = all_markersets[parent]
        except KeyError:    # Parent not calculated yet. Wait for it.
            return False
        r = specs[parent][key]
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


def calculate_markersets_mapping(specs, requirements, traces):
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
            ok = _add_markersets(specs, key, trace, all_markersets)
            if not ok:
                continue
            successful_keys.add(key)
        if not successful_keys:
            break   # No progress? Deadlocked. Give up.
        for key in successful_keys:
            del traces[key]

    return all_markersets


def set_markers(candidates, traces, requirements, dependencies):
    """Add markers to candidates based on the dependency tree.

    :param candidates: A key-candidate mapping. Candidates in the mapping will
        have their markers set.
    :param traces: A graph trace (produced by `traces.trace_graph`) providing
        information about dependency relationships between candidates.
    :param requirements: A collection of requirements that was originally
        provided to be resolved.
    :param dependencies: A key-collection mapping containing what dependencies
        each candidate in `candidates` requested.

    Keys in mappings and entries in the trace are identifiers of a package, as
    implemented by the `identify` method of the resolver's provider.

    The candidates are modified in-place.
    """
    markersets_mapping = calculate_markersets_mapping(
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
