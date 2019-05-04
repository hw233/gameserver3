# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import traceback
import time
import datetime
import json
import random
import gevent
import logging
from gevent import monkey;monkey.patch_all()
from gevent import lock
from gevent.queue import Queue
from sqlalchemy import and_

from util.commonutil import *

from db.user import *
from db.lottery_reward_log import *
from db.lottery_log import *
from db.lottery_auto import *
from db.rank_lottery_top import *
from db.robot import *
from db.robot_war import *
from db.lottery_result import *
from eventsender import *
import lotteryconf
from db import connect
from proto import constant_pb2
from proto import struct_pb2
from proto import lottery_pb2
from hall.messagemanager import MessageManager

from goldflower import game as goldflower

class Table:
    def __init__(self, service):
        self.service = service
        self.lock = lock.Semaphore()
        self.sender = EventSender(self)
        self.table_event_queue = Queue()

        self.game = None
        self.start_time = -1
        self.push_players = {}
        self.big_winner_uids = []

        self.last_big_winner = None
        self.reward_gold_pool = 0
        self.real_gold_pool = 0
        self.last_baozi = 0
        self.history = []
        self.baozi_choice_index = 0
        # self.show_baozi_time = int(time.time()) + 60 * 90 # 线上
        self.show_baozi_time = int(time.time()) + 60 * 5 # 测试

        self.half_gold_count = 0

        gevent.spawn(self.restart_game)
        gevent.spawn_later(1, self.real_send_event)
        gevent.spawn_later(1, self.replace_big_winner_uid)



    def restart_game(self):
        self.start_time = int(time.time())
        self.init()
        while True:
            self.game = Game(self)
            self.game.start()
            self.game.running()
            self.game.over()
            gevent.sleep( abs(lotteryconf.GAMECONF['timeout'] - (int(time.time()) - self.start_time)) )

    def init(self):
        logging.info(u'Table 初始化...')
        self.get_last_big_winner()
        logging.info(u'加载最后大赢家: %s' % self.last_big_winner)
        self.get_reward_gold_pool()
        logging.info(u'加载奖池金币数：%d' % self.reward_gold_pool)
        self.get_last_baozi()
        logging.info(u'加载豹子最后出现时间：%d' % self.last_baozi)
        self.get_history()
        logging.info(u'加载历史牌型记录：%s' % self.history)

    def get_last_big_winner(self):
        if self.last_big_winner != None and self.last_big_winner.win_gold > 0:
            print 'seconds'
            return self.last_big_winner

        session = self.get_session()
        try:
            last_winner = session.query(TLotteryLog.big_winner_gold,TLotteryLog.create_time,TUser.id,TUser.nick,TUser.avatar)\
                .join(TUser, TUser.id == TLotteryLog.big_winner)\
                .order_by(TLotteryLog.id.desc())\
                .first()
            self.last_big_winner = Player(last_winner.id, -1)
            self.last_big_winner.win_gold = last_winner.big_winner_gold
            self.last_big_winner.create_unixtime = int(time.mktime(last_winner.create_time.timetuple()))
        except:
            traceback.print_exc()
        finally:
            self.close_session(session)

        return self.last_big_winner

    def get_reward_gold_pool(self):
        if self.reward_gold_pool > 0 :
            return self.reward_gold_pool

        session = self.get_session()
        try:
            log = session.query(TLotteryLog.reward_gold_pool, TLotteryLog.real_gold_pool)\
                .order_by(TLotteryLog.id.desc())\
                .first()
            self.reward_gold_pool = log.reward_gold_pool
	    if log.real_gold_pool < 0:
                self.real_gold_pool = 0
	    else:
	        self.real_gold_pool = log.real_gold_pool
        except:
            traceback.print_exc()
        finally:
            self.close_session(session)

        return self.reward_gold_pool

    def get_last_baozi(self):
        if self.last_baozi > 0 :
            return self.last_baozi

        session = self.get_session()
        try:
            last_baozi_datetime = session.query(TLotteryLog.create_time)\
                .filter(TLotteryLog.poker_type == constant_pb2.P_BAOZI)\
                .order_by(TLotteryLog.id.desc())\
                .first()
            self.last_baozi = int(time.mktime(last_baozi_datetime.create_time.timetuple()))
        except:
            traceback.print_exc()
        finally:
            self.close_session(session)

        return self.last_baozi

    def get_history(self):
        if len(self.history) > 0 :
            return self.history

        session = self.get_session()
        try:
            poker_types = session.query(TLotteryLog.poker_type)\
                .order_by(TLotteryLog.id.desc())\
                .limit(lotteryconf.GAMECONF['poker_type_history_len'])\
                .all()
            self.history = [x.poker_type for x in poker_types]
        except:
            traceback.print_exc()
        finally:
            self.close_session(session)

        return self.history

    def append_hisotry(self, poker_type):
        self.history.append(poker_type)
        if len(self.history) > lotteryconf.GAMECONF['poker_type_history_len']:
            self.history = self.history[-lotteryconf.GAMECONF['poker_type_history_len']:]

    def in_table(self, uid):
        if uid in self.push_players:
            return True
        return False

    def sit_table(self, user_info, access_service):
        self.push_players[user_info.id] = Player(user_info.id, access_service, user_info)

    def get_sit_table_proto_struct(self, user_info, pb2):
        pb2.live_seconds = 0

        pb2.remain_seconds = self.game.get_remain_seconds()

        pb2.reward_gold_pool = self.reward_gold_pool
        pb2.last_baozi = int(time.time()) - self.last_baozi

        last_winner = self.get_last_big_winner()
        if last_winner:
            if last_winner.user_info == None:
                last_winner.lazy_load_user(self.service.dal)
            last_winner.get_big_winner_proto_struct(pb2.last_big_winner)

        historys = self.get_history()
        for poker_type in historys:
            PokerTypeBet(-1, poker_type).get_proto_struct(pb2.history.add())

        bets = self.get_poker_type_bet()
        for poker_type, bet_gold in bets.items():
            PokerTypeBet(bet_gold, poker_type).get_proto_struct(pb2.poker_type_bet.add())

        my_bets = self.get_poker_type_bet(user_info.id)
        my_bet_types = {}
        for bet in my_bets:
            if bet.poker_type not in my_bet_types:
                my_bet_types[bet.poker_type] = bet.bet_gold
            else:
                my_bet_types[bet.poker_type] += bet.bet_gold
        for poker_type, bet_gold in my_bet_types.items():
            PokerTypeBet(bet_gold, poker_type).get_proto_struct(pb2.my_bet.add())

        auto_bet_user = self.get_lottery_auto_users(user_info.id)
        if auto_bet_user != None and auto_bet_user.status != -1:
            pb2.remain_auto_bet = auto_bet_user.auto_bet_count - auto_bet_user.auto_bet_now
        else:
            pb2.remain_auto_bet = 0

        if self.game.poker_manager.win_poker != None:
            for poker in self.game.poker_manager.win_poker.pokers:
                poker.get_proto_struct(pb2.win_poker.add())
            pb2.win_poker_type = self.game.poker_manager.win_poker_type


    def get_poker_type_bet(self, my_bet = 0):
        if my_bet == 0:
            return self.game.bet_history
        else:
            if my_bet in self.game.bet_players:
                return self.game.bet_players[my_bet]
            return []

    def auto_bet(self, uid, bets, auto_bet_number):
        player = self.push_players[uid]
        player.auto_bet_number = auto_bet_number

        self.add_auto_bet(uid,bets,auto_bet_number)

        bets_gold = sum([bet.bet_gold for bet in bets])
        # player.minus_gold(self, bets_gold * auto_bet_number)
        session = get_context("session",None)
        if session == None:
            session = self.get_session()
            set_context("session", session)
        player.modify_gold(session, -(bets_gold * auto_bet_number))
        return bets_gold

    def add_auto_bet(self, uid, bets, auto_bet_number):
        session = self.get_session()
        try:
            auto =  TLotteryAuto()
            auto.uid = uid
            auto.auto_bet_count = auto_bet_number
            auto.auto_bet_now = 0
            auto.auto_bet_pokers = json.dumps([{'bet_gold':bet.bet_gold,'poker_type':bet.poker_type} for bet in bets])
            auto.win_gold = 0
            auto.status = 1 # 1=进行中，0=已完成，-1=手动取消
            auto.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
            session.merge(auto)
            session.flush()
        except:
            traceback.print_exc()
        finally:
            self.close_session(session)

    def cancel_auto_bet(self, bet_user):
        session = self.get_session()
        try:
            session.query(TLotteryAuto).filter(TLotteryAuto.uid == bet_user.uid).update({
                TLotteryAuto.status : bet_user.status
            })
        except:
            traceback.print_exc()
        finally:
            self.close_session(session)

    def leave_table(self, uid):
        # 用户既没有自动投，也没有普通投，就移除推送用户列表
        if not self.get_lottery_auto_users(uid):
            if uid not in self.game.bet_players:
                self.push_players.pop(uid)

    def get_lottery_auto_users(self, uid = 0):
        session = self.get_session()
        try:
            # status,1=进行中，0=已完成，-1=手动取消
            if uid == 0:
                return session.query(TLotteryAuto).filter(TLotteryAuto.status == 1).all()
            else:
                return session.query(TLotteryAuto).filter(and_(TLotteryAuto.uid == uid, TLotteryAuto.status == 1)).first()
        except:
            traceback.print_exc()
        finally:
            self.close_session(session)

    def remove_timeout_player(self, uid):
        if uid not in self.game.bet_players:
            self.push_players.pop(uid)

    def is_timeout(self, player_timeout):
        if self.start_time >= player_timeout:
            return True
        else:
            return False

    def extend_timeout(self, uid):
        player = self.push_players[uid]
        player.timeout = int(time.time()) + lotteryconf.GAMECONF['timeout']
        return lotteryconf.GAMECONF['timeout']

    def notify_one(self,event,player):
        event_type = event.header.command
        event_data = event.encode()
        try:
            if player.access_service == -1:
                # 机器人投
                pass
            elif player.access_service == 0:
                # 自动投，用户可能在线，也可能不在线
                access_service = self.service.redis.hget('online', player.uid)
                if access_service != None:
                    self.send_table_event(int(access_service), player.uid, event_type, event_data)
            else:
                # 普通投
                self.send_table_event(player.access_service,player.uid,event_type,event_data)
        except:
            traceback.print_exc()
        finally:
            pass

    def send_table_event(self,access_service,uid,event_type,event_data):
        self.table_event_queue.put_nowait((access_service,uid,event_type,event_data,))

    def real_send_event(self):
        service = self.service
        while True:
            access_service,uid,event_type,event_data = self.table_event_queue.get()
            service.send_client_event(access_service,uid,event_type,event_data)

    def get_session(self):
        return connect.Session()

    def close_session(self, session):
        if session:
            session.close()
            session = None

    def send_bet_done_mail(self, session, bet_user):
        message = ''
        if bet_user.auto_bet_count == bet_user.auto_bet_now and bet_user.status == 0:
            message = u'您在欢乐时时彩自动跟注%d次，完成%d次，赢取金币%d' % (bet_user.auto_bet_count,
                                                bet_user.auto_bet_now,
                                                bet_user.win_gold)
        elif bet_user.status == -1:
            message = u'您在欢乐时时彩自动跟注%d次，完成%d次，赢取金币%d' % (bet_user.auto_bet_count,
                                                bet_user.auto_bet_now,
                                                bet_user.win_gold)

        if bet_user.win_gold > 0:
            message += u'，请及时领取金币！'

        MessageManager.send_mail(session, bet_user.uid, 0,
                                 title=u'欢乐时时彩',
                                 content=message,
                                 type=1 if bet_user.win_gold > 0 else 0,
                                 gold=bet_user.win_gold)
        MessageManager.push_notify_mail(self.service.redis, bet_user.uid)

    def broadcast_big_reward(self, user_info, win_gold):
        MessageManager.push_lottery_win(self.service.redis, user_info.id, user_info.nick, user_info.vip_exp, win_gold)

    def replace_big_winner_uid(self):
        while True:
            session = self.get_session()
            try:
                robots = session.query(TRobot.uid).join(TUser, TRobot.uid == TUser.id).filter(TUser.gold > 5000000).all()
                robots_war = session.query(TRobotWar.uid).join(TUser, TRobotWar.uid == TUser.id).filter(TUser.gold > 5000000).all()
                robots_uids = set([x.uid for x in robots_war] + [x.uid for x in robots])
                not_robots = lotteryconf.get_robots_not_online(self.service.redis, robots_uids)

                if len(self.big_winner_uids) == 0:
                    self.big_winner_uids = random.sample(not_robots, 10)
                else:
                    for new_uid in random.sample(not_robots, 5):
                        idx = random.randint(0, len(self.big_winner_uids) -1)
                        self.big_winner_uids[idx] = new_uid
            except:
                traceback.print_exc()
            finally:
                self.close_session(session)
            gevent.sleep(600)

    def robot_can_pay(self, real_bet_gold, baozi_total):
	if real_bet_gold != 0:
	    return False
	return True

    def real_pool_can_pay(self, real_bet_gold, baozi_total):
	if real_bet_gold <= 0:
	    return False

	logging.info('real=%d,total=%d,reward=%d' % (real_bet_gold,baozi_total,self.reward_gold_pool * lotteryconf.GAMECONF['reward_gold_rate']))
	reward_real_gold = real_bet_gold / float(baozi_total) * (self.reward_gold_pool * lotteryconf.GAMECONF['reward_gold_rate'])
	v1 = real_bet_gold / float(baozi_total)
	v2 = self.reward_gold_pool * lotteryconf.GAMECONF['reward_gold_rate']
	v3 = v1 * v2
	logging.info('1=%s,%s' % (v1,type(v1)))
	logging.info('2=%s,%s' % (v2,type(v2)))
	logging.info('3=%s,%s' % (v3,type(v3)))
	logging.info('reward_real_gold=%d' % reward_real_gold)
	if reward_real_gold > 0:
	    return self.real_gold_pool > reward_real_gold
	return False
	    

    def need_show_baozi(self):
        return self.show_baozi_time < int(time.time())


