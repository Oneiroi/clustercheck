#!/usr/bin/env python

import argparse
import sys
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
__dependencies__="PyMySQL (rh-python35-python-PyMySQL (el6) / python-pymysql (ubuntu) / python-PyMySQL (openSUSE) / python-twisted >= 12.2)"
__description__="Provides a stand alone http service, evaluating wsrep_local_state intended for use with HAProxy. Listens on 8000"
'''

logger = logging.getLogger(__name__)


class opts:
    available_when_donor = 0
    disable_when_ro      = 0
    is_ro                = 0
    cache_time           = 1
    last_query_time      = 0
    last_query_result    = 0
    cnf_file             = '~/.my.cnf'
    being_updated        = False
    # Overriding the connect timeout so that status check doesn't hang
    c_timeout              = 10
    r_timeout              = 5

class ServerStatus(resource.Resource):
    isLeaf = True

    def render_OPTIONS(self, request):
        return self.render_GET(request)

    def render_GET(self, request):
        conn    = None
        res     = ''
        httpres = ''
        ctime   = time.time()
        ttl     = opts.last_query_time + opts.cache_time - ctime
        request.setHeader("Server", "PXC Python clustercheck / 2.0")

        if (ttl <= 0) and opts.being_updated == False:
            #cache expired
            opts.being_updated = True #prevent mutliple threads falling through to MySQL for update
            opts.last_query_time = ctime
            #add some informational headers
            request.setHeader("X-Cache", [False, ])

            try:
                conn = pymysql.connect(read_default_file = opts.cnf_file,
                                       connect_timeout = opts.c_timeout,
                                       read_timeout = opts.r_timeout,
                                       cursorclass = pymysql.cursors.DictCursor)

                if conn:
                    curs = conn.cursor()
                    curs.execute("SHOW STATUS LIKE 'wsrep_local_state'")
                    res = curs.fetchall()
                    opts.last_query_response = res

                    if opts.disable_when_ro:
                        curs.execute("SHOW VARIABLES LIKE 'read_only'")
                        ro = curs.fetchone()
                        if ro['Value'].lower() in ('on', '1'):
                            res = () #read_only is set and opts.disable_when_ro is also set, we should return this node as down
                            opts.is_ro = True

                    conn.close() #we're done with the connection let's not hang around
                    opts.being_updated = False #reset the flag

            except MySQLdb.OperationalError as e:
                opts.being_updated = False #corrects bug where the flag is never reset on a communication failiure
                logger.exception()
        else:
            #add some informational headers
            request.setHeader("X-Cache", True)
            request.setHeader("X-Cache-TTL", "%d" % ttl)
            request.setHeader("X-Cache-Updating", opts.being_updated)
            request.setHeader("X-Cache-disable-when-RO", opts.disable_when_ro)
            request.setHeader("X-Cache-node-is-RO", opts.is_ro)
            #run from cached response
            res = opts.last_query_response

        if len(res) == 0:
            request.setResponseCode(503)
            request.setHeader("Content-type", "text/html")
            httpres = "Percona XtraDB Cluster Node state could not be retrieved."
            res=()
            opts.last_query_response = res
            logger.warning('{} (503)'.format(httpres))
        elif res[0]['Value'] == '4' or (int(opts.available_when_donor) == 1 and res[0]['Value'] == '2'):
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

"""
Usage:
pyclustercheck &>$LOGFILE &
To test:
curl http://127.0.0.1:8000

"""
if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-a','--available-when-donor', dest='awd', default=0, help="Available when donor [default: %default]")
    parser.add_option('-r','--disable-when-readonly', action='store_true', dest='dwr', default=False, help="Disable when read_only flag is set (desirable when wanting to take a node out of the cluster wihtout desync) [default: %default]")
    parser.add_option('-c','--cache-time', dest='cache', default=1, help="Cache the last response for N seconds [default: %default]")
    parser.add_option('-f','--conf', dest='cnf', default='~/.my.cnf', help="MySQL Config file to use [default: %default]")
    parser.add_option('-p','--port', dest='port', default=8000, help="Port to listen on [default: %default]")
    parser.add_option('-6','--ipv6', dest='ipv6', action='store_true', default=False, help="Listen to ipv6 only (disabled ipv4) [default: %default]")
    parser.add_option('-4','--ipv4', dest='ipv4', default='0.0.0.0', help="Listen to ipv4 on this address [default: %default]")
    options, args             = parser.parse_args()
    opts.available_when_donor = options.awd
    opts.disable_when_ro      = options.dwr
    opts.cnf_file             = options.cnf
    opts.cache_time           = int(options.cache)

    bind = "::" if options.ipv6 else options.ipv4

    # configure logging
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    logger.info('Starting clustercheck...')
    reactor.listenTCP(int(options.port), server.Site(ServerStatus()), interface=bind)
    reactor.run()
