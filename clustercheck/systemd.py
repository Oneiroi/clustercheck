# Copyright (C) 2019 SUSE Linux GmbH

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import logging
import os
import socket
import sys


logger = logging.getLogger(__name__)


class SystemdNotify(object):
    def __init__(self):
        self._socket = None
        self._connect()

    def _close(self):
        if self._socket:
            try:
                self._socket.close()
                self._socket = None
            except Exception as e:  # noqa
                logger.exception('Can not close socket')

    def _connect(self):
        self._close()
        try:
            addr = os.getenv('NOTIFY_SOCKET')
            if addr:
                self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                self._socket.settimeout(2.0)
                self._socket.connect(addr)
        except Exception as e:  # noqa
            logger.exception('Can not connect to "NOTIFY_SOCKET"')
            self.socket = None

    def _bytes(self, x):
        # from http://python3porting.com/problems.html#nicer-solutions
        if sys.version_info < (3,):
            return x
        else:
            import codecs
            return codecs.latin_1_encode(x)[0]

    def send(self, state):
        if not self._socket:
            logger.warning(
                'systemd: Not sending "{}. No socket connection"'.format(state))
            return

        b = self._bytes(state)
        try:
            self._socket.sendall(b)
        except Exception as e:  # noqa
            logger.exception(
                'systemd: Can not send state "{}" ("{}")'.format(b, state))
        else:
            logger.debug('systemd: Sent state"{}" ("{}")'.format(b, state))
