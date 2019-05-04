# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import gevent
from gevent import monkey;

monkey.patch_all()
from gevent import lock
from gevent.queue import Queue

import logging
import traceback
import time
import sys
import os
import random
import copy

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import and_

from proto import war_pb2 as pb2
from proto.constant_pb2 import *

from task.dailytask import *
from message.resultdef import *
from wartable.gameconf import *
from wartable.eventsender import *
from db.war_award_log import *
from db.war_log import *
from db.rank_war_top import *
from db.war_player_log import *
from goldflower import game as goldflower


class WarGame:
    def __init__(self, table):

        self.table = table
        self.state = -1  # 0:进行中，1：结算中，-1：等待、初始化
        self.sender = GameEventSender(self.table, self)

        self.red_chips = {}
        self.black_chips = {}
        self.lucky_chips = {}

        self.other_chips = {}
        self.others_win_gold = 0

        # self.fee = TABLE_GAME_CONF[4]
        self.player_actions = {}
        self.player_result = {}
        self.big_winner = {} # {'uid':12123:'gold':30000}
        # self.big_win_gold = 0
        self.top_winners = []
        self.war_id = -1

        # self.lucky_rate = 1

        self.remain_time = 0

        self.red_total = 0
        self.black_total = 0
        self.lucky_total = 0
        self.robot_manager = None

        self.real_red_total = 0
        self.real_black_total = 0
        self.real_lucky_total = 0
        self.result_gold = 0

    def is_robot(self, uid):
        if self.robot_manager == None:
            return False
        return self.robot_manager.is_robot(uid)

    def start(self):

        logging.info('start_game...' + str(self.state))
        robots_total = 0
        users_total = 0
        for x in self.table.players.values():
            if x.access_service == -1:
                robots_total += 1
            else:
                users_total += 1
        logging.info(u'users-[%d] , robots-[%d]' % (users_total, robots_total,))
        self.table.lock.acquire()
        logging.info(u'start acquire')
        try:
            for uid, player in self.table.players.items():
                if player.access_service == -1:
                    if self.table.is_online_robot(uid):
                        '''
                        机器人在线直接初始化新的用户数据
                     '''
                        self.table.players[uid].reward_gold = 0
                        self.player_result[uid] = PlayerResult(uid)
                        self.player_result[uid].gold = player.get_gold()
                    else:
                        self.table.redis.hdel('war_online', uid)
                        del self.table.players[uid]
                    continue

                if self.table.players[uid].offline_time != 0 and int(time.time()) - self.table.players[
                    uid].offline_time > 30:
                    '''
                    真实用户离线超过30秒的时候，就设置用户为离线状态
                  '''
                    self.table.players[uid].set_online(self.table.redis, 0)
                        # self.table.redis.hdel('war_online', uid)
                        # del self.table.players[uid]
                elif int(self.table.redis.hget('war_online', uid)) == 0:
                    '''
                    用户退出了红黑大战，就删除掉用户的信息
                    如果该用户是上榜用户，就保留一局
                  '''
                    if self.table.rank.is_lucky(uid) or self.table.rank.is_rich(uid):
                        if not self.table.players[uid].is_exit:
                            logging.info(u'用户退出了红黑大战，就删除掉用户的信息 if %d' % uid)
                            self.table.players[uid].reward_gold = 0
                            self.table.players[uid].is_exit = True
                            self.player_result[uid] = PlayerResult(uid)
                            self.player_result[uid].gold = player.get_gold()
                        else:
                            logging.info(u'用户退出了红黑大战，就删除掉用户的信息 else %d' % uid)
                            self.table.redis.hdel('war_online', uid)
                            del self.table.players[uid]
                    else:
                        logging.info(u'用户退出了红黑大战，就删除掉用户的信息 not rich %d' % uid)
                        self.table.redis.hdel('war_online', uid)
                        del self.table.players[uid]
                else:
                    '''
                    用户任然在红黑牌局中，初始化新的用户数据
                  '''
                    logging.info(u'用户任然在红黑牌局中，初始化新的用户数据 %d' % uid)
                    self.table.players[uid].reward_gold = 0
                    self.player_result[uid] = PlayerResult(uid)
                    self.player_result[uid].gold = player.get_gold()
            self.state = 0
            self.remain_time = ROUND_TIME + START_GAME_TIME
            self.sender.send_game_started()
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()
            logging.info(u'start release')

        gevent.sleep(START_GAME_TIME)

    def action(self):
        logging.info('action start ....' + str(self.state))
        begin = int(time.time())
        last_time = time.time()

        while (time.time() - begin) <= ROUND_TIME:
            self.remain_time = ROUND_TIME - (time.time() - begin)
            logging.info('action...' + str(self.remain_time))
            if len(self.other_chips) > 0:
                self.sender.send_bet_other()
                logging.info(u'action=未上榜用户投注：红方=%d，黑方=%d，幸运一击=%d', self.red_total, self.black_total, self.lucky_total)
            gevent.sleep(ACTION_LOOP_DURATION / float(10))

    def over(self):
        logging.info(u'over lock')
        self.table.lock.acquire()
        try:
            self.state = 1

            logging.info(u'over-1-end_game ...game-state：')
            logging.info(u'over-2-当前用户总投注：红方=%d，黑方=%d，幸运一击=%d' % (self.red_total, self.black_total, self.lucky_total))
            logging.info(u'over-3-当前真实用户总投注：红方=%d，黑方=%d，幸运一击=%d' % (self.real_red_total, self.real_black_total, self.real_lucky_total))

            self.table.reward_pool.init()
            self.table.poker_maker.init()

            logging.info(u'poker_maker.init()函数生成poker列表:' + str(self.table.poker_maker.poker_result))
            logging.info(u'winner:%s,poker_type:%d,winner_poker:%s' % (self.table.poker_maker.poker_result.winner,
                                                                        self.table.poker_maker.poker_result.winner_poker_type,
                                                                        self.table.poker_maker.poker_result.winner_poker))

            logging.info(u'结算开始：奖池-%d，库存-%d' % (self.table.reward_pool.gold, self.table.reward_pool.stack))
            # self.table.lock.acquire()
            try:
                # 遍历投注了的用户，设置每个用户的投注结果
                for uid, actions in self.player_actions.items():
                    self.set_player(uid, actions)
            finally:
                # self.table.lock.release()
                pass
            logging.info(u'结算结束：奖池-%d，库存-%d' % (self.table.reward_pool.gold, self.table.reward_pool.stack))

            logging.info(u'奖励开始：奖池-%d，库存-%d' % (self.table.reward_pool.gold, self.table.reward_pool.stack))
            self.table.reward_pool.reward()
            logging.info(u'奖励结束：奖池-%d，库存-%d' % (self.table.reward_pool.gold, self.table.reward_pool.stack))

            self.table.game_log.save_game()

            self.table.rank.init()
            self.sender.game_over()

            self.reward_box()
            logging.info(u'结果发事件结束')
            logging.info(u'排行：幸运星-%d，财富榜-%s' % (self.table.rank.lucky_player.uid if self.table.rank.lucky_player == int else 0, str([x.uid for x in self.table.rank.rich_players[:TABLE_GAME_CONF[3]]])))


        finally:
            self.table.lock.release()
            logging.info(u'over release')
        logging.info(u'保存结果结束')

        gevent.sleep(END_GAME_TIME + self.table.reward_pool.last_reward_time)

    def reward_box(self):
        for uid, player_result in self.player_result.items():
            if uid in self.table.players:
                player = self.table.players[uid]
                if player.access_service != -1 and player.get_gold() < 2000000 and player_result.bet_gold > 0:
                    if player_result.real_win_gold > 0:
                        gevent.spawn_later(8, player.check_reward_box, self.table.service, self.table.redis, 1)
                    else:
                        gevent.spawn_later(8, player.check_reward_box, self.table.service, self.table.redis, -1)
		    
                    logging.info(u'宝箱，uid=%d，次数=%s, rewal_win_gold=%d,bet_gold=%d' % (uid, player.play_result_counter,player_result.real_win_gold,player_result.bet_gold))

    def set_player(self, uid, actions):
        # logging.info(u'uid: %d,actions: %s' % (uid, str(actions))) 64763
        player_result = self.player_result[uid]
        for action in actions:
            player_result.bet_gold += action.gold  # 4000  60763

            if action.action_type == 0:
                player_result.lucky_bet += action.gold  # 2000
            else:
                player_result.red_black_bet += action.gold # 2000

            if action.action_type in self.table.poker_maker.poker_result.win_types:
                # player_result.principal += action.gold # 60000
                if action.action_type == 0:
                    win_lucky_gold = action.get_rate_gold(self.table.poker_maker.poker_result.lucky_rate)
                    player_result.win_gold += win_lucky_gold # +80000
                    player_result.lucky_bet_win += win_lucky_gold # 80000
                    player_result.principal_lucky += action.gold
                    if self.table.players[uid].access_service != -1:
                        self.table.reward_pool.minus_stack(win_lucky_gold)
                    logging.info(u'用户%d投中幸运一击，获得幸运一击金币：%d' % (uid, win_lucky_gold))

                    # self.player_result[uid].win_gold += win_lucky_gold
                    # self.player_result[uid].real_win_gold += win_lucky_gold - action.gold
                else:
                    player_result.principal_red_black += action.gold
                    player_result.win_gold += action.gold * 2  # 12000
                    player_result.red_black_bet_win += action.gold * 2  # 4000

                # logging.info(u'用户-%d，投-%d，金币数-%d，赢得-%d' % (uid, action.action_type,action.gold, self.player_result[uid].win_gold))

            # self.player_result[uid].bet_gold += action.gold
        # if player_result.win_gold > 0:
        self.win_tax(player_result)

    def win_tax(self, player_result):

        luck_real_win_gold, luck_tax_fee, luck_tax_real_fee = self.table.reward_pool.tax(player_result.lucky_bet_win - player_result.principal_lucky)
        red_black_real_win_gold ,red_black_tax_fee,red_black_real_fee = self.table.reward_pool.tax(player_result.red_black_bet_win - player_result.principal_red_black)

        # real_win_gold, tax_fee = self.table.reward_pool.tax(player_result.win_gold - player_result.principal)
        player_result.real_win_gold = luck_real_win_gold + red_black_real_win_gold # 7840
        player_result.fee = luck_tax_fee + red_black_tax_fee
        player_result.real_fee = luck_tax_real_fee + red_black_real_fee
        player_result.principal = player_result.principal_lucky + player_result.principal_red_black
        # logging.info(u'用户扣税：%d，真实赢钱：%d' % (tax_fee, real_win_gold))
        if self.table.players[player_result.uid].access_service != -1:
            logging.debug(u'1用户投注幸运一击赢得 %d，税费 %d' % (luck_real_win_gold, luck_tax_fee))
            logging.debug(u'2用户投注红黑赢得 %d，税费 %d' % (red_black_real_win_gold, red_black_tax_fee))
            logging.debug(u'3用户总赢钱 %d，总税费 %d，用户命中的总本金 %d' % (player_result.real_win_gold, player_result.fee,player_result.principal))
        self.save_player_gold(player_result)

    def save_player_gold(self, player_result):
        # player_result = self.player_result[uid]

        if self.table.rank.is_lucky(player_result.uid) or self.table.rank.is_rich(player_result.uid):
            pass
        else:
            self.others_win_gold += player_result.win_gold
            # logging.info(u'非榜上人员+钱，others_win_gold：%d' % self.others_win_gold)

        player = self.table.players[player_result.uid]
        player.plus_gold(self.table, player_result.real_win_gold + player_result.principal)
        player.save_player_brief(self.table, player_result.uid, player_result.win_gold)
        player.save_player_rank(self.table, player_result.uid, player_result.real_win_gold)

        player_result.set_gold(player)
        player.brief_log(self.table, player.uid)

        player.add_player_result(player_result)
        player.save_recent()
        if player.access_service != -1:
            self.calc_result_gold(player_result.bet_gold, player_result.win_gold)
            DailyTaskManager(self.table.redis).bet_wartable(player.uid)
        self.set_big_winner(player_result)

    def set_big_winner(self, player_result):
        if not self.big_winner.has_key('uid'):
            self.big_winner = {'uid': player_result.uid, 'win_gold': player_result.win_gold}
            return

        if player_result.win_gold > self.big_winner.get('win_gold', 0):
            self.big_winner = {'uid': player_result.uid, 'win_gold': player_result.win_gold}
            return

        if player_result.win_gold == self.big_winner.get('win_gold', 0):
            if cmp(self.table.players[player_result.uid].recent_bet_gold,
                   self.table.players[self.big_winner.get('uid')].recent_bet_gold) > 0:
                self.big_winner = {'uid': player_result.uid, 'win_gold': player_result.win_gold}

    def bet(self, player, action_type, gold):
        action = PlayerAction(action_type, gold)
        if self.player_actions.has_key(player.uid):
            self.player_actions[player.uid].append(action)
        else:
            self.player_actions[player.uid] = [action]

        if action_type == 1:
            self.red_total += gold
            if player.access_service != -1:
                self.real_red_total += gold
        elif action_type == -1:
            self.black_total += gold
            if player.access_service != -1:
                self.real_black_total += gold
        else:
            self.lucky_total += gold
            if player.access_service != -1:
                self.table.reward_pool.add_stack_gold(gold)
                self.real_lucky_total += gold

        player.minus_gold(self.table, int(gold))
        if self.table.rank.is_lucky(player.uid) or self.table.rank.is_rich(player.uid):
            self.sender.send_bet(player, action)
        else:
            WarGame.log_user_bet(action_type, gold, self.other_chips)

        if player.access_service != -1:
            logging.info(u'bet-(%d)用户%d投注：牌桌=%d ，金额=%d，剩余金币=%d' % (player.access_service,player.uid, action_type, -gold, player.gold))

        return 0

    def save_player_rank(self, table, uid, win_gold):
        # table.lock.acquire()
        session = table.get_session()
        try:
            session.query(TRankWarTop).filter(and_(TRankWarTop.uid == uid, TRankWarTop.add_date == time.strftime('%Y-%m-%d'))).update({
                TRankWarTop.total: TRankWarTop.total + win_gold
            })
        finally:
            table.close_session(session)
            # table.lock.release()

    def get_over_proto_struct(self, pb):
        logging.debug(u'player_result: %s' % str(self.player_result.keys()))
        self.table.poker_maker.poker_result.get_proto_struct(pb.result)
        pb.result.lucky_rate = self.table.poker_maker.poker_result.lucky_rate

        pb.result.reward_gold = int(self.table.reward_pool.gold)
        pb.result.result = self.table.poker_maker.poker_result.winner
        pb.result.other_gold = self.others_win_gold

        for index in range(len(self.top_winners)):
            self.top_winners[index].get_proto_struct(pb.result.top3_winners.add())

        for uid in self.table.rank.get_last_rank():
            self.player_result[uid].get_proto_struct(pb.result.player_results.add())

        return pb

    def bet_action_proto_struct(self, player, player_action, pb):
        pb.player = player.uid
        pb.action_type = player_action.action_type
        pb.chip.gold = player_action.gold
        pb.bet_gold = sum([x.gold for x in self.player_actions[player.uid]])
        pb.gold = int(player.get_gold())
        return pb

    def is_running(self):
        # 状态：0:进行中，1：结算中，-1：等待、初始化
        if self.state == 0:
            return True
        return False

    def get_other_proto_struct(self, pb_table):

        for type, bets in self.other_chips.items():
            for gold, countof in bets.items():
                if gold <= 0:
                    continue
                if type > 0:
                    if gold > 0:
                        pb2_red = pb_table.red_chips.add()
                        pb2_red.gold = gold
                        pb2_red.countof = countof
                elif type < 0:
                    if gold > 0:
                        pb2_black = pb_table.black_chips.add()
                        pb2_black.gold = gold
                        pb2_black.countof = countof
                else:
                    if gold > 0:
                        pb2_lucky = pb_table.lucky_chips.add()
                        pb2_lucky.gold = gold
                        pb2_lucky.countof = countof
        self.other_chips = {}

    def get_chips_proto_struct(self, pb_table):
        """
        当前牌桌筹码数据
        :param pb_table:
        :return:
        """
        for gold, count in self.red_chips.values():
            pb_red_chip = pb_table.chips.red_chips.add()
            pb_red_chip.gold += gold * count

        for gold, count in self.black_chips.values():
            pb_block_chip = pb_table.chips.black_chips.add()
            pb_block_chip.gold += gold * count

        for gold, count in self.lucky_chips.values():
            pb_lucky_chip = pb_table.chips.lucky_chips.add()
            pb_lucky_chip.gold += gold * count

        return pb_table

    def calc_result_gold(self, bet, win):
        self.result_gold += bet - win

    def get_bet_winner_users(self, winner):
        users = set()
        for uid, actions in self.player_actions.items():
            for action in actions:
                if action.action_type == winner:
                    users.add(uid)
                    break
        return users

    @staticmethod
    def log_user_bet(uid, gold, rows):
        if rows.has_key(uid):
            if rows[uid].has_key(gold):
                rows[uid][gold] += 1
            else:
                rows[uid][gold] = 1
        else:
            rows[uid] = {gold: 1}