class Game:
    def __init__(self, table):
        self.table = table
        self.can_bet = True

        self.poker_manager = PokerManager()

        self.bet_players = {}
        self.auto_bet_players = {}

        self.real_player_big_win = {'gold':0,'uid':0}
        self.reward_gold = 0
        self.robot_bet_record = []

        self.give_reward_gold = 0

        self.bet_history = {
            constant_pb2.P_BAOZI:0,
            constant_pb2.P_TONGHUASHUN:0,
            constant_pb2.P_TONGHUA:0,
            constant_pb2.P_SHUN:0,
            constant_pb2.P_DUI:0,
            constant_pb2.P_DAN:0,
        }

    def start(self):
        self.table.start_time = int(time.time())
        logging.info(u' ')
        logging.info(u'游戏初始化...')
        logging.info(u'start_time=%d, reward_gold=%d, real_gold=%d' % (self.table.start_time, self.table.reward_gold_pool, self.table.real_gold_pool))

        logging.info(u'减半检查，count=%d' % self.table.half_gold_count)
        if self.table.half_gold_count >= 120:
            self.table.half_gold_count = 0
            new_real_gold_pool = self.table.real_gold_pool / 2
            if new_real_gold_pool > 0:
                self.table.real_gold_pool = new_real_gold_pool
        else:
            self.table.half_gold_count += 1
        logging.info(u'real_gold_pool=%d,half_gold_count=%d' % (self.table.real_gold_pool, self.table.half_gold_count))

        auto_bet_users = self.table.get_lottery_auto_users()
        logging.info(u'加载未完成自动投注记录：%s' % auto_bet_users)
        for bet_user in auto_bet_users:
            if bet_user.uid not in self.table.push_players:
                # 用户close了，但是有自动投，所以需要重新构建Player
                self.table.push_players[bet_user.uid] = Player(bet_user.uid,0)
            bets = [PokerTypeBet(b['bet_gold'], b['poker_type']) for b in json.loads(bet_user.auto_bet_pokers)]
            self.add_bet(bet_user.uid, bets, bet_user)
            logging.info(u'用户(%d)自动投注记录：%s' % (bet_user.uid, str(self.auto_bet_players)))
            self.incr_auto_bet(bet_user)
            logging.info(u'用户(%d)自动投状态查看：总数=%d，已投=%d，状态=%d' % (bet_user.uid,bet_user.auto_bet_count,bet_user.auto_bet_now,bet_user.status))

        for player in self.table.push_players.values():
            player.win_gold = 0
            player.reward_gold = 0
            self.table.remove_timeout_player(player.uid)


        # temp_push_users = dict(self.table.push_players)
        # for uid, player in temp_push_users.items():
        #     if self.table.is_timeout(player.timeout):
        #         self.table.remove_timeout_player(uid)
        # logging.info(u'当前用户：users=%s' % (temp_push_users))
        logging.info(u'剩余用户：users=%s' % (self.table.push_players))
        # print 'start',self.table.start_time

    def add_bet(self, uid, bets, bet_user = None):
        if bet_user:
            self.auto_bet_players[uid] = bet_user

        if uid in self.bet_players:
            self.bet_players[uid] += [PokerTypeBet(bet.bet_gold, bet.poker_type) for bet in bets]
        else:
            self.bet_players[uid] = [PokerTypeBet(bet.bet_gold, bet.poker_type) for bet in bets]

        for bet in bets:
            self.bet_history[bet.poker_type] += bet.bet_gold

        print u'用户bet：',self.bet_players

    def incr_auto_bet(self, bet_user):
        bet_user.auto_bet_now += 1
        if bet_user.auto_bet_count == bet_user.auto_bet_now:
            bet_user.status = 0 # 1=进行中，0=已完成，-1=手动取消
        session = self.table.get_session()
        try:
            session.add(bet_user)
            session.flush()
        except:
            traceback.print_exc()
        finally:
            self.table.close_session(session)

    def running(self):
        logging.info(u' ')
        logging.info(u'游戏运行中...')
        while not self.is_end():

            make_bet_golds = lotteryconf.make_bet(self.table.reward_gold_pool)
            for poker_type, bet_gold in make_bet_golds.items():
                self.bet_history[poker_type] += bet_gold
            self.robot_bet_record.append(make_bet_golds)
            logging.info(u'牌型投注(%d)：%s' % (int(time.time()) - self.table.start_time,str(self.bet_history)))
            # logging.info(u'自动生成金币查看：%s' % str(self.robot_bet_record))
            # if (int(time.time()) - self.table.start_time) % 2 == 1:
            self.table.sender.game_running()
            gevent.sleep(2)

    def over(self):
        logging.info(u' ')
        logging.info(u'游戏结束中...')
        self.can_bet = False
        # 1. 得到牌结果
        self.poker_manager.random_win_poker(self.table)
        logging.info(u'生成牌=%s，牌型=%d' % (self.poker_manager.win_poker,self.poker_manager.win_poker_type))

        # 提前扣税，相关牌型已经 * 倍数 被扣税了，后面计算时，不用考虑计算扣税
        self.table.reward_gold_pool += int(self.bet_history[self.poker_manager.win_poker_type] * float(lotteryconf.GAMECONF['tax']))

        # 3. 根据牌结果计算用户输赢.普通牌型直接得出结果，豹子牌型需要另行计算
        baozi_players = {}
        for uid, bets in self.bet_players.items():
            if uid not in self.table.push_players:
                continue
            for bet in bets:
                if bet.poker_type == self.poker_manager.win_poker_type:
                    if bet.poker_type == constant_pb2.P_BAOZI:
                        if uid in baozi_players:
                            baozi_players[uid] += bet.bet_gold
                        else:
                            baozi_players[uid] = bet.bet_gold
                        logging.info(u'豹子,用户(%d)投注豹子(%d)金币数%d' % (uid,bet.bet_gold,baozi_players[uid]))
                    else:
                        win_gold = int(bet.bet_gold * self.poker_manager.get_poker_multiple())
                        tax_gold = int(win_gold * lotteryconf.GAMECONF['tax'] )
                        win_gold -= tax_gold
                        player = self.table.push_players[uid]

                        self.save_player_result(player, win_gold, 0, bet.bet_gold)
                        self.set_big_real_win(uid, player.win_gold)
                        logging.info(u'用户(%d)投注牌型(%d)金币(%d)，获得金币(%d)税费(%d),本利赢钱(%d)奖池增加税费后为(%d)' %
                                     (uid,bet.poker_type,bet.bet_gold,win_gold,tax_gold,player.win_gold,self.table.reward_gold_pool))

        # 豹子牌型需要重新计算用户按比例分配的奖池金额
        # 豹子牌型需要奖励奖池20%的金币
        if self.poker_manager.win_poker_type == constant_pb2.P_BAOZI:
            self.table.last_baozi = int(time.time())
            if self.bet_history[constant_pb2.P_BAOZI] > 0:
                logging.info(u'!豹子!：奖池=%d' % self.table.reward_gold_pool)
                reward_gold = int(self.table.reward_gold_pool * lotteryconf.GAMECONF['reward_gold_rate'])

                self.table.reward_gold_pool -= reward_gold
                self.give_reward_gold = reward_gold
                logging.info(u'20%%奖励金币：奖池=%d，20%%奖励=%d' % (self.table.reward_gold_pool,reward_gold))

                if  len(baozi_players) > 0:
                    baozi_bet_total = sum([x for x in baozi_players.values()])
                    baozi_total = self.bet_history[constant_pb2.P_BAOZI]
                    self.reward_gold = int((baozi_bet_total / float(baozi_total)) * reward_gold)
                    logging.info('real_gold_pool=%d ,1' % self.table.real_gold_pool)
                    self.table.real_gold_pool -= self.reward_gold
                    logging.info('real_gold_pool=%d ,2' % self.table.real_gold_pool)
                    logging.info(u'豹子牌型总投注：%d，真实玩家投注：%d，真实玩家奖励：%d' % (baozi_total, baozi_bet_total, self.reward_gold))
                    for uid, baozi_bet_gold in baozi_players.items():
                        if uid not in self.table.push_players:
                            continue
                        logging.info(u'玩家=%d投注=%d，真实玩家奖励=%d，获得奖励=%s' % (uid, baozi_bet_gold, self.reward_gold, baozi_bet_gold / float(baozi_total)))
                        player = self.table.push_players[uid]
                        reward_gold = int(baozi_bet_gold / float(baozi_bet_total) * self.reward_gold)
                        reward_win_gold_tax = int(reward_gold * lotteryconf.GAMECONF['tax'])
                        reward_win_gold = reward_gold - reward_win_gold_tax
                        self.save_player_result(player, reward_win_gold,reward_win_gold,baozi_bet_gold)
                        self.set_big_real_win(uid, player.win_gold)
                        logging.info(u' 用户(%d)分的奖励(%d)本利赢钱(%d)' % (uid,reward_gold,player.win_gold))


        if self.real_player_big_win['uid'] > 0 and self.real_player_big_win['gold'] > lotteryconf.BROADCAST_MIN_GOLD:
            big_reward_user = self.table.service.dal.get_user(self.real_player_big_win['uid'])
            self.table.broadcast_big_reward(big_reward_user, self.real_player_big_win['gold'])


        # 比较机器人与真实用户得出大赢家
        self.set_big_winner()

        self.table.append_hisotry(self.poker_manager.win_poker_type)
        self.save_game()
        self.table.sender.game_over()

    def save_player_result(self, player, win_gold, reward_gold, bet_gold = 0):
        player.win_gold += win_gold
        player.reward_gold += reward_gold

        player.win_gold += bet_gold


    def auto_bet_cancel(self, session, uid):
        if uid in self.auto_bet_players:
            bet_user = self.auto_bet_players[uid]
            bet_user.status = -1
            self.table.cancel_auto_bet(bet_user)
            player = self.table.push_players[uid]
            return player.plus_remain_gold(self.table, bet_user)

        else:
            # 用户可能在当局内自动投，然后马上自动取消
            bet_user = self.table.get_lottery_auto_users(uid)
            if bet_user and bet_user.auto_bet_now == 0:
                bet_user.status = -1
                self.table.cancel_auto_bet(bet_user)
                player = self.table.push_players[uid]
                return player.plus_remain_gold(self, bet_user)
            else:
                raise Exception("Error: Can't cancel user=%d Auto Bet" % uid)
        # player = self.table.players[uid]
        # player.auto_bet_number = -1

        # 撤销自动投，需要发邮件
        # self.table.send_cancel_mail()
    def check_bet(self, uid, bets):
        if uid in self.bet_players:
            bet_total = {}
            for old_bet in self.bet_players[uid]:
                if old_bet.poker_type in bet_total:
                    bet_total[old_bet.poker_type] += old_bet.bet_gold
                else:
                    bet_total[old_bet.poker_type] = old_bet.bet_gold

            for bet in bets:
                if bet.poker_type in bet_total:
                    bet_total[bet.poker_type] += bet.bet_gold
                else:
                    bet_total[bet.poker_type] = bet.bet_gold


            if max(bet_total.values()) > lotteryconf.BET_MAX:
                return False
        else:
            for bet in bets:
                if bet.bet_gold > lotteryconf.BET_MAX:
                    return False

        return True


    def bet(self, uid, bets):
        self.add_bet(uid, bets)

        bets_gold = sum([bet.bet_gold for bet in bets])
        player = self.table.push_players[uid]
        session = get_context("session",None)
        if session == None:
            session = self.table.get_session()
            set_context("session", session)
        player.modify_gold(session, -bets_gold)
        # player.minus_gold(self.table, bets_gold)
        # self.table.extend_timeout(uid)

        return bets_gold

    def get_result_proto_struct(self, incr_gold, gold, pb2):
        pb2.gold = gold
        pb2.incr_gold = incr_gold
        return pb2

    def get_gold_change_proto_struct(self, pb2):
        pb2.remain_seconds = self.get_remain_seconds()

        for bet_poker_type, bet_gold in self.bet_history.items():
            PokerTypeBet(bet_gold, bet_poker_type).get_proto_struct(pb2.poker_type_bet.add())

        return pb2

    def save_game(self):
        session = self.table.get_session()
        session.begin()
        try:
            lottery_log = self.save_lottery(session)

            self.save_baozi_reward(session, lottery_log.id, self.get_big_baozi_winner())
            self.save_rank(session, lottery_log)
            self.save_bet(session)
            session.commit()
        except:
            session.rollback()
            traceback.print_exc()
        finally:
            self.table.close_session(session)

    def save_lottery(self, session):
        log = TLotteryLog()
        log.poker = str(self.poker_manager.win_poker)
        log.poker_type = self.poker_manager.win_poker_type
        log.reward_gold_pool = self.table.reward_gold_pool
        log.real_gold_pool = self.table.real_gold_pool
        log.big_winner = self.table.last_big_winner.uid
        log.big_winner_gold = self.table.last_big_winner.win_gold
        log.dan_bet = self.bet_history[constant_pb2.P_DAN]
        log.dui_bet = self.bet_history[constant_pb2.P_DUI]
        log.shun_bet = self.bet_history[constant_pb2.P_SHUN]
        log.tonghua_bet = self.bet_history[constant_pb2.P_TONGHUA]
        log.tonghuashun_bet = self.bet_history[constant_pb2.P_TONGHUASHUN]
        log.baozi_bet = self.bet_history[constant_pb2.P_BAOZI]
        log.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
        session.add(log)
        session.flush()
        return log

    def save_baozi_reward(self, session, lottery_id, big_baozi_winner):
        if big_baozi_winner != None:
            log = TLotteryRewardLog()
            log.lottery_id = lottery_id
            log.uid = big_baozi_winner.uid
            log.create_unixtime = int(time.time())
            log.reward_gold = big_baozi_winner.reward_gold
            session.add(log)

    def save_rank(self, session, lottery_log):
        for player in self.table.push_players.values():
            if player.access_service != -1:
                self.save_player_rank(session, player.uid, player.win_gold)
                self.save_result(session, lottery_log, player)

        if self.table.last_big_winner.access_service == -1:
            self.save_player_rank(session, self.table.last_big_winner.uid, self.table.last_big_winner.win_gold)

    def save_result(self, session, lottery_log, player):
        if player.uid in self.bet_players:
            bet_golds = self.bet_players[player.uid]
            bet_total = sum([bet.bet_gold for bet in bet_golds])
            log = TLotteryResult()
            log.lottery_id = lottery_log.id
            log.uid = player.uid
            log.bet = bet_total
            log.win = player.win_gold
            session.add(log)

    def save_player_rank(self, session, uid, total):
        log = session.query(TRankLotteryTop).filter(and_(TRankLotteryTop.uid == uid, TRankLotteryTop.add_date == time.strftime('%Y-%m-%d'))).first()
        if log == None:
            log = TRankLotteryTop()
            log.add_date = time.strftime('%Y-%m-%d')
            log.uid = uid
            log.total = total
            log.created_time = time.strftime('%Y-%m-%d %H:%M:%S')
            session.add(log)
        else:
            session.query(TRankLotteryTop).filter(and_(TRankLotteryTop.uid == uid, TRankLotteryTop.add_date == time.strftime('%Y-%m-%d'))).update({
                TRankLotteryTop.total: TRankLotteryTop.total + total
            })

    def save_bet(self, session):
        for uid in self.bet_players:
            player = self.table.push_players[uid]
            if uid in self.auto_bet_players:
                bet_user = self.auto_bet_players[uid]
                if player.win_gold > 0:
                    bet_user.win_gold += player.win_gold
                    session.add(bet_user)
                if bet_user.status == -1:
                    self.table.cancel_auto_bet(bet_user)
                if bet_user.status == 0 or bet_user.status == -1:
                    self.table.send_bet_done_mail(session, bet_user)
            else:
                # player.plus_gold(self.table, player.win_gold, session)
                player.modify_gold(session, player.win_gold)

    def get_over_proto_struct(self, pb2):

        for poker in self.poker_manager.win_poker.pokers:
            poker.get_proto_struct(pb2.win_poker.add())
        pb2.win_poker_type = self.poker_manager.win_poker_type
        pb2.reward_gold_pool = self.table.reward_gold_pool

        pb2.last_baozi = int(time.time()) - self.table.last_baozi

        last_winner = self.table.get_last_big_winner()
        if last_winner:
            if last_winner.user_info == None:
                last_winner.lazy_load_user(self.table.service.dal)
            last_winner.get_big_winner_proto_struct(pb2.last_big_winner)

        return pb2

    def get_remain_seconds(self):
        remain_sec = lotteryconf.GAMECONF['bet_time'] - (int(time.time()) - self.table.start_time)
        # if remain_sec <= 0:
        #     return 0
        return remain_sec

    def is_end(self):
        return (int(time.time()) - self.table.start_time) > lotteryconf.GAMECONF['bet_time']

    def set_big_real_win(self, uid, win_gold):
        if win_gold > self.real_player_big_win['gold']:
            self.real_player_big_win['uid'] = uid
            self.real_player_big_win['gold'] = win_gold

    def set_big_winner(self):
        robot_big_winner_uid = random.choice(self.table.big_winner_uids)
        robot_big_win_gold = self.get_robot_big_winner_gold()
        if robot_big_win_gold == -1:
            return

        if self.real_player_big_win['gold'] > robot_big_win_gold:
            self.table.last_big_winner = self.table.push_players[self.real_player_big_win['uid']]
            logging.info(u'真实玩家(%d)赢取(%d) > 机器人(%d)赢取(%d)' % (self.table.last_big_winner.uid,
                                                              self.table.last_big_winner.win_gold,
                                                              robot_big_winner_uid,
                                                              robot_big_win_gold))
        else:
            self.table.last_big_winner = Player(robot_big_winner_uid, -1)
            self.table.last_big_winner.lazy_load_user(self.table.service.dal)
            self.table.last_big_winner.win_gold = robot_big_win_gold
            self.table.last_big_winner.reward_gold = robot_big_win_gold
            logging.info(u'真实玩家(%d)赢取(%d) < 机器人(%d)赢取(%d)' % (self.real_player_big_win['uid'],
                                                              self.real_player_big_win['gold'],
                                                              robot_big_winner_uid,
                                                              robot_big_win_gold))



    def get_robot_big_winner_gold(self):
        if self.poker_manager.win_poker_type == constant_pb2.P_BAOZI:
            if self.bet_history[constant_pb2.P_BAOZI] == 0:
                return -1
            for robot_bet in self.robot_bet_record:
                if robot_bet[constant_pb2.P_BAOZI] > 50000:
                    return int(50000 / float(self.bet_history[constant_pb2.P_BAOZI]) * self.give_reward_gold)
            choice_rate = random.choice([5] * 50 + [3] * 30 + [2] * 20)
            if choice_rate == 5:
                return int(8000 / float(self.bet_history[constant_pb2.P_BAOZI]) * self.give_reward_gold)
            elif choice_rate == 3:
                return int(6000 / float(self.bet_history[constant_pb2.P_BAOZI]) * self.give_reward_gold)
            elif choice_rate == 2:
                return int(4000 / float(self.bet_history[constant_pb2.P_BAOZI]) * self.give_reward_gold)
        else:
            for robot_bet in self.robot_bet_record:
                if robot_bet[self.poker_manager.win_poker_type] > 5000000:
                    return int(5000000 * self.poker_manager.get_poker_multiple())
            choice_rate = random.choice([5] * 50 + [3] * 30 + [2] * 20 + [1] * 10)
            if choice_rate == 5:
                return int(2500000 * self.poker_manager.get_poker_multiple())
            elif choice_rate == 3:
                return int(2000000 * self.poker_manager.get_poker_multiple())
            elif choice_rate == 2:
                return int(1500000 * self.poker_manager.get_poker_multiple())
            elif choice_rate == 1:
                return int(1000000 * self.poker_manager.get_poker_multiple())

    def get_big_baozi_winner(self):
        if self.poker_manager.win_poker_type != constant_pb2.P_BAOZI:
            return

        users = []
        if len(self.table.push_players) > 0:
            users += self.table.push_players.values()
        if self.table.last_big_winner.access_service == -1:
            users += [self.table.last_big_winner]

        sort_reward_users = sorted(users, cmp=lambda x,y:cmp(x.win_gold,y.win_gold),reverse=True)

        return sort_reward_users[0]

    def real_bet_baozi_total(self):
        total_gold = 0
        for uid, bets in self.bet_players.items():
            for bet in bets:
                if bet.poker_type == constant_pb2.P_BAOZI:
                    total_gold += bet.bet_gold
        return total_gold

