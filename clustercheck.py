#!/usr/bin/env python

import BaseHTTPServer
import MySQLdb
import MySQLdb.cursors
import optparse
import time
import socket

'''
__author__="See AUTHORS.txt at https://github.com/Oneiroi/clustercheck"
__copyright__="David Busby, Percona Ireland Ltd"
__license__="GNU v3 + section 7: Redistribution/Reuse of this code is permitted under the GNU v3 license, as an additional term ALL code must carry the original Author(s) credit in comment form."
__dependencies__="MySQLdb (python26-mysqldb (el5) / MySQL-python (el6) / python-mysqldb (ubuntu))"
__description__="Provides a stand alone http service, evaluating wsrep_local_state intended for use with HAProxy. Listens on 8000"
'''

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

class clustercheck(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.do_GET()

    def do_send_response(self, code, message):
        # Send a simple text/html response. However if the connection has closed
        # gracefully continue. This allows the database conn to be closed if
        # necessary and to clea the being_updated flag.
        # NOTE(jhesketh): this doesn't stop exceptions from being logged as the
        # cleanup done by SocketServer still tries to flush before closing the
        # connection
        try:
            self.send_response(code)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(message)
        except socket.error as e:
            pass

    def do_GET(self):
        ctime = time.time()
        if ((ctime - opts.last_query_time) > opts.cache_time) and opts.being_updated == False:
            #cache expired
            opts.being_updated   = True
            opts.last_query_time = ctime

            conn = None
            try:
                conn = MySQLdb.connect(
                read_default_file = opts.cnf_file,
                connect_timeout = opts.c_timeout,
                cursorclass = MySQLdb.cursors.DictCursor)

            except MySQLdb.OperationalError:
                opts.being_updated   = False #corrects a bug where the flag is never reset on communication failiure

            if conn:
                curs = conn.cursor()
                curs.execute("SHOW STATUS LIKE 'wsrep_local_state'")
                res = curs.fetchall()
            else:
                res = ''

            if opts.disable_when_ro:
                curs.execute("SHOW VARIABLES LIKE 'read_only'")
                ro = curs.fetchone()
                if ro['Value'].lower() in ('on','1'):
                    res = () #read_only is set and opts.disable_when_ro is also set, we should return this node as down
                    opts.is_ro = True

            if len(res) == 0:
                opts.last_query_result = 0
                self.do_send_response(503, "Percona XtraDB Cluster Node state could not be retrieved.")

            elif res[0]['Value'] == '4' or (int(opts.available_when_donor) == 1 and res[0]['Value'] == '2'):
                opts.last_query_result = res[0]['Value']
                self.do_send_response(200, "Percona XtraDB Cluster Node is synced.")
            else:
                opts.last_query_result = res[0]['Value']
                self.do_send_response(503, "Percona XtraDB Cluster Node is not synced.")

            if conn:
                conn.close()
                opts.being_updated = False
        else:
        #use cache result
            if opts.last_query_result == '4' or (int(opts.available_when_donor) == 1 and opts.last_query_result == '2'):
                self.do_send_response(200, "CACHED: Percona XtraDB Cluster Node is synced.")
            else:
                self.do_send_response(503, "CACHED: Percona XtraDB Cluster Node is not synced.")

"""
Usage:
pyclustercheck &>$LOGFILE &
To test:
curl http://127.0.0.1:8000

"""
if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-a','--available-when-donor', dest='awd', default=0, help="Available when donor [default: %default]")
    parser.add_option('-r','--disable-when-readonly', action='store_true', dest='dwr', help="Disable when read_only flag is set (desirable when wanting to take a node out of the cluster without desync) [default: %default]")
    parser.add_option('-c','--cache-time', dest='cache', default=1, help="Cache the last response for N seconds [default: %default]")
    parser.add_option('-f','--conf', dest='cnf', default='~/.my.cnf', help="MySQL Config file to use [default: %default]")
    parser.add_option('-p','--port', dest='port', default=8000, help="Port to listen on [default: %default]")
    parser.add_option('-6','--ipv6', action="store_true", dest='ipv6', default=False, help="Listen on ipv6 [default: %default]")

    options, args = parser.parse_args()
    opts.available_when_donor = options.awd
    opts.disable_when_ro = options.dwr
    opts.cnf_file =   options.cnf
    opts.cache_time = options.cache

    server_class = BaseHTTPServer.HTTPServer

    if options.ipv6:
        server_class.address_family = socket.AF_INET6

    httpd = server_class(('',int(options.port)),clustercheck)
    httpd.serve_forever()
