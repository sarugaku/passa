# -*- coding=utf-8 -*-
from __future__ import unicode_literals, absolute_import


def clean(project, dev=False):
    from passa.models.synchronizers import Cleaner
    from passa.operations.sync import clean

    cleaner = Cleaner(project, default=True, develop=dev)

    success = clean(cleaner)
    if not success:
        return 1

    print("Cleaned project at", project.root)
