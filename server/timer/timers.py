#coding=utf-8
import logging
import random
import time
from datetime import datetime
import traceback
from sqlalchemy.sql import select, update, delete, insert, and_,or_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

from proto.constant_pb2 import *
from proto.struct_pb2 import *

from db.connect import *
from db.timer import *

from config import var
from config.textdef import *

from timerdef import *

TIMER_HANDLERS = {
    
}

SECOND_HANDLERS = {}

MINUTE_HANDLERS = {}

HOUR_HANDLERS = {}

DAY_HANDLERS = {}

def TIMER(timerid):
    def f(func):
        TIMER_HANDLERS[timerid] = func
        return func
    return f

def HOUR(*hours):
    def f(func):
        times = hours
        if times == None or len(times) == 0:
            times = (-1,)
        for hh in times:
            if hh in HOUR_HANDLERS:
                handlers = HOUR_HANDLERS[hh]
            else:
                handlers = []
                HOUR_HANDLERS[hh] = handlers
            handlers.append(func)
        return func
    return f

def SECOND(*secs):
    def f(func):
        times = secs
        if times == None or len(times) == 0:
            times = (-1,)
        for ss in times:
            if ss in SECOND_HANDLERS:
                handlers = SECOND_HANDLERS[ss]
            else:
                handlers = []
                SECOND_HANDLERS[ss] = handlers
            handlers.append(func)
        return func
    return f

def MINUTE(*minutes):
    def f(func):
        times = minutes
        if times == None or len(times) == 0:
            times = (-1,)
        for mm in times:    
            if mm in MINUTE_HANDLERS:
                handlers = MINUTE_HANDLERS[mm]
            else:
                handlers = []
                MINUTE_HANDLERS[mm] = handlers
            handlers.append(func)
        return func
    return f
    
def DAY(*days):
    def f(func):
        times = days
        if times == None or len(times) == 0:
            times = (-1,)
        for dd in times:
            if dd in DAY_HANDLERS:
                handlers = DAY_HANDLERS[dd]
            else:
                handlers = []
                DAY_HANDLERS[dd] = handlers
            handlers.append(func)
        return func
    return f
# 测试用代码
def get_all_handlers():
    handlers = []
    for k,v in HOUR_HANDLERS.items():
        handlers.extend(v)
    for k,v in DAY_HANDLERS.items():
        handlers.extend(v)
    return handlers
    
def get_second_handlers(sec):
    handlers = []
    if -1 in SECOND_HANDLERS:
        handlers.extend(SECOND_HANDLERS[-1])
    if sec in SECOND_HANDLERS:
        handlers.extend(SECOND_HANDLERS[sec])
    return handlers    
    
def get_minute_handlers(minute):
    handlers = []
    if -1 in MINUTE_HANDLERS:
        handlers.extend(MINUTE_HANDLERS[-1])
    if minute in MINUTE_HANDLERS:
        handlers.extend(MINUTE_HANDLERS[minute])
    return handlers        
    
def get_hour_handlers(hour):
    handlers = []
    if -1 in HOUR_HANDLERS:
        handlers.extend(HOUR_HANDLERS[-1])
    if hour in HOUR_HANDLERS:
        handlers.extend(HOUR_HANDLERS[hour])
    return handlers
    
def get_day_handlers(day):
    handlers = []
    if -1 in DAY_HANDLERS:
        handlers.extend(DAY_HANDLERS[-1])
    if day in DAY_HANDLERS:
        handlers.extend(DAY_HANDLERS[day])
    return handlers

@TIMER(TIMER_EVENT_INCREASE_POWER)
def handle_timer_increase_power(service,session,timer):
    logging.info("Increase Power Now ...")
    role_id = timer.object_id
    role_db = RoleDB(session,role_id)
    role = role_db.get_role()
    
    power,max_power = role_db.get_power()
    
    if power < max_power:
        role.power += 1
    
    if (power + 1) < max_power:
        new_increase_power_timer(session,role_db,False)
    else:
        send_apns_push(session,role_id,APNS_PUSH_POWER_FULL)    
    return
    



#@HOUR()
#def handle_rank(service,session):
#    pass 
    
#@MINUTE()
#def handle_rank(service,session):
#    refresh_one_rank(session,1)    
    
    
#@DAY()
#def handle_day_delete_expired_mail(service,session):
#    logging.info("Timer Executing : delete mail")
    
    
#@MINUTE(*range(60))
#def handle_send_world_boss_notice(service,session):
#    pass
        
         
        
if __name__ == "__main__":
    
    session = Session() 
    try :
        session.begin()
        handle_rank(None,session)
        session.commit()
    except:
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()