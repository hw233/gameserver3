# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import unittest
import mock

class RankTest(unittest.TestCase):
    def setUp(self):
        print 'setUp'

    def tearDown(self):
        print 'tearDown'

    def test_run(self):
        self.assertEquals(1,1)

if __name__ == '__main__':
    pass