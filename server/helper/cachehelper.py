# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import json
from config.var import *

def add_notification_queue(redis, users,p1, p2, notifi_type = N_BROADCAST):
    item = {'users':users,'param1':p1,'param2':p2,'notifi_type':notifi_type}
    redis.lpush('notification_queue', json.dumps(item))

def add_friend_queue(redis,to_user):
    redis.hincrby('friend_queue', to_user)

def del_friend_queue(redis,to_user):
    redis.hincrby('friend_queue',to_user, -1)

def get_users_online(redis, users):
    for user in users:
        user.is_online = get_user_online(redis, user.id)

def get_user_online(redis, user):
    exists = redis.hexists('online', user)
    if exists > 0:
        return True
    return False

def get_talk_session(redis, user):
    talk_id = redis.hget('talk_session', user)
    if talk_id is not None and talk_id > 0:
        return talk_id
    return 0

def set_task_session(redis, user, talk_id):
    return redis.hset('talk_session', user, talk_id)

# def set_friend_msg(redis, )


if __name__ == '__main__':




    import redis
    r = redis.Redis(host='121.201.69.204', port=26379, db=1, password='Wgc@123456')
    # print r.ping()
    class User:
        def __init__(self, id):
            self.id = id
            self.is_online = False

        def __repr__(self):
            return 'id=%d, is_online=%s' % (self.id, self.is_online)

    u1 = User(11254)
    u2 = User(11253)
    u3 = User(11231)
    users = [u1, u2, u3]
    get_users_online(r, users)
    # for user in users:
    #     print user