class PokerManager:
    def __init__(self):
        self.win_poker = None
        self.win_poker_type = None

        self.pokers_17 = []
        self.init_poker()

    def init_poker(self):
        self.pokers_17 = []
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

    def choice_poker(self):
        idx = random.randint(0, len(self.pokers_17) - 1)
        poker = self.pokers_17[idx]
        self.pokers_17.pop(idx)
        return poker

    def random_win_poker(self, table):

        # self.win_poker = goldflower.PlayerPokers(-1, Poker(3,2),Poker(2,2),Poker(1,2))
        # self.win_poker_type = constant_pb2.P_BAOZI
        # return
        # for p in self.pokers_17:
        #     if p.poker_type == constant_pb2.P_BAOZI:
        #         self.win_poker = p
        #         self.win_poker_type = p.poker_type
        #         return
        logging.info('选牌开始=============================> %s,%s'% ( table.show_baozi_time, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(table.show_baozi_time))  ))

        # 1.概率计算三条
        real_bet_total = table.game.real_bet_baozi_total()
        baozi_total = table.game.bet_history[constant_pb2.P_BAOZI]
        print real_bet_total
        logging.info('历史用户投入=%d，真实用户总投入，%d' % (table.real_gold_pool, real_bet_total))
        baozi_choice_rate = (20,40,60,80,100,)
        for p in self.pokers_17:
            if p.poker_type == constant_pb2.P_BAOZI:
                show_baozi_rate = random.randint(1, 100)
                logging.info('命中率=%d，随机数=%d' % (baozi_choice_rate[table.baozi_choice_index], show_baozi_rate))
                if show_baozi_rate <= baozi_choice_rate[table.baozi_choice_index]:
                    table.baozi_choice_index = 0
                    # 2.概率命中三条时，需验证真实用户投注池中是否有足够的钱支付
                    if table.real_pool_can_pay(real_bet_total, baozi_total):
                        logging.info('命中率，开启豹子牌型，历史投入>奖池20%')
                        self.win_poker = p
                        self.win_poker_type = p.poker_type
                        table.show_baozi_time = int(time.time()) + 60 * random.randint(70,90)
                        logging.info('命中率，新的开启时间 %d %s' % (table.show_baozi_time, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(table.show_baozi_time))))
                        return
                else:
                    logging.info('命中率，未投中，概率升级，%d' % table.baozi_choice_index)
                    table.baozi_choice_index += 1
        # 3.如果超过指定时间没有出现3条，就指定出现3条，如果金额不够，那么该流程将会维持到投注池足够为止
        if table.need_show_baozi():
            logging.info('超时，没有出现3条')
            if table.real_pool_can_pay(real_bet_total, baozi_total):
                self.choice_baozi()
                table.show_baozi_time = int(time.time()) + 60 * random.randint(70,90)
                logging.info('超时，真人投注满足，新的开启时间 %d %s' % (table.show_baozi_time, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(table.show_baozi_time))))
                return
	    elif table.robot_can_pay(real_bet_total, baozi_total):
		self.choice_baozi()
		table.show_baozi_time = int(time.time()) + 60 * random.randint(70, 90)
                logging.info('超时，机器人开启，新的开启时间 %d %s' % (table.show_baozi_time, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(table.show_baozi_time))))
		return
		

        # 4.普通选牌，主要一定不能是豹子牌型
        logging.info('普通选牌开始')
        table.real_gold_pool += real_bet_total
        assign_poker_type = lotteryconf.get_win_poker_type()
        self.get_assign_poker(assign_poker_type)
        if self.win_poker == None:
            self.recursion_assign_poker(assign_poker_type)
            return

    def choice_baozi(self):
        self.init_poker()

        for p in self.pokers_17:
            if p.poker_type == constant_pb2.P_BAOZI:
                self.win_poker = p
                self.win_poker_type = p.poker_type
                return True

        return self.choice_baozi()

    def recursion_assign_poker(self, poker_type):
        while True:
            self.init_poker()
            self.get_assign_poker(poker_type)
            if self.win_poker != None:
                break

    def get_assign_poker(self, assign_poker_type):
        for poker in self.pokers_17:
            if poker.poker_type == assign_poker_type:
                self.win_poker = poker
                self.win_poker_type = poker.poker_type
                break

    def get_poker_multiple(self):
        return lotteryconf.GAMECONF['poker_multiple'][self.win_poker_type]

