# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals


def sync(syncer):
    print("Starting synchronization")
    installed, updated, skipped, cleaned = syncer.sync()
    if cleaned:
        print("Removed: {}".format(", ".join(sorted(cleaned))))
    if installed:
        print("Installed: {}".format(", ".join(sorted(installed))))
    if updated:
        print("Updated: {}".format(", ".join(sorted(updated))))
    if skipped:
        print("Skipped: {}".format(", ".join(sorted(skipped))))
    return True
