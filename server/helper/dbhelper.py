#coding:utf-8

from datetime import datetime

from db.account_book import *
from helper.constant import *

def recycle_gold(session,**kw):
    ab = TAccountBook()
    ab.type = TYPE_RECYCLE
    ab.gold = 0
    ab.diamond = 0
    ab.game_id = 0
    ab.uid = -1
    ab.create_time = datetime.now()
    for k,v in kw.items():
        setattr(ab,k,v)

    session.add(ab)

def provide_gold(session,**kw):
    ab = TAccountBook()
    ab.type = TYPE_PROVIDE
    ab.gold = 0
    ab.diamond = 0
    ab.game_id = 0
    ab.uid = -1

    ab.create_time = datetime.now()
    for k,v in kw.items():
        setattr(ab,k,v)

    session.add(ab)