class PokerMaker:
    def __init__(self, table):

        self.table = table
        self.red_morethan_88 = 0
        self.black_morethan_88 = 0

        self.pokers_17 = []
        self.random_poker = []
        self.pokers = []

        self.poker_result = None

    def init(self):
        self.pokers_17 = []        # 新的17副牌的数据
        self.random_poker = []     # 随机选出的两幅牌列表
        self.pokers = []           # 最终选出的两幅牌列表
        self.poker_result = None   # 最终的牌结果对象

        self.create_poker()        # 初始化，选择一对随机的牌
        self.check_352()           # 验证随机牌中是否有352的牌型
        self.poker_result = PokerResult(self.get_winner(), self.pokers)   # 设置牌的结果对象

    def check_352(self):
        if self.pokers[0].is_352() and not self.pokers[1].is_baozi():
            if self.pokers[0].is_tonghua():
                self.pokers[0].poker_type = P_TONGHUA
            else:
                self.pokers[0].poker_type = P_DAN
            self.pokers.sort(cmp=lambda x, y: x.compare(y), reverse=True)
            return

        if self.pokers[1].is_352() and not self.pokers[0].is_baozi():
            if self.pokers[1].is_tonghua():
                self.pokers[1].poker_type = P_TONGHUA
            else:
                self.pokers[1].poker_type = P_DAN
            self.pokers.sort(cmp=lambda x, y: x.compare(y), reverse=True)

    def get_winner(self):
        # red_rate, black_rate = self.get_rate()
        red_rate, black_rate = self.get_new_rate(self.get_new_fix_rate())
        if self.table.check_round_rate():
            logging.info(u'互换比例-前：red：%f，black：%f' % (red_rate, black_rate))
            red_rate, black_rate = black_rate, red_rate
            logging.info(u'互换比例-后：red：%f，black：%f' % (red_rate, black_rate))
        logging.info(u'最终比例：red：%f，black：%f' % (red_rate, black_rate))
        b = [1 for i in range(int(red_rate * 100))]
        win_list = b + [-1 for i in range(int(black_rate * 100))]

        return random.choice(win_list)


    def get_new_rate(self, new_fix_rate):
        red_rate = 0.5
        black_rate = 0.5
        if self.table.game.real_red_total == 0 and self.table.game.real_black_total == 0:
            logging.info(u'both eq 0, return 0.5,0.5')
            return red_rate,black_rate
        if self.table.game.real_red_total == self.table.game.real_black_total:
            logging.info(u'both eq, return 0.5,0.5')
            return red_rate,black_rate

        if self.table.game.real_red_total > 0 and self.table.game.real_black_total == 0:
            black_rate += new_fix_rate
            red_rate -= new_fix_rate
            logging.info(u'real_red_total > real_black_total, return %f,%f' % (red_rate,black_rate))
            return red_rate, black_rate
        if self.table.game.real_black_total > 0 and self.table.game.real_red_total == 0:
            black_rate -= new_fix_rate
            red_rate += new_fix_rate
            logging.info(u'real_red_total >0 and > real_black_total, return %f,%f ' % (red_rate,black_rate))
            return red_rate, black_rate

        if self.table.game.real_red_total > self.table.game.real_black_total:
            black_rate += new_fix_rate
            red_rate -= new_fix_rate
            logging.info(u'real_red_total > real_black_total, return  %f, %f ' % (red_rate,black_rate))
            return red_rate, black_rate
        if self.table.game.real_red_total < self.table.game.real_black_total:
            red_rate += new_fix_rate
            black_rate -= new_fix_rate
            logging.info(u'real_red_total < real_black_total, return  %f, %f ' % (red_rate,black_rate))
            return red_rate, black_rate
        return red_rate,black_rate

    def get_new_fix_rate(self):
        # self.table.lock.acquire()
        logging.debug(u'get_fix_rate acquire')
        session = self.table.get_session()
        try:
            fix_rate = 0
            result_gold = session.query(TWarLog.result_gold).order_by(TWarLog.id.desc()).limit(1000).all()
            if 0 > sum([x[0] for x in result_gold]):
                fix_rate = 0.08
                return fix_rate
            if 0 > sum([x[0] for x in result_gold[:100]]):
                fix_rate = 0.06
                return fix_rate
            if 0 > sum([x[0] for x in result_gold[:20]]):
                fix_rate = 0.04
                return fix_rate

            fix_rate = 0.02
            return fix_rate
        finally:
            logging.info(u'查询获得战局比例fix_rate：%f' % fix_rate)
            self.table.close_session(session)
            # self.table.lock.release()
            logging.debug(u'get_fix_rate release')

    def create_poker(self):
        # self.init_poker()
        # self.random_poker.append(self.pokers_17[0])
        # self.random_poker.append(self.pokers_17[1])
        # self.pokers = self.random_poker
        # return
        # if random.randint(1,2) > 1:
        #     self.random_poker.append( goldflower.PlayerPokers(-1, Poker(1,11),Poker(1,5),Poker(1,1)) )
        #     self.random_poker.append( goldflower.PlayerPokers(-1, Poker(2,3),Poker(2,5),Poker(2,2)) )
        #     self.pokers = self.random_poker
        #     return
        stack_gold = self.table.reward_pool.stack
        while True:
            self.init_poker()
            self.random_choice_poker()
            logging.debug(u'初次选择牌型：%s' % self.random_poker)
            if self.is_poker_draw(self.random_poker[0], self.random_poker[1]):
                logging.info(u'出现平局，重新选牌 %s', str(self.random_poker))
                continue

            # self.pokers_17.append( goldflower.PlayerPokers(-1, Poker(1, 3), Poker(2, 1), Poker(3, 5)) )
            # self.pokers_17.append( goldflower.PlayerPokers(-1, Poker(1, 8), Poker(2, 8), Poker(3, 5)) )
            # self.table.continuous_lucky_round = 5
            if self.table.is_continuous_unlucky():
                if self.table.game.real_lucky_total * 4 < stack_gold:
                    continuous_lucky_conf = self.table.get_continuous_lucky_round()
                    choice_poker = self.get_lucky_rate(continuous_lucky_conf)
                    if choice_poker > 0:
                        pokers = self.get_choice_poker(choice_poker)
                        if len(pokers) != 2:
                            logging.info(u'连续幸运一击牌型没有拿到，重新选牌')
                            continue
                        else:
                            if self.check_choice_poker(pokers) == False:
                                logging.info(u'连续幸运一击牌型中既没有顺子也没有对8大的牌，重新选牌')
                                continue

                        # 开幸运一击了，重新设置累计幸运一击数值
                        self.table.continuous_lucky_round = 0
                        logging.info(u'连续幸运一击开奖，连续局数=%d，对8大牌型(%d)，顺子(%d)，选择胜方(%d)' % (self.table.continuous_lucky_round,\
                                                                                    continuous_lucky_conf['gt_dui8'],\
                                                                                    continuous_lucky_conf['shun'],\
                                                                                    choice_poker))
                        logging.info(u'连续幸运一击开奖，poker结果,p1=%s,p2=%s' % (self.pokers[0],self.pokers[1]))
                        return
                    else:
                        self.table.incr_continuous_unlucky()
                        logging.info(u'当前17副牌型中不存在对8大和顺子，不开幸运一击连续局数：%d' % self.table.continuous_lucky_round)
                else:
                    self.table.incr_continuous_unlucky()
                    logging.info(u'真实用户投注*4倍小于库存，不开幸运一击连续局数：%d' % self.table.continuous_lucky_round)
            else:
                self.table.incr_continuous_unlucky()
                logging.info(u'5局以内，不开幸运一击连续局数：%d' % self.table.continuous_lucky_round)



            if self.table.game.real_lucky_total == 0:
                self.pokers = self.random_poker
                logging.info(u'暂无真实用户投注，直接返回随机牌型，p1(%d): %s, p2(%d): %s' % (
                self.random_poker[0].poker_type, self.random_poker[0], self.random_poker[1].poker_type,
                self.random_poker[1]))
                return

            if stack_gold <= 0:
                if self.is_lt_dui8(self.random_poker[0]) and self.is_lt_dui8(self.random_poker[1]):
                    self.pokers = self.random_poker
                    logging.info(u'stack_gold小于0,stack_gold: %d' % stack_gold)
                    logging.info(u'选取的random poker比对8小，p1: %s, p2: %s' % (self.random_poker[0], self.random_poker[1]))
                    return
                else:
                    logging.info(u'原有的牌，比对8大，重新选择比对8小的牌，p1: %s, p2: %s' % (self.random_poker[0], self.random_poker[1]))
                    poker1, poker2 = self.get_lt_dui8()
                    if self.is_lt_dui8(poker1) and self.is_lt_dui8(poker2):
                        self.random_poker = [poker1, poker2]
                        self.pokers = self.random_poker
                        logging.info(
                            u'重新选择后，random poker比对8小，p1: %s, p2: %s' % (self.random_poker[0], self.random_poker[1]))
                        return
                    else:
                        logging.info(u'重新选择还是比对8大，p1: %s, p2: %s' % (self.random_poker[0], self.random_poker[1]))
                        logging.info(u'重新选牌###############')
                        continue

            logging.info(u'库存数大于0，stack_gold:%d' % stack_gold)
            logging.info(u'选取的random poker比对8大或库存>0，p1: %s, p2: %s' % (self.random_poker[0], self.random_poker[1]))
            logging.info(
                u'poker_type,p1:%s, p2: %s' % (self.random_poker[0].poker_type, self.random_poker[1].poker_type))

            if self.table.game.real_lucky_total * 16 <= stack_gold:
                logging.info(u'用户投注16倍，无所谓牌型，直接返回 total:%d, stack:%d' % (self.table.game.real_lucky_total, stack_gold))
                self.pokers = self.random_poker
                logging.info(u'poker结果：%s' % str(self.random_poker))
                # print u'15 倍率，随便什么牌，直接返回'
                return

            if self.table.game.real_lucky_total * 11 <= stack_gold:
                logging.info(u'用户投注11倍，选取的牌要比豹子小 total:%d, stack:%d' % (self.table.game.real_lucky_total, stack_gold))
                if self.random_poker[0].is_baozi() or self.random_poker[1].is_baozi():
                    poker1, poker2 = self.get_lt_baozi()
                    self.random_poker = []
                    self.random_poker.append(poker1)
                    self.random_poker.append(poker2)
                self.pokers = self.random_poker
                logging.info(u'poker结果：%s' % str(self.random_poker))
                # print u'用户投注10倍，选取的牌要比豹子小 '
                return

            if self.table.game.real_lucky_total * 5 <= stack_gold:
                logging.info(u'用户投注5倍，选取的牌要比顺金小 total:%d, stack:%d' % (self.table.game.real_lucky_total, stack_gold))
                if self.random_poker[0].is_baozi() or self.random_poker[1].is_baozi() \
                        or self.random_poker[0].is_tonghuashun() or self.random_poker[1].is_tonghuashun():
                    poker1, poker2 = self.get_lt_tonghuashun_baozi()
                    self.random_poker = []
                    self.random_poker.append(poker1)
                    self.random_poker.append(poker2)
                self.pokers = self.random_poker
                logging.info(u'poker结果：%s' % str(self.random_poker))
                # print u'用户投注4倍，选取的牌要比顺金小'
                return

            if self.table.game.real_lucky_total * 4 <= stack_gold:
                logging.info(u'用户投注4倍，选取的牌要比金花小 total:%d, stack:%d' % (self.table.game.real_lucky_total, stack_gold))
                if self.random_poker[0].is_baozi() or self.random_poker[1].is_baozi() \
                        or self.random_poker[0].is_tonghuashun() or self.random_poker[1].is_tonghuashun() \
                        or self.random_poker[0].is_tonghua() or self.random_poker[1].is_tonghua():
                    poker1, poker2 = self.get_lt_tonghuashun_baozi_tonghua()
                    self.random_poker = []
                    self.random_poker.append(poker1)
                    self.random_poker.append(poker2)
                self.pokers = self.random_poker
                logging.info(u'poker结果：%s' % str(self.random_poker))
                # print u'用户投注3倍，选取的牌要比金花小'
                return

            if self.table.game.real_lucky_total * 3 <= stack_gold:
                logging.info(u'用户投注3倍，选取的牌要比顺子小 total:%d, stack:%d' % (self.table.game.real_lucky_total, stack_gold))
                if self.random_poker[0].is_baozi() or self.random_poker[1].is_baozi() \
                        or self.random_poker[0].is_tonghuashun() or self.random_poker[1].is_tonghuashun() \
                        or self.random_poker[0].is_tonghua() or self.random_poker[1].is_tonghua() \
                        or self.random_poker[0].is_shun() or self.random_poker[1].is_shun():
                    poker1, poker2 = self.get_lt_tonghuashun_baozi_tonghua_shun()
                    self.random_poker = []
                    self.random_poker.append(poker1)
                    self.random_poker.append(poker2)
                self.pokers = self.random_poker
                logging.info(u'poker结果：%s' % str(self.random_poker))
                # print u'用户投注2倍，选取的牌要比顺子小'
                return

            if self.table.game.real_lucky_total * 3 > stack_gold:
                logging.info(
                    u'用户投注3倍大于库存，只能返回比对8小的牌 total:%d, stack:%d' % (self.table.game.real_lucky_total, stack_gold))
                poker1, poker2 = self.get_lt_tonghuashun_baozi_tonghua_shun_ltdui8()
                self.random_poker = []
                self.random_poker.append(poker1)
                self.random_poker.append(poker2)
                self.pokers = self.random_poker
                logging.info(u'poker结果：%s,p1:%d,p2:%d' % (
                str(self.random_poker), self.pokers[0].poker_type, self.pokers[1].poker_type))
                return
    def check_choice_poker(self, pokers):
        if pokers[0].is_shun():
            self.pokers = pokers[:]
            return True
        elif pokers[1].is_shun():
            self.pokers[0] = pokers[1]
            self.pokers[1] = pokers[0]
            return True
        elif PokerMaker.is_dui_gt_8(pokers[0]):
            self.pokers = pokers[:]
            return True
        elif PokerMaker.is_dui_gt_8(pokers[1]):
            self.pokers[0] = pokers[1]
            self.pokers[1] = pokers[0]
            return True
        return False

    def get_choice_poker(self, choice_poker):
        pokers = []
        if choice_poker == 1:
            pokers.append(self.get_gt_dui_8())
        elif choice_poker == 2:
            pokers.append(self.get_shun())
        if len(pokers) < 2:
            pokers.append(self.get_lt_dui8_and_dan())
        return pokers

    def get_lucky_rate(self, poker_type_rate):
        poker_rate = []
        if self.has_gt_dui8():
            poker_rate = [1 for _ in range(poker_type_rate['gt_dui8'])]
        if self.has_shun():
            poker_rate += [2 for _ in range(poker_type_rate['shun'])]
        if len(poker_rate) < 100:
            poker_rate += [-1 for _ in range(100 - len(poker_rate))]
        random.shuffle(poker_rate)
        choice_poker = random.choice(poker_rate)
        return choice_poker

    def has_gt_dui8(self):
        for poker in self.pokers_17:
            if PokerMaker.is_dui_gt_8(poker):
                return True
        return False

    def has_shun(self):
        if P_SHUN in [x.poker_type for x in self.pokers_17]:
            return True

    def get_lt_baozi(self):
        poker1 = None
        poker2 = None
        poker2s = []
        for poker in self.pokers_17:
            if poker.poker_type == P_TONGHUASHUN:
                poker2s.append(poker)
            elif poker.poker_type == P_TONGHUA:
                poker2s.append(poker)
            elif poker.poker_type == P_SHUN:
                poker2s.append(poker)
            elif poker.poker_type == P_DUI:
                poker2s.append(poker)
            elif poker.poker_type == P_DAN:
                poker2s.append(poker)
        idx = random.randint(0, len(poker2s) - 1)
        poker1 = poker2s[idx]
        poker2s.pop(idx)
        idx = random.randint(0, len(poker2s) - 1)
        poker2 = poker2s[idx]
        poker2s.pop(idx)
        return poker1, poker2

    def get_lt_tonghuashun_baozi(self):
        poker1 = None
        poker2 = None
        poker2s = []
        for poker in self.pokers_17:
            if poker.poker_type == P_TONGHUA:
                poker2s.append(poker)
            elif poker.poker_type == P_SHUN:
                poker2s.append(poker)
            elif poker.poker_type == P_DUI:
                poker2s.append(poker)
            elif poker.poker_type == P_DAN:
                poker2s.append(poker)
        idx = random.randint(0, len(poker2s) - 1)
        poker1 = poker2s[idx]
        poker2s.pop(idx)
        idx = random.randint(0, len(poker2s) - 1)
        poker2 = poker2s[idx]
        poker2s.pop(idx)
        return poker1, poker2

    def get_lt_tonghuashun_baozi_tonghua(self):
        poker1 = None
        poker2 = None
        poker2s = []
        for poker in self.pokers_17:
            if poker.poker_type == P_SHUN:
                poker2s.append(poker)
            elif poker.poker_type == P_DUI:
                poker2s.append(poker)
            elif poker.poker_type == P_DAN:
                poker2s.append(poker)
        idx = random.randint(0, len(poker2s) - 1)
        poker1 = poker2s[idx]
        poker2s.pop(idx)
        idx = random.randint(0, len(poker2s) - 1)
        poker2 = poker2s[idx]
        poker2s.pop(idx)
        return poker1, poker2


    def get_lt_tonghuashun_baozi_tonghua_shun(self):
        poker1 = None
        poker2 = None
        poker2s = []
        for poker in self.pokers_17:
            if poker.poker_type == P_DUI:
                poker2s.append(poker)
            elif poker.poker_type == P_DAN:
                poker2s.append(poker)
        idx = random.randint(0, len(poker2s) - 1)
        poker1 = poker2s[idx]
        poker2s.pop(idx)
        idx = random.randint(0, len(poker2s) - 1)
        poker2 = poker2s[idx]
        poker2s.pop(idx)
        return poker1, poker2

    def get_lt_tonghuashun_baozi_tonghua_shun_ltdui8(self):
        poker1 = None
        poker2 = None
        poker2s = []
        for poker in self.pokers_17:
            if PokerMaker.is_dui_lt_8(poker):
                poker2s.append(poker)
            elif poker.poker_type == P_DAN:
                poker2s.append(poker)
        idx = random.randint(0, len(poker2s) - 1)
        poker1 = poker2s[idx]
        poker2s.pop(idx)
        idx = random.randint(0, len(poker2s) - 1)
        poker2 = poker2s[idx]
        poker2s.pop(idx)
        return poker1, poker2

    def get_lt_dui8(self):
        poker1 = None
        poker2 = None
        pokers = []
        for poker in self.pokers_17:
            if self.is_lt_dui8(poker):
                pokers.append(poker)

        idx = random.randint(0, len(pokers) - 1)
        poker1 = pokers[idx]
        pokers.pop(idx)
        idx = random.randint(0, len(pokers) - 1)
        poker2 = pokers[idx]
        pokers.pop(idx)
        return poker1, poker2

    def is_lt_dui8(self, poker):
        if poker.poker_type == P_DAN:
            return True
        if PokerMaker.is_dui_lt_8(poker):
            return True
        return False

    def is_poker_draw(self, poker1, poker2):
        if poker1.poker_type == poker2.poker_type:
            poker2_value = [x.value for x in poker2.pokers]
            if poker1.pokers[0].value in poker2_value \
                    and poker1.pokers[1].value in poker2_value \
                    and poker2.pokers[2].value in poker2_value:
                return True
        return False

    def init_poker(self):
        pokers = []
        for flower in xrange(1, 5):
            for value in xrange(1, 14):
                pokers.append(Poker(flower, value))

        while len(pokers) >= 3:
            poker1 = random.choice(pokers)
            pokers.remove(poker1)
            poker2 = random.choice(pokers)
            pokers.remove(poker2)
            poker3 = random.choice(pokers)
            pokers.remove(poker3)
            p = goldflower.PlayerPokers(-1, poker1, poker2, poker3)
            self.pokers_17.append(p)

        self.pokers_17.sort(cmp=lambda x, y: x.compare(y), reverse=True)

    def random_choice_poker_backup(self):
        self.random_poker = []
        idx = random.randint(0, len(self.pokers_17) - 1)
        self.random_poker.append(self.pokers_17[idx])
        self.pokers_17.pop(idx)
        poker_2_len = idx + random.randint(2, 5)
        if poker_2_len <= len(self.pokers_17) - 1:
            self.random_poker.append( self.pokers_17[poker_2_len] )
            self.pokers_17.pop(poker_2_len)
        else:
            idx = random.randint(0, len(self.pokers_17) - 1)
            self.random_poker.append(self.pokers_17[idx])
            self.pokers_17.pop(idx)
        # self.random_poker.append(self.pokers_17[0])
        # self.random_poker.append(self.pokers_17[1])
        self.random_poker.sort(cmp=lambda x, y: x.compare(y), reverse=True)

    def random_choice_poker(self):
        self.random_poker = []
        p1 = random.choice(self.pokers_17)
        self.random_poker.append(p1)
        self.pokers_17.remove(p1)

        p2 = random.choice(self.pokers_17)
        self.random_poker.append(p2)
        self.pokers_17.remove(p2)

        self.random_poker.sort(cmp=lambda x, y: x.compare(y), reverse=True)

    def get_gt_dui_8(self):
        for index, poker in enumerate(self.pokers_17):
            if PokerMaker.is_dui_gt_8(poker):
                self.pokers_17.pop(index)
                return poker
        return None


    def get_shun(self):
        for index,poker in enumerate(self.pokers_17):
            if poker.is_shun() and not poker.is_tonghua():
                self.pokers_17.pop(index)
                return poker
        return None

    def get_lt_dui8_and_dan(self):
        choice_pokers = self.pokers_17[:]
        random.shuffle(choice_pokers)
        for index,poker in enumerate(choice_pokers):
            if self.is_lt_dui8(poker):
                self.pokers_17.pop(index)
                return poker
        return None

    @staticmethod
    def is_dui_lt_8(poker):
        if poker.is_dui() and poker.poker_type == P_DUI:
            if poker.pokers[0].value == 1 or poker.pokers[1].value == 1 or poker.pokers[2].value == 1:
                return False
            if poker.pokers[0].value < 8 and poker.pokers[1].value < 8 \
                    or poker.pokers[1].value < 8 and poker.pokers[2].value < 8 \
                    or poker.pokers[0].value < 8 and poker.pokers[2].value < 8:
                return True
        return False

    @staticmethod
    def is_dui_gt_8(poker):
        if poker.is_baozi():
            return False
        if poker.is_dui():
            if poker.pokers[0].value == 1 and poker.pokers[1].value == 1 \
                    or poker.pokers[1].value == 1 and poker.pokers[2].value == 1 \
                    or poker.pokers[0].value == 1 and poker.pokers[2].value == 1:
                return True
            if poker.pokers[0].value >= 8 and poker.pokers[1].value >= 8 \
                    or poker.pokers[1].value >= 8 and poker.pokers[2].value >= 8 \
                    or poker.pokers[0].value >= 8 and poker.pokers[2].value >= 8:
                return True
        return False


