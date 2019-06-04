
import time
import mechanize

class Transaction(object):
    def __init__(self):
        pass

    def run(self):
        start = time.time()
        br = mechanize.Browser()
        br.set_handle_robots(False)
        resp = br.open('http://localhost:8000')
        resp.read()
        latency = time.time() - start
        self.custom_timers['Cluster_check_latency'] = latency
        assert (resp.code in (200,503)), 'Bad HTTP Response'


if __name__ == '__main__':
    trans = Transaction()
    trans.run()
    print(trans.custom_timers)
