# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from proto.constant_pb2 import *

# 总计时：暂定28s,加上计算时间1s，29s
START_GAME_TIME = 3
ROUND_TIME = 15
ACTION_LOOP_DURATION = 10
END_GAME_TIME = 0
RESTART_TIME = 8


TABLE_GAME_CONF = (
    20000, # 最低投注额
    20,    # 最近局数
    20,    # 最近走势长度
    7,     # 富豪榜前几名
    0.02,  # 抽税
    8,     # 幸运一击对子起步
    0.4,   # 奖池开奖第一名分配额
    300,   # 超时被踢时限
    3,     # 机器人奖池开奖倍率'
    8,     # 开奖延时秒数
    1000000000, # 奖池最大值 ，注意，已弃用
    2000000000, # 库存最大值，注意，已弃用
    3,          # 开奖前几名
    50,         # 加假的总人数，开奖时在开奖人数上加上该值的一般
    (2000000,10000000),         # 机器人增加金币区间
    100000000, # 最高下注总额
)

LUCK_PUNCH_CONF = {
    P_BAOZI:16,
    P_TONGHUASHUN:11,
    P_TONGHUA:5,
    P_SHUN:4,
    P_DUI:3,
}
def get_luck_reward(poker):
    # 获得幸运牌型的奖的数据
    if poker.is_baozi():
        return LUCK_PUNCH_CONF[P_BAOZI]
    elif poker.is_tonghuashun():
        return LUCK_PUNCH_CONF[P_TONGHUASHUN]
    elif poker.is_tonghua():
        return LUCK_PUNCH_CONF[P_TONGHUA]
    elif poker.is_shun():
        return LUCK_PUNCH_CONF[P_SHUN]
    elif poker.is_dui():
        if poker[1].value > TABLE_GAME_CONF[5]:
            return LUCK_PUNCH_CONF[P_DUI]
    return LUCK_PUNCH_CONF[P_DAN]

def get_tax(gold):
    if gold <= 100000000: # <1亿时，70~90%的金币放入奖池
        return 70, 90
    elif gold > 100000000 and gold <= 500000000: # 金币<5亿时，60%~80%的金币放入奖池
        return 60, 80
    else:                  # >5亿时，50%~70%的金币放入奖池
        return 50, 70

def pool_fee_rate(tax_fee):
    pool_rate = ()
    if tax_fee <= 100000000: # <1亿时，70~90%的金币放入奖池
        pool_rate = 70, 90
    elif tax_fee > 100000000 and tax_fee <= 500000000: # 金币<5亿时，60%~80%的金币放入奖池
        pool_rate = 60, 80
    else:                  # >5亿时，50%~70%的金币放入奖池
        pool_rate = 50, 70
    return pool_rate

POKER_REWARD_CONF = [
    # A金花5~5%；顺金6~6%；豹子7~8%；地龙9~10%
    {P_TONGHUA:(5,5), P_TONGHUASHUN:(6,6),P_BAOZI:(7,8), P_352:(9, 10)},
    # A金花11~12%；顺金13~14%；豹子15~17%；地龙18~20%
    {P_TONGHUA:(11,12), P_TONGHUASHUN:(13,14),P_BAOZI:(15,17), P_352:(18, 20)},
    # A金花21~12%；顺金23~24%；豹子25~27%；地龙28~30%
    {P_TONGHUA:(21,22), P_TONGHUASHUN:(23,24),P_BAOZI:(25,27), P_352:(28, 30)},
    # A金花31~32%；顺金33~34%；豹子35~37%；地龙38~40%
    {P_TONGHUA:(31,32), P_TONGHUASHUN:(33,34),P_BAOZI:(35,37), P_352:(38, 40)},
    # A金花41~42%；顺金43~44%；豹子45~47%；地龙48~50%
    {P_TONGHUA:(41,42), P_TONGHUASHUN:(43,44),P_BAOZI:(45,47), P_352:(48, 50)},
    # A金花51~52%；顺金53~54%；豹子55~57%；地龙58~60%
    {P_TONGHUA:(51,52), P_TONGHUASHUN:(53,54),P_BAOZI:(55,57), P_352:(58, 60)},
]
def get_reward_range(gold, poker_type):
    if gold <= 100000000:
        return POKER_REWARD_CONF[0].get(poker_type)
    elif gold > 100000000 and gold <= 200000000:
        return POKER_REWARD_CONF[1].get(poker_type)
    elif gold > 200000000 and gold <= 300000000:
        return POKER_REWARD_CONF[2].get(poker_type)
    elif gold > 300000000 and gold <= 400000000:
        return POKER_REWARD_CONF[3].get(poker_type)
    elif gold > 400000000 and gold <= 500000000:
        return POKER_REWARD_CONF[4].get(poker_type)
    else:
        return POKER_REWARD_CONF[5].get(poker_type)

def odds_calc(is_lucky, player_poker):
    if is_lucky:
        return 1

    if player_poker.is_dan():
        return 1
    elif player_poker.is_dui():
        if dui_gt_8(player_poker.pokers):
            return 2
        return 1
    elif player_poker.is_shun():
        return 3
    elif player_poker.is_tonghua():
        return 4
    elif player_poker.is_tonghuashun():
        return 10
    elif player_poker.is_baozi():
        return 15
    elif player_poker.is_352():
        return 1

def is_dui_gt_8(player_poker):
    if player_poker.is_dui():
        if player_poker.pokers[0].value >= 8 and player_poker.pokers[1].value >= 8 \
            or player_poker.pokers[1].value >= 8 and player_poker.pokers[2].value >= 8 \
            or player_poker.pokers[0].value >= 8 and player_poker.pokers[2].value >= 8:
            return True
    return False

def is_dui_lt_8(player_poker):
    if player_poker.is_dui():
        if player_poker.pokers[0].value == 1 or player_poker.pokers[1].value == 1 or player_poker.pokers[2].value == 1:
                return False
        if player_poker.pokers[0].value < 8 and player_poker.pokers[1].value < 8 \
                or player_poker.pokers[1].value < 8 and player_poker.pokers[2].value < 8 \
                or player_poker.pokers[0].value < 8 and player_poker.pokers[2].value < 8:
            return True
    return False

def is_dui_a(player_poker):
    if player_poker.is_dui():
        if player_poker.pokers[0].value == 1 and player_poker.pokers[1].value == 1 \
                or player_poker.pokers[1].value == 1 and player_poker.pokers[2].value == 1 \
                or player_poker.pokers[0].value == 1 and player_poker.pokers[2].value == 1:
            return True
    return False