class PokerResult:
    def __init__(self, winner, pokers):
        self.winner = None
        self.winner_poker = None
        self.winner_poker_type = None

        self.red_poker = None
        self.black_poker = None

        self.lucky_rate = 1
        self.win_types = []
        self.init(winner, pokers)

    def init(self, winner, pokers):
        self.winner = winner
        self.set_pokers(pokers)
        self.set_lucky_rate()
        self.set_win_type()

    def set_pokers(self, pokers):
        pokers.sort(cmp=lambda x, y: x.compare(y), reverse=True)
        if self.winner > 0:
            self.red_poker = pokers[0]
            self.black_poker = pokers[1]
        else:
            self.black_poker = pokers[0]
            self.red_poker = pokers[1]

        self.winner_poker = pokers[0]
        self.winner_poker_type = pokers[0].poker_type

    def set_lucky_rate(self):
        if self.winner_poker_type == P_DUI:
            if PokerMaker.is_dui_gt_8(self.winner_poker):
                self.lucky_rate = LUCK_PUNCH_CONF.get(self.winner_poker_type, 1)
            else:
                self.lucky_rate = 1
        elif self.winner_poker_type == P_DAN:
            self.lucky_rate = 1
        else:
            self.lucky_rate = LUCK_PUNCH_CONF.get(self.winner_poker_type, 1)

            # self.is_winner_lucky_poker(self.winner_poker)

    def set_win_type(self):
        if self.is_reward():
            self.win_types = [self.winner, 0]
        else:
            self.win_types = [self.winner]
        logging.info(u'赢牌方结果：%s, lucky_rate=%d' % (str(self.win_types), self.lucky_rate))

    def is_reward(self):
        logging.info(u'验证赔率，当前赔率：%d' % self.lucky_rate)
        if self.lucky_rate > 1:
            return True
        return False

    def is_tonghua_A(self):
        if 1 in [x.value for x in self.winner_poker.pokers]:  # 必须为A金花
            return True
        return False

    def get_proto_struct(self, pb_result):
        if PokerMaker.is_dui_gt_8(self.red_poker):
            pb_result.red_morethan_88 = 1
        random.shuffle(self.red_poker.pokers)
        for p in self.red_poker.pokers:
            pb_poker = pb_result.red_pokers.add()
            pb_poker.flower = p.flower
            pb_poker.value = p.value
        pb_result.red_poker_type = self.red_poker.poker_type

        if PokerMaker.is_dui_gt_8(self.black_poker):
            pb_result.black_morethan_88 = 1
        random.shuffle(self.black_poker.pokers)
        for p in self.black_poker.pokers:
            pb_poker = pb_result.black_pokers.add()
            pb_poker.flower = p.flower
            pb_poker.value = p.value
        pb_result.black_poker_type = self.black_poker.poker_type



    def is_winner_lucky_poker(self, poker):
        if poker.is_baozi():
            self.is_lucky = True
        if poker.is_tonghua():
            self.is_lucky = True
        if poker.is_shun():
            self.is_lucky = True
        if poker.is_tonghuashun():
            self.is_lucky = True
        if poker.is_352():
            self.is_lucky = True
        if PokerMaker.is_dui_gt_8(poker):
            self.is_lucky = True

    def __repr__(self):
        return 'red(%d):%s, black(%d):%s' % (
        self.red_poker.poker_type, self.red_poker.pokers, self.black_poker.poker_type, self.black_poker.pokers)


