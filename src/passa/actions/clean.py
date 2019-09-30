# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals


def clean(project, default=True, dev=False, sync=True):
    from passa.models.synchronizers import Synchronizer
    from passa.operations.sync import clean

    syncer = Synchronizer(
        project, default=default, develop=dev, clean_unneeded=True, dry_run=not sync
    )

    success = clean(syncer)
    if not success:
        return 1

    if sync:
        print("Cleaned project at", project.root)
