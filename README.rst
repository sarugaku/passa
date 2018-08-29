===================================
Passa: Toolset for Pipfile projects
===================================

.. image:: https://img.shields.io/pypi/v/passa.svg
    :target: https://pypi.org/project/passa

.. image:: https://img.shields.io/pypi/l/passa.svg
    :target: https://pypi.org/project/passa

.. image:: https://api.travis-ci.com/sarugaku/passa.svg?branch=master
    :target: https://travis-ci.com/sarugaku/passa

.. image:: https://img.shields.io/pypi/pyversions/passa.svg
    :target: https://pypi.org/project/passa

.. image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
    :target: https://saythanks.io/to/techalchemy

.. image:: https://readthedocs.org/projects/passa/badge/?version=master
    :target: http://passa.readthedocs.io/en/master/?badge=master
    :alt: Documentation Status


Installation
============

Install from PyPI_::

    $ pipenv install passa

Install from GitHub_::

    $ pipenv install -e git+https://github.com/sarugaku/passa.git#egg=passa


.. _PyPI: https://pypi.org/project/passa
.. _GitHub: https://github.com/sarugaku/passa


Summary
=======

Passa is a toolset for performing tasks in a Pipfile project, designed to be
used as a backing component of Pipenv_. It contains several components:

* A resolver designed for performing dependency resolution using a stateful
  look-forward algorithm to resolve dependencies (backed by ResolveLib_).
* Interface to interact with individual requirement specifications inside
  Pipfile and Pipfile.lock (backed by RequirementsLib_).
* A command line interface to invoke the above operations.

.. _Pipenv: https://github.com/pypa/pipenv
.. _ResolveLib: https://github.com/sarugaku/resolvelib
.. _RequirementsLib: https://github.com/sarugaku/requirementslib


`Read the documentation <https://passa.readthedocs.io/>`__.
