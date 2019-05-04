#coding: utf-8
'''
Created on 2012-2-20

@author: Administrator
'''

import sys
import random

from datetime import datetime

from db.connect import *
from db.account import *
from db.user import *
from db.user_goldflower import *
from db.robot import *

def create_robot(count):
    session = Session()
    try :
        session.begin()

        for i in xrange(count):
            account = TAccount()
            account.mobile = "1234567"
            account.imei = "imei" + str(i)
            account.imsi = "imsi" + str(i)
            account.state = 0
            account.password = "123456"
            account.device_id = "did" + str(i)
            session.add(account)
            session.flush()

            user = TUser()
            user.id = account.id
            user.nick = "robot" + str(account.id)
            user.avatar = "http://img1.3lian.com/2016/gif/w/15/61.jpg"
            user.gold = 200000
            user.diamond = 0
            user.vip = 0
            user.money = 0
            user.type = 1
            user.create_time = datetime.now()
            user.channel = "test"
            session.add(user)

            user_gf = TUserGoldFlower()
            user_gf.id = user.id
            user_gf.channel = "test"
            user_gf.exp = 0
            user_gf.win_games = 0
            user_gf.total_games = 0
            user_gf.best=""
            user_gf.create_time = datetime.now()

            session.add(user_gf)

            robot = TRobot()
            robot.uid = user.id
            robot.type = random.choice([1,2,3])
            robot.win_gold = 0
            robot.state = 1
            robot.create_time = datetime.now()
            session.add(robot)

        session.commit()
    except :
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":

    count = int(sys.argv[1])
    create_robot(count)
    print "Done"