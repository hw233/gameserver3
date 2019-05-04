# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from db.connect import *
from db.user import *
from db.user_goldflower import *
from db.account import *
from datetime import datetime,date

session = Session()
for i in range(31,1031):
    account = TAccount()
    account.state = -1
    account.device_id = 'robot_'+str(i)
    session.add(account)
    session.flush()

    user = TUser()
    user.id = account.id
    user.nick = 'robot_'+str(account.id)
    user.avatar = ''
    user.gold = 50000
    user.diamond = 10000
    user.vip = 0
    user.money = 0
    user.type = 0
    user.charm = 0
    user.birthday = date(2000,1,1)
    user.sign = 'i\'m robot %d' % account.id
    user.sex = 0
    user.channel = 'robot'
    user.create_time = datetime.now()
    session.add(user)


    user_gf = TUserGoldFlower()
    user_gf.id = account.id
    user_gf.channel = 'robot'
    user_gf.win_games = 0
    user_gf.total_games = 0
    user_gf.best = ''
    user_gf.wealth_rank = 0
    user_gf.win_rank = 0
    user_gf.charm_rank = 0
    user_gf.charge_rank = 0
    user_gf.create_time = datetime.now()
    user_gf.max_bank = 0
    user_gf.max_items = 0
    user_gf.max_gifts = 0
    user_gf.signin_days = 0
    user_gf.last_signin_day = date(2000,1,1)
    user_gf.online_time = 0
    user_gf.login_times = 0
    user_gf.change_nick = -1
    session.add(user_gf)
    session.flush()


