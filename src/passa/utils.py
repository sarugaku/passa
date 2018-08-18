# -*- coding=utf-8 -*-
from __future__ import absolute_import, unicode_literals

import atexit
import functools

from vistir.compat import TemporaryDirectory
from vistir.path import mkdir_p


def identify_requirment(r):
    """Produce an identifier for a requirement to use in the resolver.

    Note that we are treating the same package with different extras as
    distinct. This allows semantics like "I only want this extra in
    development, not production".

    This also makes the resolver's implementation much simpler, with the minor
    costs of possibly needing a few extra resolution steps if we happen to have
    the same package apprearing multiple times.
    """
    return "{0}{1}".format(r.normalized_name, r.extras_as_pip)


def ensure_mkdir_p(mode=0o777):
    """Decorator to ensure `mkdir_p` is called to the function's return value.
    """
    def decorator(f):

        @functools.wraps(f)
        def decorated(*args, **kwargs):
            path = f(*args, **kwargs)
            mkdir_p(path, mode=mode)
            return path

        return decorated

    return decorator


def cheesy_temporary_directory(*args, **kwargs):
    """Uses a python 2/3 compatible TemporaryDirectory from `vistir`.

    Registers a handler to cleanup after itself using a backported version of 
    `weakref.finalize` if necessary.
    """
    temp_src = TemporaryDirectory(*args, **kwargs)

    atexit.register(temp_src.cleanup)
    return temp_src.name


def get_pinned_version(ireq):
    """Get the pinned version of an InstallRequirement.

    An InstallRequirement is considered pinned if:

    - Is not editable
    - It has exactly one specifier
    - That specifier is "=="
    - The version does not contain a wildcard

    Examples:
        django==1.8   # pinned
        django>1.8    # NOT pinned
        django~=1.8   # NOT pinned
        django==1.*   # NOT pinned

    Raises `TypeError` if the input is not a valid InstallRequirement, or
    `ValueError` if the InstallRequirement is not pinned.
    """
    try:
        specifier = ireq.specifier
    except AttributeError:
        raise TypeError("Expected InstallRequirement, not {}".format(
            type(ireq).__name__,
        ))

    if ireq.editable:
        raise ValueError("InstallRequirement is editable")
    if not specifier:
        raise ValueError("InstallRequirement has no version specification")
    if len(specifier._specs) != 1:
        raise ValueError("InstallRequirement has multiple specifications")

    op, version = next(iter(specifier._specs))._spec
    if op not in ('==', '===') or version.endswith('.*'):
        raise ValueError("InstallRequirement not pinned (is {0!r})".format(
            op + version,
        ))

    return version


def is_pinned(ireq):
    """Returns whether an InstallRequirement is a "pinned" requirement.

    An InstallRequirement is considered pinned if:

    - Is not editable
    - It has exactly one specifier
    - That specifier is "=="
    - The version does not contain a wildcard

    Examples:
        django==1.8   # pinned
        django>1.8    # NOT pinned
        django~=1.8   # NOT pinned
        django==1.*   # NOT pinned
    """
    try:
        get_pinned_version(ireq)
    except (TypeError, ValueError):
        return False
    return True
