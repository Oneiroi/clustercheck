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

import mock
import unittest

import clustercheck


class TestClustercheck(unittest.TestCase):
    def test__db_is_ro(self):
        cursor_mock = mock.MagicMock()
        # check for OFF
        cursor_mock.fetchone.return_value = {u'Value': 'OFF',
                                             u'Variable_name': 'read_only'}
        res = clustercheck._db_is_ro(cursor_mock)
        cursor_mock.called_once_with()
        self.assertEqual(res, False)

        # check for ON
        cursor_mock.fetchone.return_value = {u'Value': 'ON',
                                             u'Variable_name': 'read_only'}
        res = clustercheck._db_is_ro(cursor_mock)
        cursor_mock.called_once_with()
        self.assertEqual(res, True)

    def test__db_get_wsrep_local_state(self):
        cursor_mock = mock.MagicMock()
        # check for available value
        cursor_mock.fetchone.return_value = {
            u'Value': '4',
            u'Variable_name': 'wsrep_local_state'
        }
        res = clustercheck._db_get_wsrep_local_state(cursor_mock)
        cursor_mock.called_once_with()
        self.assertEqual(res, 4)

        # check for non-available value (eg. no cluster)
        cursor_mock.fetchone.return_value = {
        }
        res = clustercheck._db_get_wsrep_local_state(cursor_mock)
        cursor_mock.called_once_with()
        self.assertEqual(res, None)
