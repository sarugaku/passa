0.3.0 (2018-08-30)
==================

Features
--------

- Improves consolidation logic to merge ``Requires-Python`` into ``python_version`` markers. This greatly reduced clutterness in Pipfile.lock.  `#14 <https://github.com/sarugaku/passa/issues/14>`_
  
- Try to suppress installation errors unless ``PASSA_NO_SUPPRESS_EXCEPTIONS`` is set. This matches the behaviour of locking.  `#17 <https://github.com/sarugaku/passa/issues/17>`_
  
- ``sync`` is redisigned to be intergrated into ``add``, ``remove``, and ``upgrade``. Various ``clean`` operations are added to purge unneeded packages from the environment. ``install`` is added as a combination of ``lock`` and ``sync``.  `#20 <https://github.com/sarugaku/passa/issues/20>`_
  

Bug Fixes
---------

- Fix entry point declaration in package so the ``passa`` command can work.  `#18 <https://github.com/sarugaku/passa/issues/18>`_


0.2.0 (2018-08-29)
==================

Features
--------

- Add ``sync`` command to synchronize the running environment with Pipfile.lock.


Bug Fixes
---------

- Fix CLI invocation on Python 2.


0.1.0 (2018-08-28)
==================

Features
--------

- Initial Release!
