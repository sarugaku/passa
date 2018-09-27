# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

from packaging.markers import Marker
from .specifiers import PySpecs, gen_marker
import six
import distlib.markers

six.add_move(six.MovedAttribute("Mapping", "collections", "collections.abc"))
from six.moves import Mapping, reduce

try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache


def _ensure_marker(marker):
    if not isinstance(marker, Marker):
        return Marker(str(marker))
    return marker


def _strip_extra(elements):
    """Remove the "extra == ..." operands from the list."""

    return _strip_marker_elem("extra", elements)


def _strip_pyversion(elements):
    return _strip_marker_elem("python_version", elements)


def _strip_marker_elem(elem_name, elements):
    """Remove the supplied element from the marker.

    This is not a comprehensive implementation, but relies on an important
    characteristic of metadata generation: The element's operand is always
    associated with an "and" operator. This means that we can simply remove the
    operand and the "and" operator associated with it.
    """

    extra_indexes = []
    preceding_operators = ["and"] if elem_name == "extra" else ["and", "or"]
    for i, element in enumerate(elements):
        if isinstance(element, list):
            cancelled = _strip_marker_elem(elem_name, element)
            if cancelled:
                extra_indexes.append(i)
        elif isinstance(element, tuple) and element[0].value == elem_name:
            extra_indexes.append(i)
    for i in reversed(extra_indexes):
        del elements[i]
        if i > 0 and elements[i - 1] in preceding_operators:
            # Remove the "and" before it.
            del elements[i - 1]
        elif elements:
            # This shouldn't ever happen, but is included for completeness.
            # If there is not an "and" before this element, try to remove the
            # operator after it.
            del elements[0]
    return (not elements)


def _get_stripped_marker(marker, strip_func):
    """Build a new marker which is cleaned according to `strip_func`"""

    if not marker:
        return None
    marker = _ensure_marker(marker)
    elements = marker._markers
    strip_func(elements)
    if elements:
        return marker
    return None


def get_without_extra(marker):
    """Build a new marker without the `extra == ...` part.

    The implementation relies very deep into packaging's internals, but I don't
    have a better way now (except implementing the whole thing myself).

    This could return `None` if the `extra == ...` part is the only one in the
    input marker.
    """

    return _get_stripped_marker(marker, _strip_extra)


def get_without_pyversion(marker):
    """Built a new marker without the `python_version` part.

    This could return `None` if the `python_version` section is the only section in the
    marker.
    """

    return _get_stripped_marker(marker, _strip_pyversion)


def _markers_collect_extras(markers, collection):
    # Optimization: the marker element is usually appended at the end.
    for el in reversed(markers):
        if (isinstance(el, tuple) and
                el[0].value == "extra" and
                el[1].value == "=="):
            collection.add(el[2].value)
        elif isinstance(el, list):
            _markers_collect_extras(el, collection)


def _markers_collect_pyversions(markers, collection):
    local_collection = []
    marker_format_str = "{0}"
    for i, el in enumerate(reversed(markers)):
        if (isinstance(el, tuple) and
                el[0].value == "python_version"):
            new_marker = str(gen_marker(el))
            local_collection.append(marker_format_str.format(new_marker))
        elif isinstance(el, six.string_types):
            local_collection.append(el)
        elif isinstance(el, list):
            _markers_collect_pyversions(el, local_collection)
    if local_collection:
        local_collection = "{0}".format(" ".join(local_collection))
        collection.append(local_collection)


@lru_cache(maxsize=128)
def get_contained_extras(marker):
    """Collect "extra == ..." operands from a marker.

    Returns a list of str. Each str is a speficied extra in this marker.
    """
    if not marker:
        return set()
    extras = set()
    marker = _ensure_marker(marker)
    _markers_collect_extras(marker._markers, extras)
    return extras


def get_contained_pyversions(marker):
    """Collect all `python_version` operands from a marker.

    Returns a set of :class:`~passa.internals.specifiers.PySpecs` instances.
    """

    collection = []
    if not marker:
        return set()
    marker = _ensure_marker(marker)
    # Collect the (Variable, Op, Value) tuples and string joiners from the marker
    _markers_collect_pyversions(marker._markers, collection)
    marker_str = " ".join(collection)
    if not marker_str:
        return set()
    # Use the distlib dictionary parser to create a dictionary 'trie' which is a bit
    # easier to reason about
    marker_dict = distlib.markers.parse_marker(marker_str)[0]
    version_set = set()
    pyversions = parse_marker_dict(marker_dict)
    if isinstance(pyversions, set):
        version_set.update(pyversions)
    else:
        version_set.add(pyversions)
    # Each distinct element in the set was separated by an "and" operator in the marker
    # So we will need to reduce them with an intersection here rather than a union
    # in order to find the boundaries
    versions = reduce(lambda x, y: x & y, version_set)
    if not versions:
        return PySpecs()
    return versions


def _markers_contains_extra(markers):
    # Optimization: the marker element is usually appended at the end.
    return _markers_contains_key(markers, "extra")


def _markers_contains_pyversion(markers):
    return _markers_contains_key(markers, "python_version")


def _markers_contains_key(markers, key):
    for element in reversed(markers):
        if isinstance(element, tuple) and element[0].value == key:
            return True
        elif isinstance(element, list):
            if _markers_contains_key(element, key):
                return True
    return False


@lru_cache(maxsize=128)
def contains_extra(marker):
    """Check whehter a marker contains an "extra == ..." operand.
    """
    if not marker:
        return False
    marker = _ensure_marker(marker)
    return _markers_contains_extra(marker._markers)


@lru_cache(maxsize=128)
def contains_pyversion(marker):
    """Check whether a marker contains a python_version operand.
    """

    if not marker:
        return False
    marker = _ensure_marker(marker)
    return _markers_contains_pyversion(marker._markers)


def parse_marker_dict(marker_dict):
    op = marker_dict["op"]
    lhs = marker_dict["lhs"]
    rhs = marker_dict["rhs"]
    # This is where the spec sets for each side land if we have an "or" operator
    sides = set()
    # And if we hit the end of the parse tree we use this format string to make a marker
    format_string = "{lhs} {op} {rhs}"
    # Essentially we will iterate over each side of the parsed marker if either one is
    # A mapping instance (i.e. a dictionary) and recursively parse and reduce the specset
    # Union the "and" specs, intersect the "or"s to find the most appropriate range
    if any(issubclass(type(side), Mapping) for side in (lhs, rhs)):
        for side in (lhs, rhs):
            specs = PySpecs()
            if issubclass(type(side), Mapping):
                specs.add(parse_marker_dict(side))
            else:
                # This is the easiest way to go from a string to a PySpec instance
                specs.add(PySpecs.from_marker(Marker(side)))
            sides.add(specs)
        if op == "and":
            # When we are "and"-ing things together, it probably makes the most sense
            # to reduce them here into a single PySpec instance
            if not sides:
                sides = [lhs, rhs]
            sides = reduce(lambda x, y: x | y, sides)
            return PySpecs.from_marker(Marker(str(sides)))
        # Actually when we "or" things as well we can also just turn them into a reduced
        # set using this logic now
        return reduce(lambda x, y: x & y, sides)
    else:
        # At the tip of the tree we are dealing with strings all around and they just need
        # to be smashed together
        return PySpecs.from_marker(Marker(format_string.format(**marker_dict)))
