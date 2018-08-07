# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
__version__ = '0.0.0.dev0'


from . import cli
from .lockfile import get_hashes
from .resolver import RequirementsLibProvider
