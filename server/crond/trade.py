# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import sys
import os
import redis

import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connect import *
from db.trade import *
from db.user import *
from db.mail import *
from config import var
from sqlalchemy import func,and_

from hall.messagemanager import *

DAYS = 3
ONLINE = 0

session = Session()

def get_out_of_stack():
    return session.query(TTrade).filter(and_(func.datediff(func.now(), TTrade.sell_time) >= DAYS, TTrade.status == ONLINE)).all()

def backof_user_gold(trade):
   
    content = u'您挂售的%d金币，售价%d钻石，超过72小时未能售出，自动下架' % (trade.gold, trade.diamond)
    MessageManager.send_mail(session, trade.seller, 0,
                             title=u'金币交易自动下架',
                             content=content,
                             type=1,
                             gold=trade.gold
                             )
    MessageManager.push_notify_mail(r, trade.seller)

if __name__ == '__main__':
    r = redis.Redis(**var.CROND_REDIS)
    items = get_out_of_stack()
    session.begin()
    for index, item in enumerate(items):
        item.status = -1
        session.merge(item)
        backof_user_gold(r, item)
        print item
    session.commit()
