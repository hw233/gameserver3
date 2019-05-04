# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from config import var
from texas import texasconf
from lottery import lotteryconf

def is_hall_close(uid):
    if var.FIX_ENV_HALL and uid not in var.FIX_ENV_HALL_USERS:
        return True
    return False

def is_war_close(uid):
    if var.FIX_ENV_WAR and uid not in var.FIX_ENV_WAR_USERS:
        return True
    return False

def is_texas_close(uid):
    if texasconf.FIX and uid not in texasconf.FIX_USERS:
        return True
    return False

def is_lottery_close(uid):
    if lotteryconf.FIX and uid not in lotteryconf.FIX_USERS:
        return True
    return False

def kick_user_out(r,uid):
    if r.hexists('war_game', uid):
        r.hset('war_game',uid,0)
    elif r.hexists('online', uid):
        pass