class Poker:
    def __init__(self, flower, value):
        self.flower = flower
        self.value = value

    def __eq__(self, other):
        return self.flower == other.flower and self.value == other.value

    def __repr__(self):
        return "%d-%d" % (self.flower, self.value,)

    def get_proto_struct(self, pb_poker=None):
        if pb_poker == None:
            pb_poker = pb2.Poker()
        pb_poker.flower = self.flower
        pb_poker.value = self.value
        return pb_poker


class Rank:
    def __init__(self, table):
        self.table = table
        self.lucky_player = 0
        self.rich_players = []

        self.top_players = []

    def init(self):
        self.top_players = []
        self.reload_lucky()
        self.reload_richs()

    def get_last_rank(self):
        last_rank = []
        if self.lucky_player != 0:
            last_rank.append(self.lucky_player.uid)
        if len(self.rich_players) > 0:
            last_rank += [x.uid for x in self.rich_players[:TABLE_GAME_CONF[3]]]

        print 'last_rank:##########################',last_rank
        return last_rank

    def reload_lucky(self):
        self.lucky_player = 0
        luckys = sorted(self.table.players.values(), cmp=Rank.get_real_lucky, reverse=True)

        for player in luckys:
            if player.access_service == -1:
                try:
                    if self.table.robot_manager.check_robot_online(player.uid):
                        self.lucky_player = player
                        self.lucky_player.seat = -1
                        return self.lucky_player
                except Exception as e:
                    print player.uid
                    print self.table.robot_manager.robots
                    print e.message
                finally:
                    pass
            elif player.online > 0:
                self.lucky_player = player
                self.lucky_player.seat = -1
                return self.lucky_player
        return self.lucky_player

    @staticmethod
    def get_real_lucky(p1, p2):
        win_count_result = cmp(p1.recent_win_games, p2.recent_win_games)
        if win_count_result == 0:
            return cmp(p1.recent_bet_gold, p2.recent_bet_gold)
        return win_count_result

    def reload_richs(self):
        old_rich_player = None
        if len(self.rich_players) > 0:
            old_rich_player = self.rich_players[0]

        self.rich_players = []

        rank_players = sorted(self.table.players.values(), cmp=lambda x, y: cmp(x.recent_bet_gold, y.recent_bet_gold),
                              reverse=True)

        for player in rank_players:
            if player.get_gold() > 0:
                if player.access_service == -1:
                    if self.table.robot_manager.check_robot_online(player.uid):
                        self.rich_players.append(player)
                        self.top_players.append(player)
                elif player.online > 0:
                    self.rich_players.append(player)
                    self.top_players.append(player)

        lucky_index = -1
        for index, player in enumerate(self.rich_players[:21]):
            if player.uid == self.lucky_player.uid:
                lucky_index = index
            player.seat = index
            player.recent_rich_rank = index

        if lucky_index >= 0:
            self.rich_players.pop(lucky_index)

        if old_rich_player != None and len(self.rich_players) > 0:
            if old_rich_player.uid != self.rich_players[0].uid:
                # self.table.lock.acquire()
                try:

                    gevent.spawn_later(13, self.table.broadcast_change_rich, (self.table.players[self.rich_players[0].uid],))

                finally:
                    # self.table.lock.release()
                    pass



        return self.rich_players

    def is_lucky(self, uid):
        if type(self.lucky_player) != int and self.lucky_player.uid == uid:
            return True
        return False

    def is_rich(self, uid):
        ids = [x.uid for x in self.rich_players[:TABLE_GAME_CONF[3]]]
        if self.is_lucky(uid):
            if self.lucky_player.uid in ids:
                ids.remove(self.lucky_player.uid)
        if uid in ids:
            return True
        return False

    def has_lucky(self):
        if type(self.lucky_player) != int and self.lucky_player != 0:
            return True
        return False



