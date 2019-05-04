# -*- coding: utf-8 -*-
import collections
import json

__author__ = 'Administrator'

import random
import time
import traceback
import gevent
import logging
from sqlalchemy import and_
from activity.robot_uids import robot_all_uids

import os,sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db.activity_user import *
from db.activity_wheel_log import *
from db.user import *
from hall.messagemanager import MessageManager
from helper.encryhelper import md5_encry

class ActivityManager:

    def __init__(self, session, dal, r):
        self.session = session
        self.dal = dal
        self.r = r

    def get_param_val(self, uid, key, val):
        activity_user = self.load_activity_user(uid)
        user_params = self.prase_activity_params(activity_user.params)
        if key in user_params:
            return user_params[key]
        else:
            return None

    def load_activity_user(self, uid):
        return self.session.query(TActivityUser).filter(TActivityUser.uid == uid).first()

    def prase_activity_params(self, str_params):
        result = None
        try:
            result = json.loads(str_params)
        except ValueError as e:
            return None
        finally:
            pass
        return result

    def load_user(self, uid):
        return self.session.query(TUser).filter(TUser.id == uid).first()

    def save_params(self, uid, params):
        self.session.query(TActivityUser).filter(TActivityUser.uid == uid).update({
            TActivityUser.params : params
        })

    def save_user_info(self, user_info):
        # self.dal.save_user(self.session, user_info)
        self.session.query(TUser).filter(TUser.id == user_info.id).update({
            TUser.gold:user_info.gold,
            TUser.diamond:user_info.diamond,
            TUser.flow_card:user_info.flow_card,
        })
        self.dal.get_user(user_info.id, True)

    def save_user_code(self, unique_user_code):
        self.r.rpush('activity_wheel_code',unique_user_code)


    def save_game_result(self, activity_game):
        user_info = activity_game.user_info
        params = json.dumps(activity_game.params)
        unique_user_code = activity_game.unique_user_code

        self.save_params(user_info.id, params)
        self.save_user_info(user_info)
        self.save_user_code(unique_user_code)

    def get_handle(self, params_key, uid):
        user_info = self.dal.get_user(uid)
        if user_info == None:
            return False, {'code':-1,'msg':u'当前用户不存在，请重新登录','ext':{}}

        activity_user = self.load_activity_user(uid)
        if activity_user == None:
            return False, {'code':-1,'msg':u'当前用户配置信息不存在，请检查','ext':{}}

        user_params = self.prase_activity_params(activity_user.params)
        if user_params == None:
            return False, {'code':-1, 'msg':u'活动参数配置错误，请联系管理人员','ext':{}}

        return True, HANDLER_MAP[params_key](user_info, user_params)  #{'wheel':{'play_count':3}}

class Wheel:
    def __init__(self, user_info, params):
        self.user_info = user_info
        self.params = params
        self.unique_user_code = None
        self.result = None

    def can_play(self):
        return int(self.params['wheel']['play_count']) > 0

    def minus_count(self, count):
        self.params['wheel']['play_count'] = self.params['wheel']['play_count']  - count

    def handle(self):
        # 1.用户抽奖并给用户加相关的奖品
        lucky_item = get_trophy()
        # print 'before:',self.user_info.gold,self.user_info.diamond,self.user_info.flow_card
        old_val = getattr(self.user_info,lucky_item[3])
        # print 'old',self.user_info.id,lucky_item[3],old_val
        new_val = old_val + lucky_item[1]
        # print 'new_val+',old_val,lucky_item[1],new_val
        setattr(self.user_info, lucky_item[3], new_val)
        # print 'set new_val=',lucky_item[3],new_val
        self.result = lucky_item
        # print self.result
        # print 'after:',self.user_info.gold,self.user_info.diamond,self.user_info.flow_card


        # 2.减去用的抽奖可用次数
        self.minus_count(1)

        # 3.返回md5（用户id+当前时间戳秒数+用户昵称）
        # unique_user_code = md5_encry(str(self.user_info.id)+str(int(time.time()))+str(random.randint(10000,99999)))
        # self.unique_user_code = unique_user_code+'_'+str(self.user_info.id)+'_'+str(self.user_info.channel)
        unique_user_code = str(self.user_info.id)+'_'+str(self.user_info.channel)
        self.unique_user_code = unique_user_code
        return unique_user_code
    
def robot_wheel_queue(r):
    session = None
    while True:
        if random.choice([1,2]) > 1:

            robot_table = random.choice(['robot','robot_war'])
            uid = random.choice(robot_all_uids)
            r.rpush('activity_wheel_code', uid+'_robot')
        gevent.sleep(random.randint(3,5))



