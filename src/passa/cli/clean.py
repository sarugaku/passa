# -*- coding=utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from ..actions.clean import clean
from ._base import BaseCommand
from .options import dev, no_default, sync_group


class Command(BaseCommand):

    name = "clean"
    description = "Uninstall unlisted packages from the environment."
    arguments = [dev, no_default, sync_group]

    def run(self, options):
        return clean(
            project=options.project, default=options.default, dev=options.dev,
            sync=options.sync
        )


if __name__ == "__main__":
    Command.run_parser()
