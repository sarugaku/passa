# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import resolvelib


class BaseReporter(object):
    """Reporter for the whole process.

    This reporter only defines the interface, but does nothing.
    """
    def __init__(self):
        self.for_resolver = resolvelib.BaseReporter()

    def starting_resolve(self, requirements):
        pass

    def starting_trace(self, state):
        pass

    def ending_trace(self, traces):
        pass

    def starting_hash(self):
        pass

    def starting_metadata(self):
        pass

    def starting_lock(self):
        pass

    def ending(self):
        pass