class PlayerAction:
    def __init__(self, action_type, gold):
        self.action_type = action_type
        self.gold = gold

    def get_rate_gold(self, rate):
        return self.gold * rate

    def __repr__(self):
        return 'action_type=%d, gold=%d' % (self.action_type, self.gold)


class PlayerResult:
    def __init__(self, uid):
        self.uid = uid
        self.bet_gold = 0
        self.win_gold = 0
        self.fee = 0
        self.gold = 0

        self.reward_gold = 0
        self.real_win_gold = 0

        self.principal = 0
        self.principal_win = 0
        self.principal_lucky = 0
        self.principal_red_black = 0
        self.red_black_bet = 0
        self.red_black_bet_win = 0
        self.lucky_bet = 0
        self.lucky_bet_win = 0
        self.real_fee = 0

    def reload_fields(self):
        self.bet_gold = 0
        self.win_gold = 0
        self.fee = 0
        self.gold = 0

        self.reward_gold = 0
        self.real_win_gold = 0

        self.principal = 0
        self.principal_win = 0
        self.principal_lucky = 0
        self.principal_red_black = 0
        self.red_black_bet = 0
        self.red_black_bet_win = 0
        self.lucky_bet = 0
        self.lucky_bet_win = 0
        self.real_fee = 0

    def set_bet_gold(self, bet_gold):
        self.bet_gold = bet_gold

    def set_win_gold(self, win_gold):
        self.win_gold = win_gold

    def set_real_win_gold(self, real_win_gold):
        self.real_win_gold = real_win_gold

    def set_fee(self, fee):
        self.fee = fee

    def set_gold(self, player):
        self.gold = player.get_gold()

    def set_reward_gold(self, reward_gold):
        self.reward_gold = reward_gold

    def get_proto_struct(self, pb_player_result, player = None, redis = None):
        if pb_player_result == None:
            pb_player_result = war_pb2.WarPlayerGameResult()
        pb_player_result.uid = self.uid
        pb_player_result.bet_gold = int(self.bet_gold)
        pb_player_result.win_gold = int(self.win_gold)
        pb_player_result.fee = int(self.fee)
        if player != None and redis != None:
            user_gold = redis.hget( 'u'+str(self.uid), 'gold')
            if user_gold != None:
                pb_player_result.gold = int(user_gold)
            else:
                pb_player_result.gold = int(self.gold)
        else:
            pb_player_result.gold = int(self.gold)
        pb_player_result.reward_gold = int(self.reward_gold)

    def __repr__(self):
        return 'uid=%d,bet_gold=%d,win_gold=%d,fee=%d,gold=%d,reward_gold=%d,real_win_gold=%d' % \
               (self.uid, self.bet_gold, self.win_gold, self.fee, self.gold, self.reward_gold,self.real_win_gold)


