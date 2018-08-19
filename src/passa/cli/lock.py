# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from resolvelib import NoVersionsAvailable, ResolutionImpossible

from passa.reporters import print_requirement


def lock(project, force=False):
    success = updated = False
    try:
        updated = project.lock(force=force)
    except NoVersionsAvailable as e:
        print("\nCANNOT RESOLVE. NO CANDIDATES FOUND FOR:")
        print("{:>40}".format(e.requirement.as_line(include_hashes=False)))
        if e.parent:
            line = e.parent.as_line(include_hashes=False)
            print("{:>41}".format("(from {})".format(line)))
        else:
            print("{:>41}".format("(user)"))
    except ResolutionImpossible as e:
        print("\nCANNOT RESOLVE.\nOFFENDING REQUIREMENTS:")
        for r in e.requirements:
            print_requirement(r)
    else:
        success = True
    return success, updated