def listen_wheel_queue(r, dal):
    session = None
    while True:
        try:
            code_len = r.llen('activity_wheel_code')
            wheel_info = json.loads(r.get('activity_wheel_info'))
            logging.info(u'检测中：code_len=%d,wheel_len=%d' % (code_len, int(wheel_info['wheel_len'])))
            # 1.验证用户id队列长度 >= 本期活动完成值
            if code_len >= int(wheel_info['wheel_len']):
                logging.info(u'开奖：code_len=%d,wheel_len=%d' % (code_len, int(wheel_info['wheel_len'])))
                session = Session()
                session.begin()
                codes = r.lrange('activity_wheel_code', 0, int(wheel_info['wheel_len']))
                lucky_code = random.choice(codes)
                suid,channel = lucky_code.split('_')
                lucky_uid = int(suid)
                logging.info(u'选择中奖人：%d，总参与人数=%d' % (lucky_uid, len(codes)))

                # 给中奖用户给予中奖活动宝物
                # user_info = dal.get_user(lucky_uid, True)
                # old_val = getattr(user_info,wheel_info['val_type'])
                # new_val = old_val + int(wheel_info['val'])
                # setattr(user_info, wheel_info['val_type'], new_val)
                # user_info.nick = user_info.nick.decode('utf-8') if isinstance(user_info.nick, str) else user_info.nick
                # user_info.sign = user_info.sign.decode('utf-8') if isinstance(user_info.sign, str) else user_info.sign
                # dal.save_user(session, user_info)

                if wheel_info['val_type'] == 'diamond':
                    diamond = wheel_info['val']
                    gold = 0
                    flow_card = 0
                elif wheel_info['val_type'] == 'gold':
                    diamond = 0
                    gold = wheel_info['val']
                    flow_card = 0
                elif wheel_info['val_type'] == 'flow_card':
                    diamond = 0
                    gold = 0
                    flow_card = wheel_info['val']

                logging.info(u'给用户奖励：%s,%s, %s' % (wheel_info['val_type'], wheel_info['val'], wheel_info['val_type_name']))

                # 设置用户投注记录中
                log = TActivityWheelLog()
                log.uid = lucky_uid
                log.round = wheel_info['round']
                log.reward_item = str(wheel_info['val'])+wheel_info['val_type_name'].encode('utf-8')
                log.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
                session.add(log)

                # 给参与活动的所有用户（排除掉机器人）发邮件
                unique_users = set([])
                for code in codes:
                    tmp_uid,tmp_channel = code.split('_')
                    if tmp_channel != 'robot':
                        unique_users.add( int(tmp_uid) )

                for unique_uid in unique_users:
                    if unique_uid == lucky_uid:
                        MessageManager.send_mail(session, lucky_uid, 0,
                                             title=u'幸运转盘',
                                             content=u'恭喜您，在第%d期幸运转轮活动中，运气爆棚，喜获 %d %s' % (wheel_info['round'],wheel_info['val'],wheel_info['val_type_name']),
                                             type=1,
                                             gold=gold,
                                             diamond=diamond,
                                             flow_card=flow_card)

                    else:
                        MessageManager.send_mail(session, unique_uid, 0,
                                             title=u'幸运转盘',
                                             content=u'很遗憾，您参加的第%d期幸运转轮活动中未中奖。' % (wheel_info['round']),
                                             type=0)

                # 将参与的所有用户移除队列
                r.ltrim('activity_wheel_code', int(wheel_info['wheel_len']), -1)

                # 生成新的一期宝物
                incr_id = r.incr('activity_wheel_round')
                treasure = random.choice(TREASURE_CONF)
                treasure_info = json.dumps({'round':incr_id,'val':treasure[2],'val_type':treasure[1], 'wheel_len':treasure[0],'val_type_name':treasure[3]})
                r.set('activity_wheel_info', treasure_info)
                logging.info(u'生成新一期宝物信息：%s' % treasure_info)
                session.commit()
        except Exception as e:
            traceback.print_exc()
        finally:
            if session !=None:
                session.close()
                session = None
        gevent.sleep(3)


def get_trophy():
    lists = []
    for index, trophy in enumerate(REWARD_TROPHY):
        lists += trophy[0] * [trophy[2]]
    lucky_item = random.choice(lists)

    for x in REWARD_TROPHY:
        if x[2] == lucky_item:
            return x

# 中奖记录：(中奖索引，数值，类型)
REWARD_TROPHY = (
    # (0,0,'IPhone 8'),
    (30,400000,'gold_400000','gold',u'金币'),
    (20,40,'diamond_40','diamond',u'钻石'),
    (20,500000, 'gold_500000','gold',u'金币'),
    (10,150, 'flow_card_150','flow_card',u'流量卡'),
    (20,600000,'gold_600000','gold',u'金币')
)

ACTIVITY_USER_CONF = {"wheel": {"play_count": 0}}

HANDLER_MAP = {
    'wheel':Wheel
}

TREASURE_CONF = [
    (100, 'gold', 1000000,u'金币'),
    (200, 'gold', 2000000,u'金币'),
    (300, 'gold', 3000000,u'金币'),
    (400, 'gold', 4000000,u'金币'),
    (500, 'gold', 5000000,u'金币'),
    (100, 'diamond', 100,u'钻石'),
    (200, 'diamond', 200,u'钻石'),
    (300, 'diamond', 300,u'钻石'),
    (400, 'diamond', 400,u'钻石'),
    (500, 'diamond', 500,u'钻石'),
]




if __name__ == '__main__':
    import redis
    from db.connect import *
    from dal.core import *
    from util.commonutil import *
    session = Session()
    set_context('session', session)
    r = redis.Redis(password='Wgc@123456', db=2)
    dal = DataAccess(r)

    robot_wheel_queue(r)
    # listen_wheel_queue(None, session, r, dal)
