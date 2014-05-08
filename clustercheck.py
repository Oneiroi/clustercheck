#!/usr/bin/env python

from twisted.web import server, resource
from twisted.internet import reactor
import MySQLdb
import MySQLdb.cursors
import optparse

'''
__author__="See AUTHORS.txt at https://github.com/Oneiroi/clustercheck"
__copyright__="David Busby, Percona Ireland Ltd"
__license__="GNU v3 + section 7: Redistribution/Reuse of this code is permitted under the GNU v3 license, as an additional term ALL code must carry the original Author(s) credit in comment form."
__dependencies__="MySQLdb (python26-mysqldb (el5) / MySQL-python (el6) / python-mysqldb (ubuntu) / pyton-twisted)"
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
        conn = None
        res = ''
	httpres = ''

        try:
            conn = MySQLdb.connect(read_default_file = opts.cnf_file,
                                   connect_timeout = opts.c_timeout,
                                   cursorclass = MySQLdb.cursors.DictCursor)

            if conn:
                curs = conn.cursor()
                curs.execute("SHOW STATUS LIKE 'wsrep_local_state'")
                res = curs.fetchall()
            else:
                res = ''
        except MySQLdb.OperationalError:
            print "Error connecting with MySQL"

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

        if conn:
            conn.close()

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
    parser.add_option('-f','--conf', dest='cnf', default='~/.my.cnf', help="MySQL Config file to use [default: %default]")
    parser.add_option('-p','--port', dest='port', default=8000, help="Port to listen on [default: %default]")
    options, args = parser.parse_args()
    opts.available_when_donor = options.awd
    opts.cnf_file =   options.cnf

    reactor.listenTCP(int(options.port), server.Site(ServerStatus()))
    reactor.run()
