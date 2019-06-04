#!/usr/bin/env python

import argparse
from contextlib import contextmanager
from twisted.web import server, resource
from twisted.internet import reactor
import pymysql
import pymysql.cursors
import time
import logging

'''
__author__="See AUTHORS.txt at https://github.com/Oneiroi/clustercheck"
__copyright__="David Busby, Percona Ireland Ltd"
__license__="GNU v3 + section 7: Redistribution/Reuse of this code is permitted under the GNU v3 license, as an additional term ALL code must carry the original Author(s) credit in comment form."
__description__="Provides a stand alone http service, evaluating wsrep_local_state intended for use with HAProxy. Listens on 8000"
'''

logger = logging.getLogger(__name__)


class opts:
    available_when_donor = 0
    disable_when_ro = 0
    is_ro = 0
    cache_time = 1
    last_query_time = 0
    last_query_result = 0
    cnf_file = '~/.my.cnf'
    being_updated = False
    # Overriding the connect timeout so that status check doesn't hang
    c_timeout = 10
    r_timeout = 5


def _db_is_ro(cursor):
    """is the database cluster node readonly?"""
    cursor.execute("SHOW VARIABLES LIKE 'read_only'")
    ro = cursor.fetchone()
    if ro['Value'].lower() in ('on', '1'):
        return True
    return False


def _db_get_wsrep_local_state(cursor):
    """
    get the WSREP local state or None
    see http://galeracluster.com/documentation-webpages/\
        galerastatusvariables.html#wsrep-local-state
    """
    cursor.execute("SHOW STATUS LIKE 'wsrep_local_state'")
    res = cursor.fetchone()
    if res:
        return int(res['Value'])
    return None


@contextmanager
def _db_get_connection(read_default_file, connect_timeout, read_timeout):
    try:
        conn = pymysql.connect(read_default_file=read_default_file,
                               connect_timeout=connect_timeout,
                               read_timeout=read_timeout,
                               cursorclass=pymysql.cursors.DictCursor)
        yield conn
    finally:
        try:
            conn.close()
        except:  # noqa
            pass


class ServerStatus(resource.Resource):
    isLeaf = True

    def render_OPTIONS(self, request):
        return self.render_GET(request)

    def render_GET(self, request):
        conn = None
        res = ''
        httpres = ''
        ctime = time.time()
        ttl = opts.last_query_time + opts.cache_time - ctime
        request.setHeader("Server", "PXC Python clustercheck / 2.0")

        if (ttl <= 0) and opts.being_updated is False:
            # cache expired
            opts.being_updated = True  # prevent mutliple threads falling through to MySQL for update
            opts.last_query_time = ctime
            # add some informational headers
            request.setHeader("X-Cache", [False, ])

            try:
                with _db_get_connection(
                        opts.cnf_file, opts.c_timeout, opts.r_timeout) as conn:
                    if conn:
                        curs = conn.cursor()
                        res = _db_get_wsrep_local_state(curs)
                        opts.last_query_response = res

                        if opts.disable_when_ro:
                            if _db_is_ro(curs):
                                opts.is_ro = True
                                res = None  # read_only is set and opts.disable_when_ro is also set, we should return this node as down

                        opts.being_updated = False  # reset the flag

            except pymysql.OperationalError as e:  # noqa
                opts.being_updated = False  # corrects bug where the flag is never reset on a communication failiure
                logger.exception("Can not get wsrep status")
        else:
            # add some informational headers
            request.setHeader("X-Cache", True)
            request.setHeader("X-Cache-TTL", "%d" % ttl)
            request.setHeader("X-Cache-Updating", opts.being_updated)
            request.setHeader("X-Cache-disable-when-RO", opts.disable_when_ro)
            request.setHeader("X-Cache-node-is-RO", opts.is_ro)
            # run from cached response
            res = opts.last_query_response

        if res is None:
            request.setResponseCode(503)
            request.setHeader("Content-type", "text/html")
            httpres = "Percona XtraDB Cluster Node state could not be retrieved."
            res = ()
            opts.last_query_response = res
            logger.warning('{} (503)'.format(httpres))
        elif res == 4 or (int(opts.available_when_donor) == 1 and res == 2):
            request.setResponseCode(200)
            request.setHeader("Content-type", "text/html")
            httpres = "Percona XtraDB Cluster Node is synced."
            logger.debug('{} (200)'.format(httpres))
        else:
            request.setResponseCode(503)
            request.setHeader("Content-type", "text/html")
            httpres = "Percona XtraDB Cluster Node is not synced."
            logger.warning('{} (503)'.format(httpres))

        return httpres


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--available-when-donor', dest='awd', default=0, help="Available when donor [default: %(default)s]")
    parser.add_argument('-r', '--disable-when-readonly', action='store_true', dest='dwr', default=False, help="Disable when read_only flag is set (desirable wen wanting to take a node out of the cluster wihtout desync) [default: %(default)s]")
    parser.add_argument('-c', '--cache-time', dest='cache', default=1, help="Cache the last response for N seconds [default: %(default)s]")
    parser.add_argument('-f', '--conf', dest='cnf', default='~/.my.cnf', help="MySQL Config file to use [default: %(default)s]")
    parser.add_argument('-p', '--port', dest='port', default=8000, help="Port to listen on [default: %(default)s]")
    parser.add_argument('-6', '--ipv6', dest='ipv6', action='store_true', default=False, help="Listen to ipv6 only (disabled ipv4) [default: %(default)s]")
    parser.add_argument('-4', '--ipv4', dest='ipv4', default='0.0.0.0', help="Listen to ipv4 on this address [default: %(default)s]")

    args = parser.parse_args()
    opts.available_when_donor = args.awd
    opts.disable_when_ro = args.dwr
    opts.cnf_file = args.cnf
    opts.cache_time = int(args.cache)

    bind = "::" if args.ipv6 else args.ipv4

    # configure logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    logger.info('Starting clustercheck...')
    reactor.listenTCP(int(args.port), server.Site(ServerStatus()), interface=bind)
    reactor.run()


if __name__ == '__main__':
    main()
