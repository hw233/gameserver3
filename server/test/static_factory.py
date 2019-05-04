# -*- coding: utf-8 -*-
__author__ = 'Administrator'


class test:

    def __init__(self, order):
        self.order = order

    def __repr__(self):
        return 'test'

    def handler(self):
        return 'test11111',self.order.comment

class foo:
    def __init__(self, order):
        self.order = order

    def handler(self):
        return 'foo22222',self.order.comment

    def __repr__(self):
        return 'foo'

class order:
    def __init__(self, comment):
        self.comment = comment

class OrderFactory:
    type = {
            'test_message':test,
            'foo_message':foo
        }

    @staticmethod
    def create(order):
        if order.comment in OrderFactory.type:
            handler = OrderFactory.type[order.comment]
            return handler(order)

if __name__ == '__main__':

    print OrderFactory.create(order('foo_message')).handler()