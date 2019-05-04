#coding: utf-8
import gevent
from gevent import monkey;monkey.patch_all()
import json
import logging
import traceback


import random,time

from collections import Counter
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time

from proto.constant_pb2 import *

from message.base import *
from message.resultdef import *

    

class RoomManager:
    def __init__(self,service,max_user):
        self.service = service
        if service != None:
            self.redis = service.redis
        else:
            self.redis = None

        self.max_user = max_user
        
    def get_user_room(self,uid):
        prefix = "room_users_"
        room_ids = self.redis.keys(prefix + "*")
        for room_id in room_ids:
            if self.redis.hexists(room_id,uid):
                return int(room_id[len(prefix):])
        return -1
            
    def find_room(self):
        counters = []
        prefix = "room_users_"
        room_ids = self.redis.keys(prefix + "*")
        for room_id in room_ids:
            rid = int(room_id[len(prefix):])
            counters.append((rid,self.redis.hlen(room_id),))

        if len(counters) == 0:
            return -1
        idle_one = min(counters,key=lambda x:x[1])

        while len(counters) > 0:
            room_info = max(counters,key=lambda x:x[1])
            if room_info[1] >= self.max_user:
                counters.remove(room_info)
            else:
                return room_info[0]
        
        return idle_one[0]

    
    
        
if __name__ == '__main__':
    pass
