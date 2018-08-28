===================================
Passa: Toolset for Pipfile projects
===================================

Passa is a toolset for performing tasks in a Pipfile project. It contains
several components:

* A resolver designed for performing dependency resolution using a stateful
  look-forward algorithm to resolve dependencies (backed by ResolveLib_).
* Interface to interact with individual requirement specifications inside
  Pipfile and Pipfile.lock (backed by RequirementsLib_).
* A command line interface to invoke the above operations.

.. _ResolveLib: https://github.com/sarugaku/resolvelib
.. _RequirementsLib: https://github.com/sarugaku/requirementslib


Contents
========

.. toctree::
   :maxdepth: 2
