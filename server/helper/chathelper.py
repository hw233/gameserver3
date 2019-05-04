# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import json

from db.robot import *
from db.robot_war import *
from db.robot_texas import *

from helper import wordhelper
from helper import encryhelper

def is_robot(session,r, uid):
    rs = r.hget('online', uid)
    if rs != None:
        if int(rs) == 1000 or int(rs) == 5800:
            return True
    else:
        robot = session.query(TRobot).filter(TRobot.uid == uid).first()
    if robot != None:
        return True
    robot_war = session.query(TRobotWar).filter(TRobotWar.uid == uid).first()
    if robot_war != None:
        return True
    robot_texas = session.query(TRobotTexas).filter(TRobotTexas.uid == uid).first()
    if robot_texas != None:
        return True
    return False

def is_humen(r, uid):
    rs = r.hget('online', uid)
    if rs != None:
        if int(rs) == 100:
            return True
    return False


def filter_chat(message):
    try:
        user_message_dict = json.loads(message)
        if isinstance(user_message_dict, int):
            user_message = wordhelper.replace_number(user_message_dict)
            return user_message
        elif isinstance(user_message_dict['content'], int):
            user_message = json.dumps(user_message_dict)
            return user_message
        elif 'content' in user_message_dict.keys():
            user_message = encryhelper.filter_emoji(user_message_dict['content'])
            user_message = wordhelper.filter_replace(user_message)
            user_message = wordhelper.replace_alpha_number(user_message)
            user_message_dict['content'] = user_message
            user_message = json.dumps(user_message_dict)
            return user_message
    except ValueError as e:
        user_message = encryhelper.filter_emoji(message)
        user_message = wordhelper.filter_replace(user_message)
        user_message = wordhelper.replace_alpha_number(user_message)
        # print user_message
        return user_message
