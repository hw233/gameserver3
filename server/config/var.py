#coding: utf-8
import time
import random
from datetime import time as dt_time
from datetime import date as dt_date
from proto.constant_pb2 import *



DEBUG                       = True
UNIT_TEST                   = False

FIX_ENV_HALL = False
FIX_ENV_HALL_USERS = [11260,11254]
FIX_ENV_WAR = False
FIX_ENV_WAR_USERS = [11260,11254]

#http://api.chanzor.com/send?account=wanggouchao&password=153457&mobile=13480879974&content=%E6%B5%8B%E8%AF%95%E9%AA%8C%E8%AF%81%E7%A0%81%EF%BC%9A4321%E3%80%90%E7%BD%91%E8%B4%AD%E6%BD%AE%E3%80%91
SMS_CONF={
    'zc_sms':{
        'account':'wanggouchao',
        'password':'153457',
    },
    'url':"http://api.chanzor.com/send",
    'sign':'【网购潮科技】',
    'tpl':'您的短信验证码是@如非本人操作，请忽略此短信。本短信免费。',
    'exp':60,
}

MAIL_TEMPLATE = {
	1:u'魅力值增加，+%d',
	2:u'魅力值减少，-%d',
	3:u'同意您的好友申请，并添加您为好友',
	4:u'已拒绝您的好友申请',
	5:u'出售金币成功',
	6:u'恭喜到达活动要求',
	7:u'获得%d个喇叭，赶快去吼一嗓子吧',
	8:u'获得%d个钻石，赶快去背包里看看吧',
    9:u'点击领取使用',
}

REGISTER_FAST_LOGIN_KEY = '@cardgame123'
REGISTER_NICK_COLOR = 'FF0066'
BORADCAST_CHANGE_NAME = 1
BORADCAST_SEND_CHAT = 7

DEFAULT_USER={
    'avatar':[''],
    'sign':u'这家伙很懒，什么也没留下。',
    'nick':[u'游客',u'来宾',u'赌客'],
    'nick_num':["%04d",(0, 9999)],
    'gold':20000,
    'diamond':0,
    'vip':0,
    'money':0,
    'charm':0,
    'birthday':dt_date(2000,1,1),
    'sex':0,
    'is_charge':0,
    'vip_exp':0,
    'default_item':(1,0),
    'flow_card':0,
}

DEFAULT_USER_GLODFLOWER ={
    'exp':0,
    'win_games':0,
    'total_games':0,
    'best':'',
    'wealth_rank':0,
    'win_rank':0,
    'charm_rank':0,
    'charge_rank':0,
    'max_bank':0,
    'max_items':0,
    'max_gifts':0,
    'signin_days':-1,
    'last_signin_day':dt_date(2000,1,1),
    'oneline_time':0,
    'login_times':0,
    'change_nick':-1,
}

PRM_SIGN_LUCK_DAYS = [7,14,21,28]
PRM_CHANGE_NAME_MINUS_DIAMOND = 100
PRM_MAX_DEVICE_ID = 15
PRM_MAX_PASSWORD_LEN = 15
PRM_MIN_PASSWORD_LEN = 6

SYS_MAX_SIGN_DAY = 7

STATE_IS_SHOW = 0
STATE_NO_ACCEPT_REWARD = 1
STATE_ACCEPT_REWARD = 0
STATE_NEED_POPUP = 0
STATE_DISABLED = -1
STATE_ENABLE = 0

TRANSFER_GOLD_LOW = 100000
TRANSFER_GOLD_FEE = 0.05
TRANSFER_AUTH_LEVEL = 2


TAX_NUM = 0.05 # 金币交易，税率



NO_KICK_LEVEL = 6   # 被踢的人在vip6及以上等级有免踢权限
BUY_GOLD_LEVEL = 1  # vip1及以上才可以购买金币
SELL_GOLD_LEVEL = 3 # vip3及以上等级可在金币交易中出售金币

# 系统提醒时间
NOTI_TIME = 300
NOTI_TIME_2 = 180
	# optional int32 id = 1;
	# required int32 money = 2;
	# required int32 diamond = 3;
	# required int32 gold = 4;
	# required int32 hore = 5;
	# required int32 kicking_card = 6;
	# required int32 vip_card = 7;
