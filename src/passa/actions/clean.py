# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals


def clean(project, default=True, dev=False, sync=True):
    from passa.models.synchronizers import Cleaner
    from passa.operations.sync import clean

    cleaner = Cleaner(project, default=default, develop=dev, sync=sync)

    success = clean(cleaner)
    if not success:
        return 1

    if sync:
        print("Cleaned project at", project.root)
