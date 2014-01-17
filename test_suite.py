#!/usr/bin/python

"""Tests for wind"""

import unittest
from wind.web.datastructures import FlexibleDeque


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
        q = FlexibleDeque(['y', '-', 'combinator', '...'])

        q.gather(12)
        assert q == FlexibleDeque(['y-combinator', '...'])

        q.gather(13)
        assert q == FlexibleDeque(['y-combinator.', '..'])
        
        q.gather(30)
        assert q == FlexibleDeque(['y-combinator...'])

        # Gather right
        q = FlexibleDeque(['Park', ' ', 'il', 'su', '...'])

        q.gather(9, left=False)
        assert q == FlexibleDeque(['Par', 'k ilsu...'])
        
        q.gather(30, left=False)
        assert q == FlexibleDeque(['Park ilsu...'])



if __name__ == '__main__':
    unittest.main()