class RewardPool:
    def __init__(self, table):
        self.table = table
        self.game = table.game
        self.rank = table.rank
        self.players = table.players

        self.gold = 0  # 奖池金币

        self.stack = 0
        self.last_reward = None
        self.last_reward_time = 0
        self.records = []

        self.reward_players_log = []
        self.reward_gold = 0
        self.tax_rate = ()

    def init(self):
        self.last_reward_time = 0    # 开奖时延
        self.reward_players_log = [] # 记录当前奖励的用户日志
        self.reward_gold = 0         # 此次奖励的金额
        self.tax_rate = ()           # 此次收税范围
        self.get_tax_rate()          # 设置收税的金额范围
        logging.debug(u'税收范围确定：%d,%d' % (self.tax_rate))

    def get_tax_rate(self):
        if self.gold <= 100000000:  # <1亿时，70~90%的金币放入奖池
            self.tax_rate = 70, 90
        elif self.gold > 100000000 and self.gold <= 500000000:  # 金币<5亿时，60%~80%的金币放入奖池
            self.tax_rate = 60, 80
        else:  # >5亿时，50%~70%的金币放入奖池
            self.tax_rate = 50, 70

    def tax(self, real_win_gold):
        if real_win_gold < 0:
            return 0,0
        tax_fee = float(real_win_gold) * TABLE_GAME_CONF[4]

        tax_pool_gold = tax_fee * (float(random.randint(*self.tax_rate)) / 100)
        # tax_pool_gold = tax_fee * (float(70) / 100)
        # logging.debug(u'收税Before：gold=%d，tax_pool_gold=%s'% (self.gold,tax_pool_gold))
        # if tax_pool_gold > 0:
        #     logging.debug(u'收税Now：gold=%d，tax=%d'% (self.gold, tax_pool_gold))
        self.gold = int(self.gold) + int(tax_pool_gold)
        # logging.debug(u'收税Now：gold=%d，tax=%d'% (self.gold, tax_pool_gold))

        # if self.gold > TABLE_GAME_CONF[10]:
            # self.gold = TABLE_GAME_CONF[10]
        return float(real_win_gold) - tax_fee, tax_fee, tax_pool_gold

    def reward(self):
        winner_poker_type = self.table.poker_maker.poker_result.winner_poker_type
        if winner_poker_type not in (P_352, P_TONGHUA, P_TONGHUASHUN, P_BAOZI):
            return

        if winner_poker_type == P_TONGHUA:
            if not self.table.poker_maker.poker_result.is_tonghua_A():
                return

        if len(self.table.game.player_actions) == 0:
            return

        if self.table.game.lucky_total == 0:
            return

        reward_users = list(self.table.game.get_bet_winner_users(self.table.poker_maker.poker_result.winner))
        if len(reward_users) <= 0:
            return
        # logging.info(u'抽奖开始，当前牌型，%d' % winner_poker_type)
        self.reward_players(winner_poker_type, reward_users)

    def reward_players(self, winner_poker_type, reward_users):
        reward_gold = self.get_reward_gold(winner_poker_type)
        # top_lucky_users = self.get_top_luck_users()

        top1 = self.get_top_one(reward_users)
        if top1 == -1:
            return
        #print 'top1:',top1
        reward_users.remove(top1)
        bet_remain_gold, reward_remain_gold = self.reward_top_one(top1, reward_gold)


        #print 'bet_remain_gold:%d,reward_remain_gold:%d' % (bet_remain_gold,reward_remain_gold)
        for other in reward_users:
            self.reward_other(other, bet_remain_gold, reward_remain_gold)

        self.set_top_winners()

        if reward_gold > 0:
            self.last_reward_time = TABLE_GAME_CONF[9]
        #print '#################################',self.stack,type(self.stack),reward_gold,type(reward_gold)

        self.gold -= reward_gold

        self.reward_gold = reward_gold
        # self.table.game.big_winner = {}

    def get_reward_gold(self, winner_poker_type):
        if self.gold <= 100000000:
            low, hight = POKER_REWARD_CONF[0].get(winner_poker_type)
        elif self.gold > 100000000 and self.gold <= 200000000:
            low, hight = POKER_REWARD_CONF[1].get(winner_poker_type)
        elif self.gold > 200000000 and self.gold <= 300000000:
            low, hight = POKER_REWARD_CONF[2].get(winner_poker_type)
        elif self.gold > 300000000 and self.gold <= 400000000:
            low, hight = POKER_REWARD_CONF[3].get(winner_poker_type)
        elif self.gold > 400000000 and self.gold <= 500000000:
            low, hight = POKER_REWARD_CONF[4].get(winner_poker_type)
        else:
            low, hight = POKER_REWARD_CONF[5].get(winner_poker_type)

        reward_gold = int(self.gold * (float(random.randint(low, hight)) / 100))
        logging.info(u'reward-奖池：奖池金币数=%d,此次奖励金币数=%d' % (self.gold, reward_gold))
        return reward_gold

    def get_top_luck_users(self):
        top_users = []
        if self.rank.has_lucky():
            top_users.append(self.rank.lucky_player.uid)
        top_users += [x.uid for x in self.rank.rich_players[:TABLE_GAME_CONF[3]]]

        top_users = set(top_users)
        top_luck_users = set()
        for uid in top_users:
            if self.table.game.player_actions.has_key(uid) and len(self.table.game.player_actions[uid]) > 0:
                for action in self.table.game.player_actions[uid]:
                    if action.action_type == 0:
                        top_luck_users.add(uid)
                        break

        # logging.info(u'此次投注了幸运一击的用户：%s', str(top_luck_users))
        return top_luck_users

    def get_top_one(self, reward_users):
        robots = []
        top_robots = []
        real_players = []
        top_real_players = []
        for uid in reward_users:
            if self.table.players[uid].access_service == -1:
                robots.append(uid)
                if self.table.rank.is_lucky(uid) or self.table.rank.is_rich(uid):
                    top_robots.append(uid)
            else:
                real_players.append(uid)
                if self.table.rank.is_lucky(uid) or self.table.rank.is_rich(uid):
                    top_real_players.append(uid)

        if len(top_robots) == 0 and len(top_robots) == 0:
            return -1
        
        if len(top_real_players) == 0:
            return random.choice(top_robots)

        if len(top_robots) == 0:
            return random.choice(top_real_players)

        bet_count = robots + real_players
        #logging.info(u'机器人投注幸运一击：%s，真实玩家投注幸运一击：%s' % (str(robots), str(real_players)))

        old_robot_rate, old_real_player_rate = float(len(robots)) / len(bet_count), float(len(real_players)) / len(
            bet_count)
        #print old_robot_rate,old_real_player_rate
        #logging.info(u'得出原始概率：robot-%s,player-%s' % (str(old_robot_rate), str(old_real_player_rate)))

        total_rate = old_robot_rate * TABLE_GAME_CONF[8] + old_real_player_rate

        new_robot_rate, new_real_player_rate = old_robot_rate * TABLE_GAME_CONF[
            8] / total_rate, old_real_player_rate / total_rate
        #logging.info(u'得出机器人倍数新概率，总数-%s，机器人-%s，用户-%s' % (total_rate, new_robot_rate, new_real_player_rate))
        #print new_robot_rate,new_real_player_rate
        rate_list = [-1 for x in range(int(new_robot_rate * 100))]
        rate_list += [1 for x in range(int(new_real_player_rate * 100))]
        #print 'real',len([x for x in rate_list if x > 0])
        #print 'robot',len([x for x in rate_list if x < 0])
        #print rate_list
        random_type = random.choice(rate_list)
        #print random_type
        if random_type > 0:
            player = random.choice(top_real_players)
            #logging.debug(u'top1选出真实用户：uid-%d,gold-%d' % (player, self.table.players[player].get_gold()))
            return player
        else:
            player = random.choice(top_robots)
            #logging.info(u'top1选出机器人用户：uid-%d,gold-%d' % (player, self.table.players[player].get_gold()))
            return player

    def reward_top_one(self, top1, reward_gold):
        top1_reward_gold = int(float(reward_gold) * TABLE_GAME_CONF[6])
        #print 'top1_reward_gold',top1_reward_gold
        reward_remain_gold = reward_gold - top1_reward_gold
        #print 'reward_remain_gold',reward_remain_gold
        # if not self.table.game.is_robot(top1):
        #   self.minus_stack(top1_reward_gold)
            #logging.info(u'奖励：TOP—1，当前用户%d是第一名，奖励金币：%d，总奖励金币数：%d' % (top1, top1_reward_gold, reward_gold))

        self.table.players[top1].reward_gold = top1_reward_gold
        # self.table.game.player_result[top1].win_gold += top1_reward_gold
        self.table.game.player_result[top1].reward_gold = top1_reward_gold

        # logging.info(u'奖励：用户投注在幸运一击的actions, %s' % (self.table.game.player_actions))
        top1_bet_total = sum(action.gold for action in self.table.game.player_actions[top1] \
                             if action.action_type == self.table.poker_maker.poker_result.winner)
        # top1_bet_total = get_player_bet_total(top1, 0, self.table.game.player_actions)
        if self.table.poker_maker.poker_result.winner > 0:
            bet_remain_gold = self.table.game.red_total - top1_bet_total
        else:
            bet_remain_gold = self.table.game.black_total - top1_bet_total
        # bet_remain_gold = self.table.game.lucky_total - top1_bet_total

        self.add_reward_player(top1, top1_reward_gold, 1)
        # self.table.lock.acquire()
        #logging.debug(u'1192 acquire')
        try:
            self.table.players[top1].plus_gold(self.table, top1_reward_gold)
            self.table.game.player_result[top1].gold = self.table.players[top1].get_gold()
            # self.table.broadcast_war_award(self.players[top1].user_dal, self.players[top1].user_dal)
            self.table.game.top_winners.append(self.players[top1])
            if self.table.players[top1].access_service != -1:
                self.table.game.calc_result_gold(0, top1_reward_gold)
            gevent.spawn_later(16, self.table.broadcast_war_award, *(self.players[top1].user_dal, top1_reward_gold,) )
        finally:
            pass
            # self.table.lock.release()
            #logging.debug(u'1197 release')

        return bet_remain_gold, reward_remain_gold

    def reward_other(self, uid, bet_remain_gold, reward_remain_gold):
        other_bet_total = sum(action.gold for action in self.table.game.player_actions[uid] \
                             if action.action_type == self.table.poker_maker.poker_result.winner)
        # user_bet_lucky = sum([action.gold for action in self.table.game.player_actions[uid]])
        # print 'user_bet_lucky',user_bet_lucky

        remain_reward_other_gold = reward_remain_gold * (float(other_bet_total) / bet_remain_gold)
        #if not self.table.game.is_robot(uid):
        #    self.minus_stack(remain_reward_other_gold)
            # logging.info(u'奖励：Others，当前用户%d，奖励金币：%d' % (uid, remain_reward_other_gold))
            # print 'remain_reward_other_gold',remain_reward_other_gold
        self.table.players[uid].reward_gold = int(remain_reward_other_gold)
        # self.table.game.player_result[uid].win_gold += int(remain_reward_other_gold)
        self.table.game.player_result[uid].reward_gold = int(remain_reward_other_gold)
        self.table.players[uid].plus_gold(self.table, remain_reward_other_gold)
        self.table.game.player_result[uid].gold = self.table.players[uid].get_gold()
        self.add_reward_player(uid,remain_reward_other_gold, 0)
        if self.table.players[uid].access_service != -1:
                self.table.game.calc_result_gold(0, remain_reward_other_gold)

    def add_reward_player(self, uid, reward_gold, is_top1=0):
        log = TWarAwardLog()
        log.war_id = 0
        log.award = reward_gold
        log.is_top1 = is_top1
        log.uid = uid
        log.create_time = int(time.time())
        self.reward_players_log.append(log)

    def set_top_winners(self):
        # self.reward_players_log.sort(cmp=lambda x, y: cmp(x.award, y.award), reverse=True)

        # logging.info(u'开奖前三的用户 top winners 3：%s' % str(self.reward_players_log[:3]))
        for reward_log in sorted(self.reward_players_log, key=lambda x:x.award, reverse=True)[:3]:
            if  reward_log.uid == self.table.game.top_winners[0].uid:
                continue
            self.table.game.top_winners.append(self.table.players[reward_log.uid])

    def add_stack_gold(self, gold):
        if self.stack < 5000000:
            self.stack += int(float(gold) * 0.95)
        elif 5000000 < self.stack < 20000000:
            self.stack += int(float(gold) * 0.9)
        elif 20000000 < self.stack < 100000000:
            self.stack += int(float(gold) * 0.85)
        elif self.stack > 100000000:
            self.stack += int(float(gold) * 0.8)


    def win_tax(self, win_gold):
        fee = float(win_gold) * TABLE_GAME_CONF[4]
        low, hight = get_tax(self.gold)
        tax = fee * (float(random.randint(low, hight)) / 100)
        self.gold += tax
        # if self.gold > TABLE_GAME_CONF[10]:
        #     self.gold = TABLE_GAME_CONF[10]
        return float(win_gold) - tax

    def minus_stack(self, gold):
        if self.stack >= gold:
            self.stack -= gold

    def append_record(self, result):
        if len(self.records) > TABLE_GAME_CONF[1] :
            self.records.pop(0)
        self.records.append(result)


