# coding: utf-8

from goldflower.game import PlayerPokers

p = PlayerPokers.from_pokers_str(-1, '2-7,4-7,1-7')
print p
print p.poker_type

