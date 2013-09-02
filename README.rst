Buildout for the substanced.net website
=======================================

This buildout builds sdnet for development.  

Installing
----------

Check this package out of GitHub:

  $ git clone git@github.com:Pylons/sdnet_buildout.git

Cd into the ``sdnet_buildout`` directory.

Download virtualenv from http://pypi.python.org/pypi/virtualenv and install
it into your system Python (2.7+).  Once you've installed it, create a
virtualenv like so::

  $ $PYTHONHOME/bin/virtualenv .

Where $PYTHONHOME/bin is where your Python installation installs its scripts.
This will create a virtualenv within the ``sdnet_buildout`` directory.

After you've succesfully done the above, invoke the buildout via::

  $ bin/python bootstrap.py
  $ bin/buildout -U

.. warning:: The ``-U`` flag above is *very important*.  It specifies
   to buildout that it should ignore the ``~/.buildout/default.cfg``
   file, which is often trampled upon by other software in ways that
   are incompatible with our usage of buildout.

When it's finished, ``sdnet`` and its dependencies should have been
downloaded and compiled.  All required bfg software should also be installed
within the buildout environment.

If the buildout doesn't finish successfully due to a compilation error, make
sure you have gcc configured on your system and make sure you have the Python
development libraries installed.  For Debian-based systems, this means
installing the ``build-essentials`` and ``python-devel`` (or perhaps
``python-dev``) packages.  For Mac OS X users, this means having XCode Tools
installed.  Then try again.

You should then be able to run the following commands and visit the
running application at http://127.0.0.1:6588 in a browser.  You may
log in as ``admin`` with password ``admin`` to the management interface at
http://127.0.0.1:6546/manage::

  [chrism@oops sdnet_buildout]$ bin/supervisord
  [chrism@oops sdnet_buildout]$ bin/pserve etc/development.ini --reload

Success looks like this::

  [chrism@oops sdnet_buildout]$ bin/supervisord
  [chrism@oops sdnet_buildout]$ bin/populate etc/development.ini
  <lots of output>
  [chrism@thinko sdnet_buildout]$ bin/pserve etc/development.ini --reload
  Starting subprocess with file monitor
  2012-03-21 14:47:15,711 INFO  [ZEO.ClientStorage][MainThread] ('localhost', 9993) ClientStorage (pid=20128) created RW/normal for storage: '1'
  2012-03-21 14:47:15,713 INFO  [ZEO.cache][MainThread] created temporary cache file '<fdopen>'
  2012-03-21 14:47:15,716 INFO  [ZEO.ClientStorage][Connect([(2, ('localhost', 9993))])] ('localhost', 9993) Testing connection <ManagedClientConnection ('127.0.0.1', 9993)>
  2012-03-21 14:47:15,718 INFO  [ZEO.zrpc.Connection(C)][('localhost', 9993) zeo client networking thread] (127.0.0.1:9993) received handshake 'Z3101'
  2012-03-21 14:47:15,818 INFO  [ZEO.ClientStorage][Connect([(2, ('localhost', 9993))])] ('localhost', 9993) Server authentication protocol None
  2012-03-21 14:47:15,819 INFO  [ZEO.ClientStorage][Connect([(2, ('localhost', 9993))])] ('localhost', 9993) Connected to storage: ('localhost', 9993)
  2012-03-21 14:47:15,820 INFO  [ZEO.ClientStorage][Connect([(2, ('localhost', 9993))])] ('localhost', 9993) No verification necessary -- empty cache
  Starting server in PID 20128.
  serving on http://0.0.0.0:6588

The ``supervisord`` command starts the ZEO server (and any other required
processes).  The application will not work without the ZEO server running.
You can use ``bin/supervisorctl`` to get a Supervisor shell to start and stop
the ZEO server.  The ``etc/supervisord.conf`` file contains Supervisor
configuration.

The ``bin/py`` command within the buildout directory will invoke an
interactive Python prompt with all the ``sdnet`` dependencies available
for import.

Log files, pid files, and database files are stored in the ``var`` directory.

Updating Sources
----------------

To update checked out source packages, you can either use "git pull" within
the source directory (e.g. within ``src/sdnet``) or you can use the
``develop up`` command from within the buildout directory to update all
packages::

  bin/develop up

This will work with any package listed in the ``buildout.cfg`` ``[sources]``
section.

The ``develop`` command has other useful options such as ``activate``,
``deactivate`` and ``info``.  See ``develop --help`` for more info.
``decactivating`` a source is useful when there's a released version of the
source and you'd rather use it than the checked out version.

Updating the Buildout
---------------------

To update the buildout, run ``git pull`` within the buildout root dir, then::

   bin/buildout

This will cause all necessary software to be upgraded and installed as per
the directions in the ``buildout.cfg`` file.

You need to do this whenever you change the ``buildout.cfg`` file or add an
``install_requires`` dependency to ``sdnet`` or any other package.

Walking Up To the System After a Few Days
-----------------------------------------

If you're a developer on the project and you need to get the software and
your database data up to date after walking away for a few days, you should
do these things::

  $ cd sdnet_buildout
  $ git pull
  $ bin/buildout
  $ bin/develop up
  $ bin/sd_evolve --latest etc/development.ini

This should get you to a place where you're running the most current software
versions and it will apply any evolve steps to your development database.

Pinning Versions
----------------

The ``[versions]`` section in the buildout.cfg can be used to pin software to
particular versions.  For example::

  [versions]
  pyramid = 1.3

After adding a version pin to the ``buildout.cfg`` file, you need to run
``bin/buildout`` again to update the software.

We may eventually want to use a private index to mitigate against PyPI
downtime.  This would also give us a vector of control for versioning.  In
the meantime, we can pin versions this way.

Evolving the Database
---------------------

When "schema" changes need to be made to persistent objects, it will be
required to run the ``bin/sd_evolve`` script::

  $ bin/sd_evolve --latest etc/development.ini

This will run all required evolution scripts present in the system.

Running Tests
-------------

To run the ``sdnet`` unit tests, use the ``test`` script in the
``sdnet`` package, e.g.::

  cd src/sdnet
  ./test

To get test coverage information, use the ``coverage`` script::

  cd src/sdnet
  ./coverage
