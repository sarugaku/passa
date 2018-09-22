# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import collections
import itertools
import operator

from cached_property import cached_property
from packaging.markers import Marker
from packaging.specifiers import Specifier, SpecifierSet

from vistir.misc import dedup


try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache


@lru_cache(maxsize=128)
def _tuplize_version(version):
    return tuple(int(x) for x in filter(lambda i: i != "*", version.split(".")))


@lru_cache(maxsize=128)
def _format_version(version):
    return ".".join(str(i) for i in version)


# Prefer [x,y) ranges.
REPLACE_RANGES = {">": ">=", "<=": "<"}


@lru_cache(maxsize=128)
def _format_pyspec(specifier):
    if isinstance(specifier, str):
        if not any(op in specifier for op in Specifier._operators.keys()):
            specifier = "=={0}".format(specifier)
        specifier = Specifier(specifier)
    version = specifier.version.replace(".*", "")
    if ".*" in specifier.version:
        specifier = Specifier("{0}{1}".format(specifier.operator, version))
    try:
        op = REPLACE_RANGES[specifier.operator]
    except KeyError:
        return specifier
    curr_tuple = _tuplize_version(version)
    try:
        next_tuple = (curr_tuple[0], curr_tuple[1] + 1)
    except IndexError:
        next_tuple = (curr_tuple[0], 1)
    specifier = Specifier("{0}{1}".format(op, _format_version(next_tuple)))
    return specifier


@lru_cache(maxsize=128)
def _get_specs(specset):
    if specset is None:
        return
    if isinstance(specset, Specifier):
        specset = str(specset)
    if isinstance(specset, str):
        specset = SpecifierSet(specset.replace(".*", ""))
    result = []
    for spec in set(specset):
        result.append((spec.operator, _tuplize_version(spec.version)))
    return result


@lru_cache(maxsize=128)
def _group_by_op(specs):
    specs = [_get_specs(x) for x in list(specs)]
    flattened = [(op, version) for spec in specs for op, version in spec]
    specs = sorted(flattened, key=operator.itemgetter(1))
    grouping = itertools.groupby(specs, key=operator.itemgetter(0))
    return grouping


@lru_cache(maxsize=128)
def cleanup_pyspecs(specs, joiner="or"):
    specs = {_format_pyspec(spec) for spec in specs}
    # for != operator we want to group by version
    # if all are consecutive, join as a list
    results = set()
    for op, versions in _group_by_op(tuple(specs)):
        versions = [version[1] for version in versions]
        versions = sorted(dedup(versions))
        # if we are doing an or operation, we need to use the min for >=
        # this way OR(>=2.6, >=2.7, >=3.6) picks >=2.6
        # if we do an AND operation we need to use MAX to be more selective
        if op in (">", ">="):
            if joiner == "or":
                results.add((op, _format_version(min(versions))))
            else:
                results.add((op, _format_version(max(versions))))
        # we use inverse logic here so we will take the max value if we are
        # using OR but the min value if we are using AND
        elif op in ("<=", "<"):
            if joiner == "or":
                results.add((op, _format_version(max(versions))))
            else:
                results.add((op, _format_version(min(versions))))
        # leave these the same no matter what operator we use
        elif op in ("!=", "==", "~="):
            version_list = sorted(
                "{0}".format(_format_version(version))
                for version in versions
            )
            version = ", ".join(version_list)
            if len(version_list) == 1:
                results.add((op, version))
            elif op == "!=":
                results.add(("not in", version))
            elif op == "==":
                results.add(("in", version))
            else:
                specifier = SpecifierSet(",".join(sorted(
                    "{0}".format(op, v) for v in version_list
                )))._specs
                for s in specifier:
                    results &= (specifier._spec[0], specifier._spec[1])
        else:
            if len(version) == 1:
                results.add((op, version))
            else:
                specifier = SpecifierSet("{0}".format(version))._specs
                for s in specifier:
                    results |= (specifier._spec[0], specifier._spec[1])
    return results


@lru_cache(maxsize=128)
def pyspec_from_markers(marker):
    if marker._markers[0][0] != 'python_version':
        return
    op = marker._markers[0][1].value
    version = marker._markers[0][2].value
    specset = set()
    if op == "in":
        specset.update(
            Specifier("=={0}".format(v.strip()))
            for v in version.split(",")
        )
    elif op == "not in":
        specset.update(
            Specifier("!={0}".format(v.strip()))
            for v in version.split(",")
        )
    else:
        specset.add(Specifier("".join([op, version])))
    if specset:
        return specset
    return None


