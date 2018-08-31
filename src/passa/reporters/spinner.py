# -*- coding=utf-8 -*-

from __future__ import absolute_import, unicode_literals

import resolvelib
import yaspin

from .base import BaseReporter


class ResolutionReporter(resolvelib.BaseReporter):
    """Reporter that shows a spinner during resolution.
    """
    def __init__(self, spinner):
        super(ResolutionReporter, self).__init__()
        self.spinner = spinner

    def adding_candidate(self, candidate):
        self.spinner.text = "Resolving {}".format(candidate.normalized_name)

    def replacing_candidate(self, current, replacement):
        self.spinner.text = replacement.normalized_name


class SpinnerReporter(BaseReporter):
    """Spinner reporter for the whole process.
    """
    def __init__(self):
        self.spinner = yaspin.yaspin()
        self.for_resolver = ResolutionReporter(self.spinner)

    def starting_resolve(self, requirements):
        self.spinner.start()
        self.spinner.text = "Resolving"

    def starting_trace(self, state):
        self.spinner.text = "Tracing"

    def starting_hash(self):
        self.spinner.text = "Fetching hash"

    def starting_metadata(self):
        self.spinner.text = "Populating metadata"

    def starting_lock(self):
        self.spinner.text = "Locking"

    def ending(self):
        self.spinner.stop()
