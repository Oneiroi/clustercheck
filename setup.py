#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='clustercheck',
      use_scm_version=True,
      setup_requires=['setuptools_scm'],
      install_requires=['Twisted'],
      description='Standalone service for reporting of Percona XtraDB/Galera cluster nodes',
      license='AGPL-3.0-only',
      keywords='galera,mariadb,percona,database,cluster',
      author='David Busby',
      author_email='oneiroi@fedoraproject.org',
      url='https://github.com/Oneiroi/clustercheck/',
      packages=['clustercheck'],
)
