#coding: utf-8
__author__ = 'Administrator'
import redis
import json
from db.connect import *
from db.gift import *

def load_gift(session,r):
    gifts = session.query(TGift).all()
    for gift in gifts:
       r.hmset('conf_gift',{
           gift.id:json.dumps({
               'id':gift.id,
               'icon':gift.icon,
               'name':gift.name,
               'description':gift.description,
               'gold':gift.gold,
               'create_time':str(gift.create_time),
           })
       })

def init():
    session = Session()
    r = redis.Redis(host='192.168.2.75')

    # 1.  cache gift from db
    load_gift(session,r)

if __name__ == "__main__":
    init()
    print "Done"