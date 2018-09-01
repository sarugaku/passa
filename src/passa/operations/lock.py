# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from resolvelib import NoVersionsAvailable, ResolutionImpossible

from passa import reporters


def lock(locker):
    success = False
    try:
        locker.lock()
    except (NoVersionsAvailable, ResolutionImpossible) as e:
        reporters.report("lock-failed", {"exception": e})
    else:
        success = True
    return success
