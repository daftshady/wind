#!/usr/bin/python

"""Tests for wind"""

import unittest
from wind.datastructures import FlexibleDeque, CaseInsensitiveDict


class StreamTestCase(unittest.TestCase):
    """Tests for modules in web.stream"""
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_socket_read_bytes(self):
        pass


class DatastructuresTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_flexible_deque_gather(self):
        # Gather left
        q = FlexibleDeque([b'y', b'-', b'combinator', b'...'])

        q.gather(12)
        assert q == FlexibleDeque([b'y-combinator', b'...'])

        q.gather(13)
        assert q == FlexibleDeque([b'y-combinator.', b'..'])

        q.gather(30)
        assert q == FlexibleDeque([b'y-combinator...'])

        # Gather right
        q = FlexibleDeque([b'Park', b' ', b'il', b'su', b'...'])

        q.gather(9, left=False)
        assert q == FlexibleDeque([b'Par', b'k ilsu...'])

        q.gather(30, left=False)
        assert q == FlexibleDeque([b'Park ilsu...'])

    def test_caseinsensitive_dict(self):
        # Test case-insensitive comparison.
        dict_ = CaseInsensitiveDict()
        dict_['club'] = 'octagon'
        assert dict_.get('CLUB') == dict_.get('ClUb')

        # Test `get` method works.
        v = dict_.get('daft', 'punk')
        assert v == 'punk'

        v = dict_.get('CLub')
        assert v == 'octagon'


if __name__ == '__main__':
    unittest.main()
