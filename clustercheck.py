#!/usr/bin/env python

import sys
from twisted.web import server, resource
from twisted.internet import reactor
import MySQLdb
import MySQLdb.cursors
import optparse
import time

'''
__author__="See AUTHORS.txt at https://github.com/Oneiroi/clustercheck"
__copyright__="David Busby, Percona Ireland Ltd"
__license__="GNU v3 + section 7: Redistribution/Reuse of this code is permitted under the GNU v3 license, as an additional term ALL code must carry the original Author(s) credit in comment form."
__dependencies__="MySQLdb (python26-mysqldb (el5) / MySQL-python (el6) / python-mysqldb (ubuntu) / python-twisted >= 12.2)"
__description__="Provides a stand alone http service, evaluating wsrep_local_state intended for use with HAProxy. Listens on 8000"
'''

class opts:
    available_when_donor = 0
    cache_time           = 1
    last_query_time      = 0
    last_query_result    = 0
    cnf_file             = '~/.my.cnf'
    being_updated        = False
    # Overriding the connect timeout so that status check doesn't hang
    c_timeout              = 10

class ServerStatus(resource.Resource):
    isLeaf = True
    
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
                conn = MySQLdb.connect(read_default_file = opts.cnf_file,
                                       connect_timeout = opts.c_timeout,
                                       cursorclass = MySQLdb.cursors.DictCursor)

                if conn:
                    curs = conn.cursor()
                    curs.execute("SHOW STATUS LIKE 'wsrep_local_state'")
                    res = curs.fetchall()
                    opts.last_query_response = res
                    conn.close() #we're done with the connection let's not hang around
                    opts.being_updated = False #reset the flag

            except MySQLdb.OperationalError:
                opts.being_updated = False #corrects bug where the flag is never reset on a communication failiure
        else:
            #add some informational headers
            request.setHeader("X-Cache", True)
            request.setHeader("X-Cache-TTL", "%d" % ttl)
            request.setHeader("X-Cache-Updating", opts.being_updated)
            #run from cached response
            res = opts.last_query_response

        if len(res) == 0:
            request.setResponseCode(503)
            request.setHeader("Content-type", "text/html")
            httpres = "Percona XtraDB Cluster Node state could not be retrieved."
        elif res[0]['Value'] == '4' or (int(opts.available_when_donor) == 1 and res[0]['Value'] == '2'):
            request.setResponseCode(200)
            request.setHeader("Content-type", "text/html")
            httpres = "Percona XtraDB Cluster Node is synced."
        else:
            request.setResponseCode(503)
            request.setHeader("Content-type", "text/html")
            httpres = "Percona XtraDB Cluster Node is not synced."


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
    parser.add_option('-c','--cache-time', dest='cache', default=1, help="Cache the last response for N seconds [default: %default]")
    parser.add_option('-f','--conf', dest='cnf', default='~/.my.cnf', help="MySQL Config file to use [default: %default]")
    parser.add_option('-p','--port', dest='port', default=8000, help="Port to listen on [default: %default]")
    parser.add_option('-6','--ipv6', dest='ipv6', action='store_true', default=False, help="Listen to ipv6 only (disabled ipv4) [default: %default]")
    parser.add_option('-4','--ipv4', dest='ipv4', default='0.0.0.0', help="Listen to ipv4 on this address [default: %default]")
    options, args             = parser.parse_args()
    opts.available_when_donor = options.awd
    opts.cnf_file             = options.cnf
    opts.cache_time           = int(options.cache)

    bind = "::" if options.ipv6 else options.ipv4

    reactor.listenTCP(int(options.port), server.Site(ServerStatus()), interface=bind)
    reactor.run()
