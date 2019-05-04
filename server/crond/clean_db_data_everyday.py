# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import sys
import os
import random
import time
import logging
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connect import *

from db.account_book import *
from db.goldflower import *
from db.goldflower_gambler import *

from db.war_log import *
from db.war_player_log import *
from db.war_award_log import *

from sqlalchemy import func,and_


class CleanUp:
    def __init__(self):
        pass
    @staticmethod
    def clean_table(session, table_name, where):
        results = session.query(table_name).filter(where).delete(synchronize_session='fetch')
        print u'Table %s Delete Result: %s' % (table_name, results)

def get_days_ago(days = 4, unixstamp = False):
    if unixstamp:
        return int(time.mktime((datetime.datetime.now() - datetime.timedelta(days=4)).date().timetuple()))
    return (datetime.datetime.now() - datetime.timedelta(days=4)).date().strftime('%Y-%m-%d')


if __name__ == '__main__':
    session = Session()
    # GameFlower
    CleanUp.clean_table(session, TAccountBook, TAccountBook.create_time <= get_days_ago(4))
    CleanUp.clean_table(session, TGoldFlower, TGoldFlower.create_time <= get_days_ago(4))
    CleanUp.clean_table(session, TGoldFlowerGambler, TGoldFlowerGambler.create_time <= get_days_ago(4))

    # WarTable
    CleanUp.clean_table(session, TWarAwardLog, TWarAwardLog.create_time <= get_days_ago(4,unixstamp=True))
    # delete war_log and war_player_log
    subquery = session.query(TWarLog.id).filter(TWarLog.create_time <= get_days_ago(4)).subquery()
    CleanUp.clean_table(session, TWarPlayerLog, TWarPlayerLog.war_id.in_(subquery))
    CleanUp.clean_table(session, TWarLog, TWarLog.create_time <= get_days_ago(4))
