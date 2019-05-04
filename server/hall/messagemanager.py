# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import json
import time
import logging
import gevent

from config.var import *
from proto.constant_pb2 import *
from db.mail import *
from message.base import *
from proto.chat_pb2 import *


class MessageManager:
    @staticmethod
    def sleep_sec(sec, func, *args):
        gevent.spawn_later(sec, func, *args)

    @staticmethod
    def push_vip_login(redis, vip_exp, nick, uid):
        message = {'vip_exp':vip_exp, 'nick':nick,'uid':uid}
        item = {'users':redis.hkeys('online'),'param1':PUSH_TYPE['vip_login'],'param2':message,'notifi_type':N_BROADCAST}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_texas_win(redis, uid, nick, vip_exp, poker_type, gold):
        message = {'uid':uid,'nick':nick,'vip_exp':vip_exp,'poker_type':poker_type, 'gold':gold}
        item = {'users':redis.hkeys('online'),'param1':PUSH_TYPE['texas_win'],'param2':message,'notifi_type':N_BROADCAST}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_lottery_win(redis, uid, nick, vip_exp, gold):
        message = {'uid':uid,'nick':nick,'vip_exp':vip_exp, 'gold':gold}
        item = {'users':redis.hkeys('online'),'param1':PUSH_TYPE['lottery_win'],'param2':message,'notifi_type':N_BROADCAST}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_h5_back(redis,uid, message):
        item = {'users':[uid],'param1':PUSH_TYPE['h5_back'],'param2':message,'notifi_type':N_H5}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_h5_create_order(redis,uid, message):
        item = {'users':[uid],'param1':PUSH_TYPE['h5_crate_order'],'param2':message,'notifi_type':N_H5}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def war_robot_chat(table, send_player, message):
        event = create_client_event(ChatEvent)
        event.body.sender = send_player.id
        event.body.table_id = -10
        event.body.chat_type = CHAT_WAR
        event.body.message = message
        event_data = event.encode()
        logging.debug(u'war robot=%d chat now %s,' % (send_player.id, message))
        for uid, is_online in table.service.redis.hgetall("war_online").items():
            uid = int(uid)
            is_online = int(is_online)
            if is_online != 1:
                continue

            if table.players.has_key(uid):
                player = table.players[uid]

                if player.access_service == -1:
                    # service.table.manager.robot_talk_notify(event)
                    pass
                else:
                    access_service = table.service.redis.hget("online",uid)
                    if access_service == None:
                        continue
                    access_service = int(access_service)
                    user = int(uid)
                    table.service.send_client_event(access_service,user,event.header.command,event_data)

    @staticmethod
    def broadcast_charge_rank(redis, message):
        item = {'users':redis.hkeys('online'),'param1':PUSH_TYPE['sys_broadcast'],'param2':message,'notifi_type':N_BROADCAST}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_notify_charge(redis, uid, param1, param2):
        item = {'users':[uid],'param1':param1,'param2':param2,'notifi_type':N_CHARGE}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def broadcast_change_vip(redis, uid, user_nick, vip_exp):
        item = {'users':redis.hkeys('online'),'param1':2,'param2':{'uid':uid,'nick':user_nick,'vip_exp':vip_exp},'notifi_type':N_BROADCAST}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def broadcast_type(redis, p1, p2):
        item = {'users':redis.hkeys('online'),'param1':p1,'param2':p2,'notifi_type':N_BROADCAST}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_notify_friend_apply(redis, user):
        item = {'users':[user],'param1':0,'param2':0,'notifi_type':N_FRIEND_APPLY}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_notify_mail(redis, user):
        item = {'users':[user],'param1':0,'param2':0,'notifi_type':N_MAIL}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_notify_reward(redis, user):
        item = {'users':[user],'param1':0,'param2':0,'notifi_type':N_REWARD}
        redis.lpush('notification_queue', json.dumps(item))
    @staticmethod
    def push_exp_upgrade(redis, user):
        item = {'users':[user],'param1':0,'param2':0,'notifi_type':N_EXP_UPGRADE}
        redis.lpush('notification_queue', json.dumps(item))
    @staticmethod
    def push_notify_broadcast(redis, msg):
        p2 = {'message':msg}
        item = {'users':redis.hkeys('online'),'param1':PUSH_TYPE['sys_broadcast'],'param2':p2,'notifi_type':N_BROADCAST}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def push_message(redis,users,p1,p2,notifi_type = N_BROADCAST):
        item = {'users':users,'param1':p1,'param2':p2,'notifi_type':notifi_type}
        redis.lpush('notification_queue', json.dumps(item))

    @staticmethod
    def send_mail(session, user_info, task_id, **kwargs):

        # 加入邮件日志，待用户下次启动拉取
        mail = TMail()
        mail.from_user = 10000
        mail.to_user = user_info if type(user_info) == int else user_info.id
        mail.sent_time = int(time.time())
        mail.title = kwargs.get('title')
        mail.content = kwargs.get('content')
        mail.type = kwargs.get('type')
        mail.diamond = kwargs.get('diamond',0)
        mail.gold = kwargs.get('gold',0)
        mail.flow_card = kwargs.get('flow_card',0)
        mail.items = kwargs.get('items')
        mail.gifts = kwargs.get('gifts')
        mail.received_time = kwargs.get('received_time')
        mail.state = 0 # 0 = 未收取
        session.add(mail)
