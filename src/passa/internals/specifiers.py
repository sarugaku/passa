# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import itertools
import operator

import six

from packaging.markers import Marker
from packaging.specifiers import Specifier, SpecifierSet
import packaging.version

from vistir.misc import dedup

six.add_move(six.MovedAttribute("Set", "collections", "collections.abc"))
from six.moves import Set


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
    if not next_tuple[1] <= PySpecs.MAX_VERSIONS[next_tuple[0]]:
        if (specifier.operator == "<"
                and next_tuple[1] - 1 <= PySpecs.MAX_VERSIONS[next_tuple[0]]):
            op = "<="
            next_tuple = (next_tuple[0], next_tuple[1] - 1)
        else:
            return specifier
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
        version = spec.version
        op = spec.operator
        if op in ("in", "not in"):
            versions = version.split(",")
            op = "==" if op == "in" else "!="
            for ver in versions:
                result.append((op, _tuplize_version(ver.strip())))
        else:
            result.append((spec.operator, _tuplize_version(spec.version)))
    return result


@lru_cache(maxsize=128)
def _group_by_op(specs):
    specs = [_get_specs(x) for x in list(specs)]
    flattened = [(op, version) for spec in specs for op, version in spec]
    specs = sorted(flattened)
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


def fix_version_tuple(version_tuple):
    op, version = version_tuple
    max_major = max(PySpecs.MAX_VERSIONS.keys())
    if version[0] > max_major:
        return (op, (max_major, PySpecs.MAX_VERSIONS[max_major]))
    max_allowed = PySpecs.MAX_VERSIONS[version[0]]
    if op == "<" and version[1] > max_allowed and version[1] - 1 <= max_allowed:
        op = "<="
        version = (version[0], version[1] - 1)
    return (op, version)


@lru_cache(maxsize=128)
def get_versions(specset, group_by_operator=True):
    specs = [_get_specs(x) for x in list(tuple(specset))]
    initial_sort_key = lambda k: (k[0], k[1])   # noqa
    initial_grouping_key = operator.itemgetter(0)
    if not group_by_operator:
        initial_grouping_key = operator.itemgetter(1)
        initial_sort_key = operator.itemgetter(1)
    version_tuples = sorted(
        set((op, version) for spec in specs for op, version in spec),
        key=initial_sort_key
    )
    version_tuples = [fix_version_tuple(t) for t in version_tuples]
    op_groups = [
        (grp, list(map(operator.itemgetter(1), keys)))
        for grp, keys in itertools.groupby(version_tuples, key=initial_grouping_key)
    ]
    versions = [
        (op, packaging.version.parse(".".join(str(v) for v in val)))
        for op, vals in op_groups for val in vals
    ]
    return versions


def gen_marker(mkr):
    m = Marker("python_version == '1'")
    m._markers.pop()
    m._markers.append(mkr)
    return m


