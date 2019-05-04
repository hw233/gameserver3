# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import random
from db.connect import *
from db.robot_war import *
from db.war_player_brief import *


class RobotBrief:
    def __init__(self):
        pass

    def change_brief(self, session):
        robot_war = session.query(TRobotWar).all()
        unique_uids = self.get_users(robot_war)
        for robot in unique_uids:
            robot_rief = session.query(TWarPlayerBrief).filter(TWarPlayerBrief.uid == robot).first()
	    if robot_rief == None:
		continue
            robot_rief.total_games = random.randint(50, 500)
            session.add(robot_rief)
            session.flush()

    def get_users(self, robot_war):
        uids = [x.uid for x in robot_war]
        unique_uids = set([])
        len_uids = len(uids)/2
        for _ in range(len_uids):
            u = random.choice(uids)
            uids.remove(u)
            unique_uids.add(u)
        return unique_uids

if __name__ == '__main__':
    session = Session()
    robot = RobotBrief()
    robot.change_brief(session)