PASS_ENCRY_STR = 'cqkj2017'

# 出售金币时，兑换的钻石 / 金币 = 比率（乘以位数）
SELL_RATE = 10000

# 每日全场任务完成，赠送钻石脚本区间
DT_ALL_DIAMOND = (1,10)
# 每日全场任务完成，赠送流量卷区间
DT_ALL_FLOW = (0,0)

# 系统推送消息类型
PUSH_TYPE ={
    'new_user_register':1,
    'vip_upgrade':2,
    'table_winner':3,
    'send_gift':4,
    'sys_broadcast':5,
    'gold_trade':6,
    'world_horn':7,
    'luck_poker':8,
    'rank_top':9,
    'charge_success':10,
    'fix_broadcast':12,
    'war_change_rich':22,
    'war_top1':21,
    'h5_back':31,
    'h5_crate_order':32,
    'texas_win':41,
    'lottery_win':42,
    'vip_login':13,
}

# **************************************充值**************************************************************
# 快冲
QUICK_CHARGE = [
    # 分，万(gold)，商品名称
    # (500, 16, u'16万金币',500),
    # (900, 35, u'35万金币',900),
    # (3900, 180, u'180万金币',3900),
    # (16900, 1000, u'1000万金币',16900),
    (500, 16, u'16万金币',1),
    (900, 35, u'35万金币',1),
    (3900, 180, u'180万金币',1),
    (16900, 1000, u'1000万金币',1),
    (2000, 80, u'80万金币',1),
    (800, 30, u'30万金币',1),
]

# 首冲
FRIST_CHARGE = {
    'title':u'首充大礼包',
    'money' : 300,
    'real_money':1,
    'diamond' : 10,
    'gold' : 20, # 单位w
    'hore' : 10,
    'kicking_card':10,
    'vip_card' :1,
    'items':'1-10,2-10,4-1'
}
# ******************************* emotion ****************************************
EMOTION_ONCE_GOLD = 1000

# ******************************* flow ****************************************
FLOW_NOSEND = -2 # 没发送
FLOW_ACCEPT = 1  # 已接受，订货中
FLOW_FAILD = -1  # 回调结束，订货失败
FLOW_SUCCESS = 0 # 回调结束，订货成功

FlOW_CHANNEL_CODE = '20176137'  # 渠道
FLOW_KEY = 'uumon6299@$#'  # 秘钥
FLOW_URL = 'http://uumon.com/api/v2/egame/flow/package/order.json'


# ******************************* web *****************************************
# web服务器配置
WEB_HOST = '0.0.0.0'
WEB_PORT = 8000

# 活动网页地址
ACTIVITY_URL = 'http://zjh.wgchao.com:18080/activity'
# 活动网页地址
ACTIVITY_CREATE_URL = 'http://zjh.wgchao.com:18080/activity/create_order'
# 活动网页地址
ACTIVITY_BACK_URL = 'http://zjh.wgchao.com:18080/activity/back'
# 活动网页地址
ACTIVITY_PLAY = {
    'wheel':'http://zjh.wgchao.com:18080/wheel/play'
}
# 第三方支付的回调
PAY_CALLBACK = 'http://zjh.wgchao.com:18080/pay_result'
# 第三方支付的回调
PAY_CALLBACK_NEW = 'http://zjh.wgchao.com:18080/pay_result_new'
# 与客户端的秘钥
CHARGE_KEY = 'cqkj2017'
# 给第三方支付的秘钥
# CP_KEY = 'bde25760c1556899efc0dff13bf41b4e' # test
CP_KEY = 'd5ff856beccf4c472831c3f16c376e28' # product
# avatar头像上传地址
UPDATE_AVATAR_URL = 'http://zjh.wgchao.com:18080/avatar'
# 更新文件上传地址
UPGRADE_URL = 'http://zjh.wgchao.com:18080/web/static/upgrade/'
# 网页使用redis，充值时提醒用户
WEB_REDIS = {'host':'localhost','port':6379,'db':0,'password':'Wgc@123456'}
# 定时任务redis
CROND_REDIS = {'host':'localhost','port':6379,'db':0,'password':'Wgc@123456'}