class PySpecs(Set):

    MAX_VERSIONS = {
        2: 7,
        3: 9
    }

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
            self.cleaned_tuples = cleanup_pyspecs(self.specifierset, joiner="and")
            self.specifierset = self.as_specset

    def add(self, other):
        if not isinstance(other, self.__class__):
            if isinstance(other, SpecifierSet):
                other = PySpecs(other)
            else:
                raise TypeError("Cannot add type {0!r} to PySpecs".format(type(other)))
        new_specifierset = SpecifierSet()
        new_specifierset &= self.as_specset
        try:
            new_specifierset &= other.as_specset
        except AttributeError:
            pass
        new_pyspec = PySpecs(new_specifierset)
        self.specifierset = new_pyspec.specifierset
        self.cleaned_tuples = new_pyspec.cleaned_tuples

    @property
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

    @property
    @lru_cache(maxsize=128)
    def as_set(self):
        return set(self.specifierset)

    @property
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

    @property
    @lru_cache(maxsize=128)
    def marker_set(self):
        markerset = {Marker(spec) for spec in self.as_string_set}
        return markerset

    @property
    @lru_cache(maxsize=128)
    def marker_string(self):
        marker_string = " and ".join(sorted(str(m) for m in self.marker_set))
        if not marker_string:
            return ""
        return str(Marker(marker_string))

    @property
    @lru_cache(maxsize=128)
    def as_markers(self):
        if not self.marker_string:
            return ""
        marker = Marker(self.marker_string)
        return marker

    @lru_cache(maxsize=128)
    def __str__(self):
        string_repr = "{0}".format(str(self.marker_string))
        return string_repr

    def __bool__(self):
        return bool(self.specifierset)

    def __nonzero__(self):  # Python 2.
        return self.__bool__()

    def get_versions(self, group_by_operator=True):
        return get_versions(self.specifierset, group_by_operator=group_by_operator)

    def get_versions_in_specset(self):
        return set([v[1] for v in self.get_versions() if v[1] in self.specifierset])

    def get_version_excludes(self):
        return set([
            v[1] for v in self.get_versions()
            if v[0] == "!=" and v[1] not in self.specifierset
        ])

    def get_version_includes(self):
        return set([v for v in ALL_PYTHON_VERSIONS if v in self.specifierset])

    def get_specset_from_versions(self, versions, include=True):
        _specset = SpecifierSet()
        op = "==" if include else "!="
        specs = set([Specifier("{0}{1}".format(op, v)) for v in versions])
        _specset._specs = frozenset(specs)
        return _specset

    def group_specs(self, specs=None, handle_exclusions=True):
        if not specs:
            specs = self.get_versions(group_by_operator=handle_exclusions)
        else:
            specs = get_versions(specs, group_by_operator=handle_exclusions)
        pyversions = enumerate(specs)

        def get_version(v):
            return ALL_PYTHON_VERSIONS.index(v[1][1])

        excludes = set()
        ranges = set()

        # group the versions on their index from ALL_PYTHON_VERSIONS - their index here
        # consecutive elements will share a group, e.g.
        # ALL_PYTHON_VERSIONS.index(parse_version("2.7")) == 7, 3.0 == 8, 3.1 == 9
        # if 2.7 is element 1, (7 - 1) = 6, if 3.0 is element 2, (8 - 2) = 6
        # and they will share a group (i.e. they are consecutive)
        for k, grp in itertools.groupby(pyversions, lambda t: get_version(t) - t[0]):
            version_group = list(grp)
            op = next(iter(v[1][0] for v in version_group), None)
            _versions = [v[1][1] for v in version_group]
            if op == "!=":
                excludes.update(set(_versions))
            else:
                min_ = min(_versions)
                max_ = max(_versions)
                if len(_versions) == 1 or str(min_) == str(max_):
                    ranges.add((min_,))
                else:
                    ranges.add((min_, max_))
        # Now add the holes between ranges to excludes
        sorted_ranges = sorted(ranges, key=lambda x: x[0])
        for k in range(len(sorted_ranges) - 1):
            lower = ALL_PYTHON_VERSIONS.index(sorted_ranges[k][-1])
            upper = ALL_PYTHON_VERSIONS.index(sorted_ranges[k + 1][0])
            if lower < upper - 1:
                excludes.update({ALL_PYTHON_VERSIONS[i] for i in range(lower + 1, upper)})
        return ranges, excludes

    def create_specset_from_ranges(self, specset=None, ranges=None, excludes=None):
        """This method takes a specifier set and simplifies it down to some range sets.

        The goal is to consume a list of matching individual version specifiers in
        "==" notation (accompanied by a set of excluded versions, that is a set() of
        Version objects) and produce a SpecifierSet with a min and max range and the
        appropriate excludes (i.e. the simplified set).

        :param specset: A specifierset with the enumerated versions
        :param ranges: The ranges to use as inputs (or the specset will be generated from it)
        :param excludes: A set of Version objects to exclude in the specifierset
        :return: A specifierset with the desired ranges
        """

        group_args = {"handle_exclusions": False}
        if ranges and not specset and isinstance(ranges, SpecifierSet):
            group_args["specs"] = ranges
            ranges, _ = self.group_specs(**group_args)
        if specset:
            group_args["specs"] = specset
        if not ranges:
            ranges, _ = self.group_specs(**group_args)
        if not excludes:
            group_args["handle_exclusions"] = True
            _, excludes = self.group_specs(**group_args)
        spec_ranges = set()
        if len(ranges) == 1 and not isinstance(next(iter(ranges)), tuple):
            spec_ranges.add(Specifier("=={0}".format(str(next(iter(ranges[0]))))))
        else:
            min_version = min([r[0] for r in ranges])
            rhs_versions = [
                r[1] for r in ranges if isinstance(r, tuple) and len(r) > 1
            ]
            max_version = max(rhs_versions) if rhs_versions else None
            spec_ranges.add(Specifier(">={0}".format(str(min_version))))
            if max_version and max_version != ALL_PYTHON_VERSIONS[-1]:
                spec_ranges.add(Specifier("<={0}".format(str(max_version))))
        for exclude in excludes:
            spec_ranges.add(Specifier("!={0}".format(str(exclude))))
        new_specset = SpecifierSet()
        new_specset._specs = frozenset(spec_ranges)
        return new_specset

    @lru_cache(maxsize=128)
    def __or__(self, other):
        # Unintuitive perhaps, but this is for "x or y" and needs to handle the
        # widest possible range encapsulated by the two using the intersection
        if not isinstance(other, PySpecs):
            other = PySpecs(other)
        if self == other:
            return self
        new_specset = SpecifierSet()
        if not self.specifierset:
            intersection = other.get_version_includes()
        elif not other.specifierset:
            intersection = self.get_version_includes()
        else:
            # In order to do an "or" propertly we need to intersect the "good" versions
            intersection = self.get_version_includes() | other.get_version_includes()
        intersection_specset = self.get_specset_from_versions(intersection)
        # And then we need to union the "bad" versions
        excludes = self.get_version_excludes() & other.get_version_excludes()
        new_specset = self.create_specset_from_ranges(ranges=intersection_specset, excludes=excludes)
        return PySpecs(new_specset)

    @lru_cache(maxsize=128)
    def __and__(self, specset):
        if not isinstance(specset, PySpecs):
            specset = PySpecs(specset)
        if str(self) == str(specset):
            return self
        combined_set = self.specifierset & specset.specifierset
        # new_specset._specs = frozenset(combined_set)
        new_pyspec = PySpecs(combined_set)
        return new_pyspec

    @classmethod
    def from_marker(cls, marker):
        if not marker:
            return PySpecs()
        if len(marker._markers) > 1:
            specs = PySpecs()
            markers = sorted([
                el for el in marker._markers
                if isinstance(el, tuple)
            ], key=lambda x: x[2].value)
            for mkr in markers:
                specs.add(cls.from_marker(gen_marker(mkr)))
            return specs
        if marker._markers[0][0].value != 'python_version':
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
            versions = [v.strip() for v in version.split(",")]
            bad_versions = ["3.0", "3.1", "3.2", "3.3"]
            if len(versions) >= 2 and any(v in versions for v in bad_versions):
                versions = bad_versions
            specset.update(
                Specifier("!={0}".format(v.strip()))
                for v in sorted(bad_versions)
            )
        else:
            specset.add(Specifier("".join([op, version])))
        if specset:
            specifierset = SpecifierSet()
            specifierset._specs = frozenset(specset)
            newset = cls(specifierset)
            return newset
        return None


def get_all_python_versions():
    major_versions = list(PySpecs.MAX_VERSIONS.keys())
    versions = (
        "{0}.{1}".format(major, minor) for major in major_versions
        for minor in range(PySpecs.MAX_VERSIONS[major] + 1)
    )
    versions = (packaging.version.parse(v) for v in versions)
    return versions


ALL_PYTHON_VERSIONS = sorted(get_all_python_versions())