class Player:
    def __init__(self, uid, access_service, user_info = None):
        self.uid = uid
        self.access_service = access_service
        self.user_info = user_info
        self.timeout = int(time.time()) + lotteryconf.GAMECONF['timeout']
        self.win_gold = 0
        self.reward_gold = 0

        self.create_unixtime = 0

    def lazy_load_user(self, dal):
        self.user_info = dal.get_user(self.uid, True)

    def modify_gold(self, session, gold):
        gold = self.user_info.modify_gold(session,int(gold))
        return gold

    def get_gold(self):
        self.gold = int(self.user_info.get_gold())
        return self.gold


    def plus_gold(self, table, gold, session = None):
        if session != None:
            self.user_info.gold += gold
            table.service.dal.save_user(session, self.user_info)
            return

        session = table.get_session()
        try:
            self.user_info.gold += gold
            table.service.dal.save_user(session, self.user_info)
        except:
            traceback.print_exc()
        finally:
            table.close_session(session)

    def get_big_winner_proto_struct(self, pb2 = None):
        if pb2 == None:
            pb2 = lottery_pb2.LotteryPlayer()
        pb2.uid = self.uid
        pb2.avatar = self.user_info.avatar
        pb2.ctime = self.create_unixtime
        pb2.gold = int(self.win_gold)
        pb2.nick = self.user_info.nick
        pb2.sex = self.user_info.sex
        pb2.vip_exp = self.user_info.vip_exp
        return pb2

    def get_big_reward_proto_struct(self, pb2 = None):
        if pb2 == None:
            pb2 = lottery_pb2.LotteryPlayer()
        pb2.uid = self.uid
        pb2.avatar = self.user_info.avatar
        pb2.ctime = self.create_unixtime
        pb2.gold = self.gold
        pb2.nick = self.user_info.nick
        pb2.vip_exp = self.user_info.vip_exp
        return pb2

    def __repr__(self):
        return '<Player uid=%d,access_service=%d,user_info=%s,timeout=%d>' % (self.uid,self.access_service,self.user_info,self.timeout)

    def plus_remain_gold(self, table, bet_user):
        if bet_user.auto_bet_now < bet_user.auto_bet_count:
            remain_auto_bet = bet_user.auto_bet_count - bet_user.auto_bet_now
            remain_gold = int(remain_auto_bet * sum([b['bet_gold'] for b in json.loads(bet_user.auto_bet_pokers)]))
            if self.user_info == None:
                self.lazy_load_user(table.service.dal)
            session = get_context('session')
            if session == None:
                session = table.get_session()
                set_context('session',session)
            self.modify_gold(session, remain_gold)
            return remain_gold
        return -1
            # self.plus_gold(table, remain_gold)


