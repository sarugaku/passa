# -*- coding=utf-8 -*-
from collections import defaultdict
from packaging.specifiers import SpecifierSet, Specifier
from packaging.markers import Variable, Op, Value, Marker
import operator
import vistir
import itertools
PYTHON_BOUNDARIES = {2: 7, 3: 9}

expr = {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.0'"}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.0.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.1'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.1.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.2'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.2.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.3'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.3.*'"}}, 'rhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'2.6'"}}, 'rhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'2.7'"}}


# From "(((python_version >= '2.7' and python_version < '2.8') or (python_version >= '3.4' and python_version < '3.5')) and python_version != '3.0' and python_version != '3.0.*' and python_version != '
#   1 3.1' and python_version != '3.1.*' and python_version != '3.2' and python_version != '3.2.*' and python_version != '3.3' and python_version != '3.3.*' and python_version >= '2.6' and python_version >= '2.7')
#      or (((python_version >= '2.7' and python_version < '2.8') or (python_version >= '3.4' and python_version < '3.5')) and python_version != '3.0.*' and python_version != '3.1.*' and python_version != '3.2.*' a
#     nd python_version != '3.3.*' and python_version >= '2.7')"


expr2 ={'op': 'or', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'or', 'lhs': {'op': 'and', 'lhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'2.7'"}, 'rhs': {'op': '<', 'lhs': 'python_version', 'rhs': "'2.8'"}}, 'rhs': {'op': 'and', 'lhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'3.4'"}, 'rhs': {'op': '<', 'lhs': 'python_version', 'rhs': "'3.5'"}}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.0'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.0.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.1'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.1.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.2'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.2.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.3'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.3.*'"}}, 'rhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'2.6'"}}, 'rhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'2.7'"}}, 'rhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'and', 'lhs': {'op': 'or', 'lhs': {'op': 'and', 'lhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'2.7'"}, 'rhs': {'op': '<', 'lhs': 'python_version', 'rhs': "'2.8'"}}, 'rhs': {'op': 'and', 'lhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'3.4'"}, 'rhs': {'op': '<', 'lhs': 'python_version', 'rhs': "'3.5'"}}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.0.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.1.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.2.*'"}}, 'rhs': {'op': '!=', 'lhs': 'python_version', 'rhs': "'3.3.*'"}}, 'rhs': {'op': '>=', 'lhs': 'python_version', 'rhs': "'2.7'"}}}


def format_specifier(s):
    s = Specifier(s)
    version = s._coerce_version(s.version)
    if s.operator in (">", "<="):
        # Prefer to always pick the operator for version n+1
        if version.release[1] < PYTHON_BOUNDARIES.get(version.release[0], 0):
            if s.operator == ">":
                new_op = ">="
            else:
                new_op = "<"
            new_version = version.release[1] + 1
            s = Specifier("{0}{1}".format(new_op, new_version))
    return s


def unnest_version(v):
    if not isinstance(v, dict):
        return v
    lhs = v.get("lhs", "")
    rhs = v.get("rhs")
    op = v.get("op", "")
    if op == "or":
        vals = [unnest_version(lhs), unnest_version(rhs)]
        return vals
    return_vals = []
    python_versions = defaultdict(set)
    if op:
        if isinstance(lhs, str):
            rhs = rhs.replace(".*", "") if rhs.endswith(".*'") else rhs
            rhs = rhs.replace("'", "")
            specifier = format_specifier("{0}{1}".format(op, rhs))
            python_versions[specifier.operator].add(specifier.version)
            return python_versions
        elif isinstance(lhs, dict):
            for side in (lhs, rhs):
                merged_python_versions = unnest_version(side)
                if isinstance(merged_python_versions, list):
                    for bool_expr_side in merged_python_versions:
                        accumulation_copy = python_versions.copy()
                        for python_version_op, python_version in bool_expr_side.items():
                            accumulation_copy[python_version_op] |= python_version
                        return_vals.append(accumulation_copy)
                else:
                    for python_version_op, python_version in merged_python_versions.items():
                        python_versions[python_version_op] |= python_version
                    return python_versions
    return return_vals


def group_by_version(versions):
    versions = sorted(map(lambda x: [int(y) for y in x], [v.split(".") for v in versions]))
    grouping = itertools.groupby(versions, key=operator.itemgetter(0))
    return grouping


if __name__ == "__main__":
    python_versions = unnest_version(expr2)
    print(python_versions)
    marker = Marker("python_version >= '2.4'")
    _markers = []
    for py_version in python_versions:
        markers = []
        for op, versions in py_version.items():
            if op == "!=":
                for _v, group in group_by_version(versions):
                    grp = sorted([v[1] for v in group])
                    # min_grp = min(grp)
                    # max_grp = max(grp)
                    # candidates = [i for i in grp if i <= max_grp and i >= min_grp]
                    # if len(candidates) == len(grp):
                    #     specifiers = [
                    #         str(Specifier("<{0}.{1}".format(_v, min_grp))),
                    #         str(Specifier(">{0}.{1}".format(_v, max_grp)))
                    #     ]
                    # else:
                    if markers and grp:
                        markers.append("and")
                    markers.append(Marker("python_version != '{0}'".format(
                        ",".join(
                                ["{0}.{1}".format(_v, patch) for patch in grp]
                            )
                        )
                    )._markers)
                # version_list.extend(specifiers)
            elif op in (">", ">=", "<", "<="):
                for _v, group in group_by_version(versions):
                    grp = sorted([v[1] for v in group])
                    if markers and grp:
                        markers.append("and")
                    if op.startswith(">"):
                        markers.append(Marker("python_version {0} '{1}.{2}'".format(op, _v, min(grp)))._markers)
                    else:
                        markers.append(Marker("python_version {0} '{1}.{2}'".format(op, _v, max(grp)))._markers)
            if markers and _markers:
                _markers.append("or")
                _markers.extend(markers)
        # version_list.append("{0}'{1}'".format(op, ",".join(sorted(list(versions,)))))
    if markers:
        marker._markers = markers
    else:
        marker = None
    print(marker)
    # version_list = " and ".join(["python_version{0}".format(v) for v in sorted(version_list)])
    print(markers)
