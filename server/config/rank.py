# -*- coding: utf-8 -*-
__author__ = 'Administrator'

# 定时任务，充值榜显示人数
RANK_GOLD_TOP = 1000
RANK_CHARGE_TOP_INDEX = 50
RANK_MAKE_MONEY_TOP_INDEX = 50

RANK_WEALTH_TOP = 10
ZRANK_GOLD_TOP = 9
RANK_WEALTH_REWARD = 10

RANK_CHARGE_TOP = 10
RANK_CHARGE_REWARD = 10
RANK_CHARGE_MAIL = u'恭喜你在 %s 充值排行中，获得第%d名的好成绩，获得如下奖励:%d个钻石'
RANK_MAKE_MONEY_TOP = 10
RANK_MAKE_MONEY_REWARD = 10
RANK_MAKE_MONEY_MAIL = u'恭喜你在赚金排行中，获得第%d名的好成绩，获得如下奖励:%d个钻石'
RANK_FAKE_LEN = 20

RANK_WAR_TOP = 10
RANK_WAR_REWARD = 10
RANK_WAR_MAIL = U'恭喜你在 %s 红黑赢利排行中，获得第%d名的好成绩，获得如下奖励:%d个金币'

RANK_TEXAS_TOP = 10
RANK_TEXAS_MAIL = U'恭喜你在 %s 德州赚金榜排行中，获得第%d名的好成绩，获得如下奖励:%d个钻石'


# 充值的钱与充值榜的钻石奖励换算关系
RANK_CHARGE_RATE = 3

RANK_FAKE_CHARGE_ENABLE = False
RANK_FAKE_CHARGE = [
    {'vip_exp': 501,'id':1,'uid':5120,'nick':'haha1','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':3,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 160,'id':2,'uid':5220,'nick':'haha2','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':6,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 227,'id':3,'uid':5320,'nick':'haha3','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':4,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 220,'id':4,'uid':5420,'nick':'haha4','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':3,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 180,'id':5,'uid':5520,'nick':'haha5','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':2,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 197,'id':6,'uid':5620,'nick':'haha6','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':1,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 221,'id':7,'uid':5720,'nick':'haha7','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':2,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 222,'id':8,'uid':5820,'nick':'haha8','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':1,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 223,'id':9,'uid':5920,'nick':'haha9','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':1,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 226,'id':10,'uid':5020,'nick':'haha10','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':2,'rank_reward':'','charm':0,'money_maked':0},
]


RANK_FAKE_MAKE_MONEYD_ENABLE = False
RANK_FAKE_MAKE_MONEYD = [
    {'vip_exp': 501,'id':1,'uid':5120,'nick':'haha1','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':3,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 160,'id':2,'uid':5220,'nick':'haha2','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':6,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 227,'id':3,'uid':5320,'nick':'haha3','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':4,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 220,'id':4,'uid':5420,'nick':'haha4','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':3,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 180,'id':5,'uid':5520,'nick':'haha5','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':2,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 197,'id':6,'uid':5620,'nick':'haha6','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':1,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 221,'id':7,'uid':5720,'nick':'haha7','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':2,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 222,'id':8,'uid':5820,'nick':'haha8','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':1,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 223,'id':9,'uid':5920,'nick':'haha9','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':1,'rank_reward':'','charm':0,'money_maked':0},
    {'vip_exp': 226,'id':10,'uid':5020,'nick':'haha10','avatar':'http://192.168.2.75:5000/static/upload/10023_867356020226898_tmp_avatar.png','gold':100,'vip':2,'rank_reward':'','charm':0,'money_maked':0},
]

RANK_MAKE_MONEY_REWARD_CONF = (100,150,100,30,25,20,10,10,10,10)