class Poker:
    def __init__(self, flower, value):
        self.flower = flower
        self.value = value

    def get_proto_struct(self, pb2 = None):
        if pb2 == None:
            pb2 = struct_pb2.Poker()
        pb2.flower = self.flower
        pb2.value = self.value
        return pb2

    def __repr__(self):
        return '%d-%d' % (self.flower, self.value)

class PokerTypeBet:
    def __init__(self, bet_gold, poker_type):
        self.bet_gold = bet_gold
        self.poker_type = poker_type

    def get_proto_struct(self, pb2 = None):
        if pb2 == None:
            pb2 = lottery_pb2.PokerTypeBet()
        pb2.poker_type = self.poker_type
        pb2.bet_gold = self.bet_gold
        return pb2

class LotteryPlayer:
    def __init__(self, uid, nick, avatar, gold, ctime = -1):
        self.uid = uid
        self.avatar = ''
        self.nick = ''
        self.gold = gold
        self.ctime = -1

    def __repr__(self):
        return '<LotteryPlayer uid=%d,avatar=%s,nick=%s,gold=%d,ctime=%d>' % \
               (self.uid,self.avatar,self.nick,self.gold,self.ctime)

    def get_proto_struct(self, pb2 = None):
        if pb2 == None:
            pb2 = lottery_pb2.LotteryPlayer()
        pb2.uid = self.uid
        pb2.avatar = self.avatar
        pb2.ctime = self.ctime
        pb2.gold = self.gold
        pb2.nick = self.nick
        return pb2

def get_reward_log(session):
    items = session.query(TUser,TLotteryRewardLog.create_unixtime,TLotteryRewardLog.reward_gold).join(TLotteryRewardLog,TLotteryRewardLog.uid == TUser.id)\
        .order_by(TLotteryRewardLog.create_unixtime.desc()).limit(20).all()
    return items


if __name__ == '__main__':
    table = Table(None)
    table.get_last_big_winner()
    print table.last_big_winner
    print table.last_big_winner.win_gold
    table.get_last_big_winner()
    print table.last_big_winner




