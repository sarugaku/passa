# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import resolvelib
import yaspin

from .traces import trace_graph


def print_title(text):
    print('\n{:=^84}\n'.format(text))


def print_requirement(r, end='\n'):
    print('{:>40}'.format(r.as_line(include_hashes=False)), end=end)


def print_dependency(state, key):
    print_requirement(state.mapping[key], end='')
    parents = sorted(
        state.graph.iter_parents(key),
        key=lambda n: (-1, '') if n is None else (ord(n[0].lower()), n),
    )
    for i, p in enumerate(parents):
        if p is None:
            line = '(user)'
        else:
            line = state.mapping[p].as_line(include_hashes=False)
        if i == 0:
            padding = ' <= '
        else:
            padding = ' ' * 44
        print('{pad}{line}'.format(pad=padding, line=line))


class ResolutionStdOutReporter(resolvelib.BaseReporter):
    """Simple reporter that prints resolution information to stdout.
    """
    def ending_round(self, index, state):
        print_title(' Round {} '.format(index))
        mapping = state.mapping
        if self._prev is None:
            difference = set(mapping.keys())
            changed = set()
        else:
            difference = set(mapping.keys()) - set(self._prev.keys())
            changed = set(
                k for k, v in mapping.items()
                if k in self._prev and self._prev[k] != v
            )
        self._prev = mapping

        if difference:
            print('New pins: ')
            for k in difference:
                print_dependency(state, k)
        print()

        if changed:
            print('Changed pins:')
            for k in changed:
                print_dependency(state, k)
        print()

    def ending(self, state):
        print_title(" STABLE PINS ")
        path_lists = trace_graph(state.graph)
        for k in sorted(state.mapping):
            print(state.mapping[k].as_line(include_hashes=False))
            paths = path_lists[k]
            for path in paths:
                if path == [None]:
                    print('    User requirement')
                    continue
                print('   ', end='')
                for v in reversed(path[1:]):
                    line = state.mapping[v].as_line(include_hashes=False)
                    print(' <=', line, end='')
                print()
        print()


class ResolutionSpinnerReporter(resolvelib.BaseReporter):
    """Reporter that shows a spinner during resolution.
    """
    def __init__(self, spinner):
        super(ResolutionSpinnerReporter, self).__init__()
        self.spinner = spinner

    def adding_candidate(self, candidate):
        self.spinner.text = "Resolving {}".format(candidate.normalized_name)

    def replacing_candidate(self, current, replacement):
        self.spinner.text = replacement.normalized_name


class StdOutReporter(object):
    """Stdout reporter for the whole process.
    """
    def __init__(self):
        self.for_resolver = ResolutionStdOutReporter()

    def starting_resolve(self, requirements):
        self._prev = None
        print_title(' User requirements ')
        for r in requirements:
            print_requirement(r)

    def starting_trace(self):
        print("Tracing")

    def starting_hash(self):
        print("Fetching hash")

    def starting_metadata(self):
        print("Populating metadata")

    def starting_lock(self):
        print("Locking")

    def ending(self):
        pass


class SpinnerReporter(object):
    """Spinner reporter for the whole process.
    """
    def __init__(self):
        self.spinner = yaspin.yaspin()
        self.for_resolver = ResolutionSpinnerReporter(self.spinner)

    def starting_resolve(self, requirements):
        self.spinner.start()
        self.spinner.text = "Resolving"

    def starting_trace(self):
        self.spinner.text = "Tracing"

    def starting_hash(self):
        self.spinner.text = "Fetching hash"

    def starting_metadata(self):
        self.spinner.text = "Populating metadata"

    def starting_lock(self):
        self.spinner.text = "Locking"

    def ending(self):
        self.spinner.stop()
