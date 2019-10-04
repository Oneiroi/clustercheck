clustercheck
============

![Travis CI build state](https://travis-ci.com/Oneiroi/clustercheck.svg?branch=twisted "TravisCI clustercheck build state")[![Total alerts](https://img.shields.io/lgtm/alerts/g/Oneiroi/clustercheck.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Oneiroi/clustercheck/alerts/)

Updated clustercheck, intended to be standalone service for the reporting of Percona XtraDB cluster nodes.

This module requires MySQLdb package for python to function, aswell as a present ~/.my.cnf for the use the service will run as.

This version is rewritten to use Python twisted, so this module is required.

To start at run time via sysvinit (largely deprecated):
echo "/usr/bin/clustercheck -f /etc/my.cnf >> /var/log/clustercheck.log 2>&1 &" >> /etc/rc.local


systemd support
===============
clustercheck supports systemd notify (READY and WATCHDOG). To enable the
features, adjust your .service file and add:

    [Service]
    Type=notify
    WatchdogSec=10


Running the testsuite
=====================
There are some basic unittests which can be called via `tox`:

    tox -epy37

There are also linter tests available. Theses can be executed via `tox`:

    tox -epep8

Contribute
==========

1. fork it.
2. Create a branch (`git checkout -b my_markup`)
3. Commit your changes (`git commit -am "I made these changes 123"`) updating AUTHORS.txt
4. Push to the branch (`git push origin my_markup`)
5. Create an [Issue][1] with a link to your branch

[1]: https://github.com/Oneiroi/clustercheck/issues

