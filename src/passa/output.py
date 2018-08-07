# -*- coding=utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from resolvelib import BaseReporter


def _key_sort(name):
    if name is None:
        return (-1, '')
    return (ord(name[0].lower()), name)


def _print_title(text):
    print('\n{:=^84}\n'.format(text))


def _print_requirement(r, end='\n'):
    print('{:>40}'.format(r.as_line()), end=end)


def _print_dependency(state, key):
    _print_requirement(state.mapping[key], end='')
    parents = sorted(state.graph.iter_parents(key), key=_key_sort)
    for i, p in enumerate(parents):
        if p is None:
            line = '(user)'
        else:
            line = state.mapping[p].as_line()
        if i == 0:
            padding = ' <= '
        else:
            padding = ' ' * 44
        print('{pad}{line}'.format(pad=padding, line=line))


class StdOutReporter(BaseReporter):
    """Simple reporter that prints things to stdout.
    """
    def starting(self):
        self._prev = None

    def ending_round(self, index, state):
        _print_title(' Round {} '.format(index))
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
                _print_dependency(state, k)
        print()

        if changed:
            print('Changed pins:')
            for k in changed:
                _print_dependency(state, k)
        print()
