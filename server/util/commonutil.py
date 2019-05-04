#coding: utf-8

import gevent
import random

from collections import namedtuple

def choice_dist_mode(lst,prob_key):
	total = reduce(lambda x,y: x + prob_key(y),lst,0)
	prob = random.randint(0,total)
	for item in lst:
		item_prob = prob_key(item)
		if item_prob >= prob:
			return item
		prob -= item_prob
	return None
	
class CollectionsUtil:
    @staticmethod
    def filter_one(lst,value,min_key,max_key):
        if callable(min_key):
            tmp = filter(lambda x:max_key(x) > value >= min_key(x),lst)
        else:
            tmp = filter(lambda x:getattr(x,max_key) > value >= getattr(x,min_key),lst)
        if len(tmp) == 0:
            return None
        return tmp[0]
    

def set_context(k,v):
    g = gevent.getcurrent()
    if not hasattr(g,"my_ctx"):
        g.my_ctx = {}
    g.my_ctx[k] = v

def get_context(k,default_value = None):
    g = gevent.getcurrent()
    if not hasattr(g,"my_ctx"):
        return default_value
    return g.my_ctx.get(k,default_value)

def destroy_context():
    g = gevent.getcurrent()
    if hasattr(g,"my_ctx"):
        del g.my_ctx



def colorize(text, code):
    return '\033[{0}m{1}\033[0m'.format(code, text)

color_codes = namedtuple(
    'ColorCodes',
    """
    strong,weak,underline,negative,hidden,strikethrow,
    black,red,green,yellow,blue,purple,cyan,lightgray,
    black_bg,red_bg,green_bg,yellow_bg,blue_bg,purple_bg,cyan_bg,lightgray_bg
    """
)


color = color_codes(
    strong=lambda x: colorize(x, 1),
    weak=lambda x: colorize(x, 2),
    underline=lambda x: colorize(x, 4),
    negative=lambda x: colorize(x, 7),
    hidden=lambda x: colorize(x, 8),
    strikethrow=lambda x: colorize(x, 9),

    black=lambda x: colorize(x, 30),
    red=lambda x: colorize(x, 31),
    green=lambda x: colorize(x, 32),
    yellow=lambda x: colorize(x, 33),
    blue=lambda x: colorize(x, 34),
    purple=lambda x: colorize(x, 35),
    cyan=lambda x: colorize(x, 36),
    lightgray=lambda x: colorize(x, 37),

    black_bg=lambda x: colorize(x, 40),
    red_bg=lambda x: colorize(x, 41),
    green_bg=lambda x: colorize(x, 42),
    yellow_bg=lambda x: colorize(x, 43),
    blue_bg=lambda x: colorize(x, 44),
    purple_bg=lambda x: colorize(x, 45),
    cyan_bg=lambda x: colorize(x, 46),
    lightgray_bg=lambda x: colorize(x, 47)
)