class WarAwardLog:
    def __init__(self, user_info, reward_player_log, total_reward, award_winners):
        self.total_award = total_reward
        self.award = reward_player_log.award
        self.award_winners = award_winners
        self.time = int(reward_player_log.create_time * 1000)

        self.uid = user_info.id
        self.avatar = user_info.avatar
        self.nick = user_info.nick
        self.sex = user_info.sex
        self.vip_exp = user_info.vip_exp

    def get_proto_struct(self, pb_record):
        if pb_record == None:
            pb_record = war_pb2.PoolRankPlayer()
        pb_record.uid = self.uid
        pb_record.avatar = self.avatar
        pb_record.nick = self.nick.decode('utf-8')
        pb_record.total_award = self.total_award
        pb_record.award = self.award
        pb_record.award_winners = self.award_winners * 3 + 1
        pb_record.time = int(self.time)
        pb_record.sex = self.sex
        pb_record.vip_exp = self.vip_exp

    def __repr__(self):
        return 'uid=%d,avatar=%s,nick=%s,total_award=%d,award=%d,award_winners=%d,time=%d' % \
               (self.uid, self.avatar, self.nick, self.total_award, self.award, self.award_winners, self.time)


class GameLog:
    def __init__(self, table):
        self.table = table
        self.data_brief = []
        self.data_player = {}
        self.data_reward = []
        self.incr = 0

        self.ways = []

    def save_game(self):
        # logging.info(u'开始保存结果数据')
        try:
            # self.table.lock.acquire()
            # logging.info(u'save_game lock')
            session = self.table.get_session()
            # logging.info(u'get session %s' % str(session))
            log = TWarLog()
            log.red_poker = str(self.table.poker_maker.poker_result.red_poker)
            log.black_poker = str(self.table.poker_maker.poker_result.black_poker)
            log.winner = self.table.poker_maker.poker_result.winner
            log.winner_poker_type = self.table.poker_maker.poker_result.winner_poker_type
            log.lucky_rate = self.table.poker_maker.poker_result.lucky_rate
            log.red_total = self.table.game.red_total
            log.black_total = self.table.game.black_total
            log.lucky_total = self.table.game.lucky_total
            log.result_gold = self.table.game.result_gold
            log.reward_pool = self.table.reward_pool.gold
            log.lucky_stack = self.table.reward_pool.stack
            log.rich = str([x.uid for x in self.table.game.table.rank.rich_players[:TABLE_GAME_CONF[3]]])
            log.star = self.table.rank.has_lucky()
            log.star = self.table.game.table.rank.lucky_player.uid if self.table.rank.has_lucky() else 0
            log.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
            log.total_award = self.table.reward_pool.reward_gold
            log.award_winners = len(self.table.reward_pool.reward_players_log)
            session.add(log)
            session.flush()
            self.table.game.war_id = log.id

            if 0 in self.table.poker_maker.poker_result.win_types:
                self.table.reward_pool.append_record(1)
            else:
                self.table.reward_pool.append_record(0)

            # logging.info(u'save game log')

            self.table.redis.hset('war_game','reward_pool', int(log.reward_pool))
            self.table.redis.hset('war_game','lucky_stack', int(log.lucky_stack))
            # logging.info(u'set war_game params')
            for reward_players_log in self.table.reward_pool.reward_players_log:
                reward_players_log.war_id = self.table.game.war_id
                session.add(reward_players_log)
            session.flush()
            # logging.info(u'set reward_players done')
            self.data_brief.append(
                    LogBrief(self.table.game.war_id, self.table.poker_maker.poker_result.winner,
                             self.table.poker_maker.poker_result.winner_poker_type,
                             self.table.poker_maker.poker_result.lucky_rate))
            # logging.info(u'save data brief')
            if len(self.ways) != 0:

                if self.ways[-1][-1] == self.table.poker_maker.poker_result.winner:
                    self.ways[-1].append(self.table.poker_maker.poker_result.winner)
                else:
                    if len(self.ways) >= TABLE_GAME_CONF[2]:
                        self.ways.pop(0)
                    self.ways.append([self.table.poker_maker.poker_result.winner])


            if self.table.robot_manager != None:
                self.table.robot_manager.save_result(self.table.poker_maker.poker_result.winner,
                                                     self.table.poker_maker.poker_result.lucky_rate)
                for uid, player_result in self.table.game.player_result.items():
                    if self.table.robot_manager.is_robot(uid):
                        continue
                    if player_result.bet_gold <= 0:
                        continue
                    player_log = TWarPlayerLog()
                    player_log.war_id = self.table.game.war_id
                    player_log.uid = uid
                    player_log.bet_gold = player_result.bet_gold
                    # player_log.red_black_bet = player_result.red_black_bet
                    # player_log.lucky_bet = player_result.lucky_bet
                    player_log.win_gold = player_result.win_gold
                    # player_log.red_black_bet_win = player_result.red_black_bet_win
                    # player_log.lucky_bet_win = player_result.lucky_bet_win
                    # player_log.real_win_gold = player_result.real_win_gold
                    player_log.fee = player_result.real_fee
                    player_log.gold = player_result.gold
                    player_log.reward_gold = player_result.reward_gold
                    session.add(player_log)
                session.flush()
        except:
            traceback.print_exc()
        finally:
            self.table.close_session(session)
            # self.table.lock.release()

            # logging.info(u'save_game release')
            # logging.info(u'结果保存事件成功')

    def get_war_brief(self, size, table):
        session = table.get_session()
        try:
            lists = session.query(TWarLog.id, TWarLog.winner, TWarLog.winner_poker_type, TWarLog.lucky_rate) \
                .order_by(TWarLog.id.desc()).limit(size).all()
        finally:
            table.close_session(session)
        lists.reverse()
        paths = [x[1] for x in lists]
        # paths.reverse()
        self.ways = []
        for x in paths:
            self.poker_ways(x)

        if lists == None or len(lists) <= 0:
            return []

        return [LogBrief(x[0], x[1], x[2], x[3]) for x in lists]

    def get_poker_path(self):
        return [LogBrief(-1, way[0], P_DAN, -1, len(way)) for way in self.ways[-20:]]

    def reward_player_log(self, table, war_id, reward_players):
        session = table.get_session()
        try:
            for reward_player in reward_players:
                reward_player.war_id = war_id
                session.add(reward_player)
            session.flush()
        finally:
            table.close_session(session)

    def get_award_lists(self, session, size, table):
        lists = session.query(TWarAwardLog, TWarLog.total_award, TWarLog.award_winners).join(TWarLog,
                                                                                             TWarAwardLog.war_id == TWarLog.id) \
            .filter(TWarAwardLog.is_top1==1) \
            .order_by(TWarAwardLog.war_id.desc()) \
            .limit(size).all()

        rs = []
        for log, total_reward, award_winners in lists:
            rs.append(WarAwardLog(self.table.dal.get_user(log.uid), log, total_reward, award_winners))
        return rs

    def poker_ways(self, winner):

        if len(self.ways) == 0:
            self.ways.append([winner])
        else:
            if self.ways[-1][-1] != winner:
                self.ways.append([winner])
            else:
                self.ways[-1].append(winner)


