# -*- coding=utf-8 -*-

from __future__ import absolute_import

import sys


class Typing(object):
    def __getattr__(self, key):
        return None


sys.modules[__name__] = Typing()
