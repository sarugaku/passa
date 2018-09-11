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


Quickstart
==========

Passa distributions can be downloaded from Appveyor’s `artifacts page`, as a
ZIP file.

.. _`artifacts page`: https://ci.appveyor.com/project/sarugaku/passa/build/artifacts

Once downloaded, you can run ``passa.zip`` with the interpreter of the
environment you want to manage:

.. code-block:: none

    python passa.zip --help

Use Passa to generate Pipfile.lock from the Pipfile in the current directory:

.. code-block:: none

    python passa.zip lock

Add packages to the project:

.. code-block:: none

    python passa.zip add pytz requests tqdm

Remove packages from the project:

.. code-block:: none

    python passa.zip remove pytz

Generate requirements.txt for the current project:

.. code-block:: none

    python passa.zip freeze --target requirements.txt


Distribution Notes
==================

Passa is available on PyPI and installable with pip, but it is not recommended
for you to do so. Passa is designed to be run *inside* the Python environment,
and, if installed with pip, would contaminate the very environment it wants to
manage.

The ZIP distribution is self-sufficient, and use only the interpreter (and the
standard library) to run itself, avoiding the contamination.


Table of Contents
=================

.. toctree::
    :maxdepth: 1

    philo
    cli