class PySpecs(collections.Set):
    def __init__(self, specs=None):
        if not specs:
            specs = SpecifierSet()
        self.specifierset = specs
        self.previous_specifierset = None
        self.cleaned_tuples = set()
        self.markers = None
        self.clean()

    def __key(self):
        return tuple(sorted(self.specifierset, key=operator.attrgetter("_spec")))

    def __contains__(self, other):
        # The current specifierset fully has every value in the supplied specifierset
        if not other.as_set - self.as_set:
            return True
        return False

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    def __repr__(self):
        return u"PySpecs({0!r})".format(str(self.specifierset))

    def __len__(self):
        return len(self.cleaned_tuples)

    def __iter__(self):
        for version in self.as_string_set:
            yield version
        return

    def clean(self):
        if len(set(self.specifierset)) == 1:
            spec = next(iter(spec for spec in self.specifierset), None)
            if spec:
                self.cleaned_tuples.add((spec.operator, spec.version))
        else:
            self.cleaned_tuples = cleanup_pyspecs(self.specifierset)
            self.specifierset = self.as_specset

    def add(self, other):
        new_pyspec = PySpecs(self.specifierset)
        new_pyspec.specifierset &= other.specifierset
        return new_pyspec

    @cached_property
    @lru_cache(maxsize=128)
    def as_specset(self):
        specs = set()
        for spec in self.cleaned_tuples:
            op, value = spec
            if op in ('in', 'not in'):
                new_op = '!=' if op == 'not in' else '=='
                for val in value.split(","):
                    specs.add(Specifier("{0}{1}".format(new_op, val)))
            else:
                specs.add(Specifier("{0}{1}".format(op, value)))
        specifierset = SpecifierSet()
        specifierset._specs = frozenset(specs)
        return specifierset

    @cached_property
    @lru_cache(maxsize=128)
    def as_set(self):
        return set(self.specifierset)

    @cached_property
    @lru_cache(maxsize=128)
    def as_string_set(self):
        returnval = set()
        if len(self.cleaned_tuples) == 1:
            val = next(iter(spec for spec in self.cleaned_tuples), None)
            if val:
                returnval.add("python_version {0[0]} '{0[1]}'".format(val))
            return returnval
        return set(
            "python_version {0[0]} '{0[1]}'".format(s)
            for s in sorted(self.cleaned_tuples)
        )

    @cached_property
    @lru_cache(maxsize=128)
    def marker_set(self):
        markerset = {Marker(spec) for spec in self.as_string_set}
        return markerset

    @cached_property
    @lru_cache(maxsize=128)
    def marker_string(self):
        marker_string = " and ".join(sorted(str(m) for m in self.as_string_set))
        if not marker_string:
            return ""
        return marker_string

    @cached_property
    @lru_cache(maxsize=128)
    def as_markers(self):
        print("generating marker using string: %s" % self.marker_string)
        if not self.marker_string:
            return ""
        marker = Marker(self.marker_string)
        return marker

    @lru_cache(maxsize=128)
    def __str__(self):
        string_repr = u"{0}".format(str(self.marker_string))
        print("converting to string: %s" % string_repr)
        return string_repr

    def __bool__(self):
        return bool(self.specifierset)

    def __nonzero__(self):  # Python 2.
        return self.__bool__()

    @lru_cache(maxsize=128)
    def __or__(self, specset):
        if not isinstance(specset, PySpecs):
            specset = PySpecs(specset)
        if str(self) == str(specset):
            return self
        combined_set = self.as_set | specset.as_set
        new_specset = SpecifierSet()
        new_specset._specs = frozenset(combined_set)
        new_pyspec = PySpecs(new_specset)
        return new_pyspec

    @classmethod
    @lru_cache(maxsize=128)
    def from_marker(cls, marker):
        if marker._markers[0][0] != 'python_version':
            return
        op = marker._markers[0][1].value
        version = marker._markers[0][2].value
        specset = set()
        if op == "in":
            specset.update(
                Specifier("=={0}".format(v.strip()))
                for v in version.split(",")
            )
        elif op == "not in":
            specset.update(
                Specifier("!={0}".format(v.strip()))
                for v in version.split(",")
            )
        else:
            specset.add(Specifier("".join([op, version])))
        if specset:
            specifierset = SpecifierSet()
            specifierset._specs = frozenset(specset)
            newset = cls(specifierset)
            return newset
        return None
