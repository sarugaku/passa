# -*- coding=utf-8 -*-

import atexit
import os
import shutil
import sys
import sysconfig


CURR_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_NAME = os.path.join(CURR_DIR, 'lib.zip')


def get_site_packages():
    prefixes = {sys.prefix, sysconfig.get_config_var('prefix')}
    try:
        prefixes.add(sys.real_prefix)
    except AttributeError:
        pass
    form = sysconfig.get_path('purelib', expand=False)
    py_version_short = '{0[0]}.{0[1]}'.format(sys.version_info)
    return {
        form.format(base=prefix, py_version_short=py_version_short)
        for prefix in prefixes
    }


def insert_before_site_packages(*paths):
    site_packages =  get_site_packages()
    index = None
    for i, path in enumerate(sys.path):
        if path in site_packages:
            index = i
            break
    if index is None:
        sys.path += list(paths)
    else:
        sys.path = sys.path[:index] + list(paths) + sys.path[index:]


def run_passa():
    from passa.cli import main
    main()


def main():
    insert_before_site_packages(ZIP_NAME)
    run_passa()


if __name__ == '__main__':
    main()
