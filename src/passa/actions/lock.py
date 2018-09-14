# -*- coding=utf-8 -*-


def lock(project=None):
    from passa.models.lockers import BasicLocker
    from passa.operations.lock import lock

    project = project
    locker = BasicLocker(project)
    success = lock(locker)
    if not success:
        return

    project._l.write()
    print("Written to project at", project.root)
