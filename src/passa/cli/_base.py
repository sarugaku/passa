# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import sys


class Command(object):
    """A CLI command.
    """
    def __init__(self, parse_arguments, parsed_main):
        self.parse_arguments = parse_arguments
        self.parsed_main = parsed_main

    def __call__(self, argv=None):
        options = self.parse_arguments(argv)
        result = self.parsed_main(options)
        if result is not None:
            sys.exit(result)
