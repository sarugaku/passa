# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import resolvelib

from .base import BaseReporter


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


class ResolutionReporter(resolvelib.BaseReporter):
    """Simple reporter that prints resolution information to stdout.
    """
    def starting(self):
        self._prev = None

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


class StdOutReporter(BaseReporter):
    """Stdout reporter for the whole process.
    """
    def __init__(self):
        self.for_resolver = ResolutionReporter()

    def starting_resolve(self, requirements):
        print_title(' User requirements ')
        for r in requirements:
            print_requirement(r)

    def starting_trace(self, state):
        self.state = state

    def ending_trace(self, traces):
        print_title(" STABLE PINS ")
        for k in sorted(self.state.mapping):
            print(self.state.mapping[k].as_line(include_hashes=False))
            paths = traces[k]
            for path in paths:
                if path == [None]:
                    print('    User requirement')
                    continue
                print('   ', end='')
                for v in reversed(path[1:]):
                    line = self.state.mapping[v].as_line(include_hashes=False)
                    print(' <=', line, end='')
                print()
        print()

    def starting_hash(self):
        print("Fetching hash")

    def starting_metadata(self):
        print("Populating metadata")

    def starting_lock(self):
        print("Locking")