class LogBrief:
    def __init__(self, id, winner, winner_poker_type, lucky_rate, continuous=-1):
        self.id = id
        self.winner = winner
        self.winner_poker_type = winner_poker_type
        self.lucky_rate = lucky_rate
        self.continuous = continuous

    def __repr__(self):
        return 'id=%d,winner=%d,winner_poker_type=%d,lucky_rate=%d,continuous=%d' % (
            self.id, self.winner, self.winner_poker_type, self.lucky_rate, self.continuous)

    def get_proto_struct(self, pb_history):
        if pb_history == None:
            pb_history = pb2.WarBriefGameResult()
        pb_history.id = self.id
        pb_history.winner = self.winner
        pb_history.lucky_rate = self.lucky_rate
        pb_history.winner_poker_type = self.winner_poker_type

        if self.continuous != -1:
            pb_history.winner_continuous = self.continuous


class WarChip:
    def __init__(self, gold):
        self.gold = gold

    def get_proto_struct(self, pb_chip):
        if pb_chip == None:
            pb_chip = pb2.WarChip()
        pb_chip.gold = self.gold
        return pb_chip


class WarChips:
    def __init__(self, gold, countof):
        self.gold = gold
        self.countof = countof

    def get_proto_struct(self, pb_chip):
        if pb_chip == None:
            pb_chip = pb2.WarChips()
        pb_chip.gold = self.gold
        pb_chip.countof = self.countof
        return pb_chip

if __name__ == '__main__':
    class tb:
        def __init__(self, pool):
            self.reward_pool = pool
            self.game = game()

        def is_continuous_unlucky(self):
            return True
    class tb_pool:
        def __init__(self):
            self.stack = 300000000

    class game:
        def __init__(self):
            self.real_lucky_total = 0

    table = tb(tb_pool())
    pm = PokerMaker(table)
    pm.init_poker()
    pm.random_choice_poker()

    i = 0
    while i < 10000000:
        for x in pm.random_poker[0].pokers:
            for y in pm.random_poker[1].pokers:
                if x.value == y.value and x.flower == y.flower:
                    print 'Error',pm.pokers
                    exit(-1)

        i += 1
    print len(pm.pokers_17)
