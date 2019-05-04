# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import redis

class WarTool:
    def __init__(self):
        self.redis = redis.Redis(password='Wgc@123456',db=1)
        self.user_count = 0
        self.robot_count = 0
        self.in_war_users = []

    def load(self):
        users = self.redis.hgetall('war_online')
        war_users = set([uid for uid,is_online in users.items() if int(is_online) == 1])
        self.in_war_users = self.get_users(war_users)
        self.robot_count = len(war_users) - self.robot_count

    def get_users(self, war_users):
        users = self.redis.hgetall('online')
        online_users = set([uid for uid,access_service in users.items() if int(access_service) == 100])
        in_war_users = war_users & online_users
        self.user_count = len(in_war_users)
        return in_war_users

    def __repr__(self):
        return 'users=%d, robot=%d\nusers_online=%s' % (self.user_count, self.robot_count, str(self.in_war_users))

if __name__ == '__main__':
    war_tool = WarTool()
    war_tool.load()
    print war_tool
