# -*- coding=utf-8 -*-

# Recommended cases to test:
# * "oslo.utils==1.4.0"
# * "requests" "urllib3<1.21.1"
# * "pylint==1.9" "pylint-quotes==0.1.9"
# * "aiogremlin" "pyyaml"
# * Pipfile from pypa/pipenv#1974 (need to modify a bit)
# * Pipfile from pypa/pipenv#2529-410209718

from .cli import main

if __name__ == "__main__":
    main()
