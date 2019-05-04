# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import random
import collections

def run():
    tmp = []
    data = [(40,60) for _ in range(65)] + [(60, 100) for _ in range(35)]
    for _ in range(100):
        tmp.append( random.randint( *random.choice(data)))
    return tmp

def calc():
    c = collections.Counter()
    for _ in range(100000):
        c[ sum(run()) / 100 ] += 1
        # print sum(run()) / 100  / 100
    return c
class C:
    def foo(self):
        return 'foo'
    def bar(self):
        return 'bar'
if __name__ == '__main__':
    # print calc()
    # print run()

    try:
        c = C()


    except Exception as e:
        print c.foo()
        print e.message
    finally:
        print c.bar()
