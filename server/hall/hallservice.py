#coding: utf-8

import json
import logging
import traceback

import sys
import binascii
import decimal
from ctypes import *
from sqlalchemy.sql import select, update, delete, insert, and_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

import random,time
from datetime import datetime
from datetime import date

from services import GameService
from message.base import *
from message.resultdef import *

from db.connect import *
from db.account import *
from db.user_goldflower import *
from db.announcement import *
from db.reward_code import *
from db.reward_code_record import *
from db.reward_task import *
from db.reward_user_log import *
from db.reward_signin import *
from db.reward_sigin_month import *
from db.shop_item import *
from db.trade import *
from db.item import *
from db.gift import *
from db.bag_gift import *
from db.bag_item import *
from db.bank_account import *
from db.user import *
from db.mail import *
from db.friend import *
from db.friend_apply import *
from db.feedback import *
from db.order import *
from db.charge_item import *
from db.charge_record import *
from db.customer_service_log import *
from db.system_achievement import *
from db.game_achievement import *
from db.pop_activity import *
from db.pop_activity_user import *
from db.flow_items import *

from proto.hall_pb2 import *
from proto.access_pb2 import *
from proto.constant_pb2 import *
from proto.struct_pb2 import *
from proto.chat_pb2 import *
from proto.reward_pb2 import *
from proto.trade_pb2 import *
from proto.bag_pb2 import *
from proto.bank_pb2 import *
from proto.mail_pb2 import *
from proto.friend_pb2 import *
from proto.rank_pb2 import *
from proto.bank_pb2 import *
from util.handlerutil import *

from config.var import *
from config.reward import *
from config.item import *
from config.sign import *
from config.mail import *
from config.broadcast import *
from helper import protohelper
from helper import cachehelper
from helper import datehelper

from dal.core import *
from hall.hallobject import *
from hall.eventsender import *
from task.achievementtask import *
from task.dailytask import *
from hall.messagemanager import *
from hall.bank import *
from helper import encryhelper
from hall.customerservice import *
from hall.bank import *
from hall.flow import *
from hall.rewardbox import *
from hall.emotion import *
from activity.luckywheel import listen_wheel_queue
from activity.luckywheel import robot_wheel_queue
from helper import systemhelper
from helper import wordhelper
from helper import chathelper

# import imp
# imp.reload(sys)
# sys.setdefaultencoding('utf8')

class HallService(GameService):

    def init(self):
        self.redis = self.server.redis
        self.da = DataAccess(self.redis)
        self.manager = Manager(self)
        self.sender = EventSender(self.manager)
        self.broadcast_list_index = 0
        gevent.spawn(self.queue_notification)
        # gevent.spawn_later(10, self.sys_broadcast_list)

        gevent.spawn(self.push_customer_message)
        # gevent.spawn_later(5, listen_wheel_queue, self.redis, self.da)
        # gevent.spawn_later(10, robot_wheel_queue, self.redis)

        self.bag = BagObject(self)
        self.hall = HallObject(self)
        self.user_gf = UserGoldFlower(self)
        self.sign = SignObject(self)
        self.friend = FriendObject(self)
        self.rank = RankObject(self)
        self.shop = ShopObject(self)
        self.item = ItemObject(self)
        self.reward = RewardObject(self)
        self.userobj = UserObject(self)
        self.vip = VIPObject(self)
        self.broke = BrokeObject(self)
        self.trade = TradeObject(self)
        self.profile = Profile(self)

        self.daliy_task = DailyTaskManager(self.redis)

        self.customer_service = CustomerService(self.redis)


    # 系统自定义广播，定时发送
    def sys_broadcast_list(self):
        while True:

            if self.broadcast_list_index >= len(BORADCAST_LIST):
                # MessageObject.push_message(self, self.redis.hkeys('online'), 12,{'message':BORADCAST_LIST[-1]})
                self.broadcast_list_index =  0
            else:
                self.broadcast_list_index =  0 if self.broadcast_list_index >= len(BORADCAST_LIST) else self.broadcast_list_index
                MessageObject.push_message(self, self.redis.hkeys('online'), PUSH_TYPE['sys_broadcast'],{'message':BORADCAST_LIST[self.broadcast_list_index]})
                self.broadcast_list_index += 1
            gevent.sleep(5)

    def setup_route(self):
        self.registe_command(QueryHallReq,QueryHallResp,self.handle_query_hall)
        self.registe_command(QueryUserReq,QueryUserResp,self.handle_query_user)
        self.registe_command(UpdateUserReq,UpdateUserResp,self.handle_update_user)
        self.registe_command(QueryRewardsReq,QueryRewardsResp,self.handle_rewards)
        self.registe_command(ReceiveRewardReq,ReceiveRewardResp,self.handle_rewards_receive)

        self.registe_command(SendChatReq,SendChatResp,self.handle_send_chat)
        self.registe_command(ReceiveCodeRewardReq,ReceiveCodeRewardResp,self.handle_code_reward)
        self.registe_command(QuerySigninRewardReq,QuerySigninRewardResp,self.handle_query_signin)
        self.registe_command(SigninReq,SigninResp,self.handle_signin)

        # 破产补助
        self.registe_command(QueryBankcruptRewardReq,QueryBankcruptRewardResp,self.handle_query_bankcrupt)
        self.registe_command(ReceiveBankcruptRewardReq,ReceiveBankcruptRewardResp,self.handle_receive_bankcrupt)

        # 转账
        self.registe_command(TransferGoldReq,TransferGoldResp,self.handle_transfer)

        # 牌桌奖励
        self.registe_command(ResetPlayRewardReq, ResetPlayRewardResp, self.handle_reset_play_reward)
        self.registe_command(ReceivePlayRewardReq, ReceivePlayRewardResp, self.handle_receive_play_reward)
        self.registe_command(RecordPlayRewardReq, RecordPlayRewardResp, self.handle_record_play_reward)

        # 商城、交易
        self.registe_command(QueryShopReq,QueryShopResp,self.handle_shop)
        self.registe_command(BuyItemReq,BuyItemResp,self.handle_shop_buy)
        self.registe_command(QueryTradeReq,QueryTradeResp,self.handle_trade)
        self.registe_command(BuyTradeReq,BuyTradeResp,self.handle_trade_buy)
        self.registe_command(SellGoldReq,SellGoldResp,self.handle_sell_gold)
        self.registe_command(OutGoldReq,OutGoldResp,self.handle_out_gold)

        # 背包
        self.registe_command(QueryBagReq,QueryBagResp,self.handle_bag)

        # 使用道具
        self.registe_command(UseItemReq,UseItemResp,self.handle_use_bag)

        # 银行
        self.registe_command(QueryBankReq,QueryBankResp,self.handle_bank)
        self.registe_command(SaveMoneyReq,SaveMoneyResp,self.handle_bank_save)

        # 信箱
        self.registe_command(SendMailReq,SendMailResp,self.handle_send_mail)
        self.registe_command(FetchMailReq,FetchMailResp,self.handle_fetch_mail)
        self.registe_command(ReceiveAttachmentReq,ReceiveAttachmentResp,self.handle_receive_mail)

        # 好友
        self.registe_command(GetFriendsReq,GetFriendsResp,self.handle_get_friends)
        self.registe_command(GetFriendAppliesReq,GetFriendAppliesResp,self.handle_get_friends_applies)
        self.registe_command(SendFriendMessageReq,SendFriendMessagetResp,self.handle_send_friends_message)
        self.registe_command(MakeFriendReq,MakeFriendResp,self.handle_make_friends)
        self.registe_command(HandleFriendApplyReq,HandleFriendApplyResp,self.handle_friends_apply)
        self.registe_command(ReceiveFriendMessageReq,ReceiveFriendMessageResp,self.handle_receive_friends_message)
        self.registe_command(RemoveFriendMessageReq,RemoveFriendMessageResp,self.handle_remove_friends)

        # 意见反馈
        self.registe_command(FeedBackReq,FeedBackResp,self.handle_feedback)

        # 注册、修改手机
        self.registe_command(BindMobileReq,BindMobileResp,self.handle_bind_mobile)

        # 活动查询
        self.registe_command(PopActivityReq,PopActivityResp,self.handle_pop_activity)

        # 买流量
        self.registe_command(QueryFlowReq,QueryFlowResp,self.handle_flow)
        self.registe_command(BuyFlowItemReq,BuyFlowItemResp,self.handle_flow_buy)

        # 发表情
        self.registe_command(SendEmotionReq,SendEmotionResp,self.handle_send_emotion)

    @USE_TRANSACTION
    def handle_send_emotion(self,session,req,resp,event):
        # print u'收到用户(%d)的发送表情请求，发给(%d)，牌桌：%d，表情：%d，总数：%d' % (req.header.user,req.body.target_player, req.body.table_id,req.body.emotion_id,req.body.count)

        tables = self.redis.keys('table_*_'+str(req.body.table_id))
        if len(tables) == 0 or tables == None:
            resp.header.result = -1
            return

        table = self.redis.hgetall(tables[0])
        # print u'打印牌桌中的用户',str(table)
        from_user = self.da.get_user(req.header.user, True)

        emotion = Emotion(self, from_user, req.body.table_id, table, req.body.target_player, req.body.emotion_id, req.body.count)
        code, result = emotion.validate()
        # print u'打印发送结果,%s, %s' % (str(code),str(result))
        if result:
            emotion.send(session)
            emotion.set_result(resp.body.result)

        resp.header.result = code

    @USE_TRANSACTION
    def handle_flow(self, session, req, resp, event):
        flow_items = session.query(TFlowItems).order_by(TFlowItems.sort.asc()).all()
        if flow_items == None or len(flow_items) <= 0:
            resp.header.result = -1
            return

        for x in flow_items:
            protohelper.set_flow_item(resp.body.items.add(), x)
        resp.header.result = 0


    @USE_TRANSACTION
    def handle_flow_buy(self, session, req, resp, event):
        flow_item = session.query(TFlowItems).filter(TFlowItems.id == req.body.shop_item_id).first()
        if flow_item == None:
            resp.header.result = -1
            return
        if flow_item.stack <= flow_item.used:
            resp.header.result = RESULT_FAILED_FLOW_STACK
            return
        # 1、手机号码验证
        # 2、手机制式验证
        user_info = self.da.get_user(req.header.user)
        if flow_item.card > user_info.flow_card:
            resp.header.result = RESULT_FAILED_FLOW_NOT_ENOUGH
            return
        flow = Flow(user_info.id, req.body.mobile, flow_item.card, flow_item.id, flow_item.name, req.body.desc)
        flow.save_order(session, flow_item)
        send_result, msg = flow.save_resp(session, flow.send_request())
        # send_result = 0
        # resp_msg = u'订购成功'
        if send_result:
            user_info.flow_card = user_info.flow_card - flow_item.card
            self.da.save_user(session, user_info)
            resp.body.incr_flow_card = -flow_item.card
            resp.body.flow_card = user_info.flow_card
            resp.header.result = 0
        else:
            resp.header.result = RESULT_FAILED_FLOW_INVALID


    # 破产补助查询
    @USE_TRANSACTION
    def handle_query_bankcrupt(self, session, req, resp, event):
        user_info = self.da.get_user(req.header.user)
        resp.body.total,resp.body.used,resp.body.gold = BrokeObject.query_broke(req.header.user,self.redis, VIP_CONF[self.vip.to_level(user_info.vip_exp)])
        resp.header.result = 0

    # 破产补助领取
    @USE_TRANSACTION
    def handle_receive_bankcrupt(self, session, req, resp, event):
        user_info = self.da.get_user(req.header.user)

        resp.header.result,resp.body.gold = BrokeObject.receive_broke(self,session,user_info, VIP_CONF[self.vip.to_level(user_info.vip_exp)])

    def cmp_friend(self,f1,f2):
        if f1.is_online == f2.is_online:
            return cmp(f1.to_uid,f2.to_uid)
        if f1.is_online:
            return 1    
        elif f2.is_online:
            return -1
        else:
            return 0

    @USE_TRANSACTION
    def handle_get_friends(self,session,req,resp,event):
        page = req.body.page
        page_size = req.body.page_size
        # friends = session.query(TFriend).filter(TFriend.apply_uid == req.header.user).offset((int(page) - 1) * page_size).limit(page_size)
        friends = session.query(TFriend).filter(TFriend.apply_uid == req.header.user).all()
        if len(friends) == 0:
            resp.body.count = 0
            resp.header.resp = 0
            return

        friend_users = []
        for friend in friends:
            friend_user = self.da.get_user(friend.to_uid)
            if friend == None or friend_user == None:
                continue
            if self.redis.hexists('online', friend.to_uid):
                friend_user.is_online = True
            else:
                friend_user.is_online = False
            friend_users.append(friend_user)

        friend_users.sort(cmp = self.cmp_friend,reverse = True)

        start = (page - 1) * page_size
        end = page * page_size

        for friend in friend_users[start:end]:
            pb = resp.body.friends.add()
            pb.avatar = friend.avatar
            pb.gold = friend.gold
            pb.uid = friend.id
            pb.nick = friend.nick
            pb.type = friend.type
            pb.is_online = friend.is_online
            pb.sex = friend.sex
            protohelper.set_room_table(pb,friend.id,self.redis)

        resp.body.count = len(friend_users)
        resp.header.result = 0
    @USE_TRANSACTION
    def handle_get_friends_applies(self,session,req,resp,event):
        page = req.body.page

        page_size = req.body.page_size

        apply_friends = session.query(TFriendApply).filter(and_(TFriendApply.to_uid == req.header.user, TFriendApply.state == 1))\
            .order_by(TFriendApply.id)\
            .offset((int(page) - 1) * page_size).limit(page_size)

        for item in apply_friends:
            temp_user = self.da.get_user(item.apply_uid)
            protohelper.set_friend_applies(resp.body.applies.add(), item, nick = temp_user.nick,avatar = temp_user.avatar, sex=temp_user.sex)

        resp.header.result = 0
    @USE_TRANSACTION
    def handle_send_friends_message(self,session,req,resp,event):
        from_user = self.da.get_user(req.header.user)
        user_message = req.body.message
        user_message = chathelper.filter_chat(user_message)
        # user_message = wordhelper.filter_replace(user_message)
        if req.body.friend_id == 10000:
            user_talk = self.customer_service.get_talk_user(req.header.user)
            user_talk.add_talk(req.header.user, req.body.message, img = from_user.avatar, is_new = True)
            self.customer_service.update_talks(req.header.user, user_talk)

            log = TCustomerServiceLog()
            log.from_user = from_user.id
            log.to_user = 10000
            log.content = req.body.message
            log.create_time = datehelper.get_today_str()
            session.add(log)
            resp.header.result = 0
            return
        elif chathelper.is_robot(session, self.redis, req.body.friend_id) and chathelper.is_humen(self.redis, req.header.user):
            user_talk = self.customer_service.get_talk_user(str(req.header.user)+'_'+str(req.body.friend_id), 'talk_robot_session')
            user_talk.add_talk(req.header.user, req.body.message, img = from_user.avatar, is_new = True)
            self.customer_service.update_talks(str(req.header.user)+'_'+str(req.body.friend_id), user_talk, 'talk_robot_session')
            resp.header.result = 0
            return

        event = create_client_event(FriendMessageEvent)
        event.body.message.message_id = self.redis.incr('message_id')
        event.body.message.from_user = req.header.user
        event.body.message.to = req.body.friend_id
        event.body.message.time = int(time.time())
        event.body.message.message = user_message
        event.body.message.from_user_nick = from_user.nick
        event.body.message.from_user_avatar = from_user.avatar
        event.body.message.from_user_sex = from_user.sex
        self.sender.send_friend_message(event, req.body.friend_id)
        self.redis.hset('message_'+str(req.body.friend_id),event.body.message.message_id,json.dumps({
            'message_id':event.body.message.message_id,
            'from_user':req.header.user,
            'to':req.body.friend_id,
            'time':int(time.time()),
            'message':user_message,
            'from_user_nick':from_user.nick,
            'from_user_avatar':from_user.avatar,
            'from_user_sex':from_user.sex
        }))
        resp.header.result = 0

    @USE_TRANSACTION
    def handle_transfer(self,session,req,resp,event):
        if req.header.user == req.body.target:
            resp.header.result = RESULT_FAILED_INVALID_TRANSFER
            return

        if req.body.target <= 10000:
            resp.header.result = RESULT_FAILED_INVALID_TRANSFER_TARGET
            return

        if req.body.gold < TRANSFER_GOLD_LOW:
            resp.header.result = RESULT_FAILED_INVALID_TRANSFER_LOW
            return

        user_info = self.da.get_user(req.header.user)
        if self.vip.to_level(user_info.vip_exp) < TRANSFER_AUTH_LEVEL:
            resp.header.result = RESULT_FAILED_INVALID_AUTH
            return

        user_bank = BankAccount(user_info)
        bank_gold = user_bank.get_bank_gold(session, req.header.user)
        all_gold = bank_gold + user_info.gold
        fee = int(req.body.gold * TRANSFER_GOLD_FEE)
        if all_gold < req.body.gold + fee:
            resp.header.result = RESULT_FAILED_NO_ENOUGH_GOLD
            return

        target_info = self.da.get_user(req.body.target)
        if target_info == None:
            resp.header.result = RESULT_FAILED_INVALID_TRANSFER_TARGET
            return

        if req.body.check == 1: # 确认
            resp.header.result = 0
            resp.body.nick = target_info.nick
            resp.body.fee = fee
            resp.body.fee_rate = int(TRANSFER_GOLD_FEE * 100)
            return

        remain_bank_gold = 0
        if bank_gold >= req.body.gold + fee:
            remain_bank_gold = bank_gold - (req.body.gold + fee)
            user_bank.save_bank_gold(session, req.header.user, remain_bank_gold)
        elif all_gold >= req.body.gold + fee:
            remain_bank_gold = bank_gold - (req.body.gold + fee)
            if remain_bank_gold < 0:
                user_bank.save_bank_gold(session, req.header.user, 0)
                user_info.gold += remain_bank_gold
        else:
            user_info.gold -= (req.body.gold + fee)

        self.da.save_user(session, user_info)
        message = MAIL_CONF['transfer_gold_target'] % (user_info.nick, user_info.id, req.body.gold)
        user_bank.send_transfer_mail(session, user_info.id, target_info,
                                     title='转账记录',
                                     content=message,
                                     type=1,
                                     gold=req.body.gold)
        MessageManager.push_notify_mail(self.redis, req.body.target)
        resp.body.result.gold = user_info.gold
        resp.body.result.diamond = user_info.diamond
        resp.body.result.incr_gold = -(req.body.gold + fee)
        resp.body.result.incr_diamond = 0
        resp.header.result = 0

    # 申请好友
    @USE_TRANSACTION
    def handle_make_friends(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)
        friend_info = self.da.get_user(req.body.target)

        if user_info is None or friend_info is None:
            resp.header.result = RESULT_FAILED_INVALID_FRIEND
            return

        # 自己+自己，直接返回
        if user_info.id == friend_info.id:
            resp.header.result = RESULT_FAILED_INVALID_FRIEND
            return

        # 不能+客服
        if req.body.target == 10000:
            resp.header.result = RESULT_FAILED_INVALID_FRIEND
            return

        # vip验证好友数限制
        my_firend_count = self.friend.get_friends_count(session, user_info.id)
        # print '------>',my_firend_count
        if self.vip.over_friend_max( self.vip.to_level(user_info.vip_exp), my_firend_count + 1 ):
            resp.header.result = RESULT_FAILED_FRIEND_MAX
            return

        target_firend_count = self.friend.get_friends_count(session, friend_info.id)
        # print '=======>',target_firend_count
        if self.vip.over_friend_max( self.vip.to_level(friend_info.vip_exp), target_firend_count + 1 ):
            resp.header.result = RESULT_FAILED_FRIEND_TARGET_MAX
            return


        resp.header.result = self.friend.make_friend(session, user_info, friend_info, req.body.message)

    # 同意/拒绝好友申请
    @USE_TRANSACTION
    def handle_friends_apply(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)
        apply_record = self.friend.get_friend_apply(session, req.body.apply_id)

        if apply_record.state == 0:
            resp.header.result = RESULT_FAILED_HAS_FRIEND
            return

        apply_user_info = self.da.get_user(apply_record.apply_uid)

        # vip验证好友数限制
        if req.body.accept:

            # 验证自己好友总数
            my_firend_count = self.friend.get_friends_count(session, user_info.id)
            if self.vip.over_friend_max( self.vip.to_level(user_info.vip_exp), my_firend_count + 1 ):
                resp.header.result = RESULT_FAILED_FRIEND_MAX
                return

            # 验证对方好友总数
            apply_firend_count = self.friend.get_friends_count(session, apply_user_info.id)
            if self.vip.over_friend_max( self.vip.to_level(apply_user_info.vip_exp), apply_firend_count + 1 ):
                resp.header.result = RESULT_FAILED_FRIEND_TARGET_MAX
                return

        self.friend.make_friend_apply(session, req.body.apply_id, req.body.accept, apply_user_info, user_info)
        resp.header.result = 0

    @USE_TRANSACTION
    def handle_receive_friends_message(self,session,req,resp,event):
        self.redis.hdel('message_'+str(req.header.user),req.body.message_id)

        resp.header.result = 0

    # 删除好友
    @USE_TRANSACTION
    def handle_remove_friends(self,session,req,resp,event):
        # 不能删除客服
        if req.body.friend_id == 10000:
            resp.header.result = RESULT_FAILED_INVALID_FRIEND
            return

        # 自己删除好友
        session.query(TFriend).filter(and_(TFriend.apply_uid == req.header.user,TFriend.to_uid == req.body.friend_id)).delete()
        # 从好友中删除自己
        session.query(TFriend).filter(and_(TFriend.apply_uid == req.body.friend_id,TFriend.to_uid == req.header.user)).delete()

        # 删除自己申请该好友的记录或者该好友申请自己好友的记录
        session.query(TFriendApply).filter(and_(TFriendApply.apply_uid == req.header.user,TFriendApply.to_uid == req.body.friend_id)).delete()
        session.query(TFriendApply).filter(and_(TFriendApply.apply_uid == req.body.friend_id,TFriendApply.to_uid == req.header.user)).delete()

        user_info_source = self.da.get_user(req.header.user)
        user_info_target = self.da.get_user(req.body.friend_id)
        self.friend.send_mail_remove_friend(session, user_info_source, user_info_target)
        MessageManager.push_notify_mail(self.redis, req.header.user)
        MessageManager.push_notify_mail(self.redis, req.body.friend_id)
        resp.header.result = 0


    # 给指定用户发送邮件
    @USE_TRANSACTION
    def handle_send_mail(self,session,req,resp,event):

        try:
            MessageObject(self.da,session).send_mail((1),{
                'to':req.body.to,
                'title':req.body.title,
                'content':req.body.content,
                'from_user':req.header.user,
                'type':0,
            })
        except Exception as e:
            # print e.message
            # print 'error...............................'
            resp.header.result = -1
            return
        resp.header.result = 0

    # 查询邮件信息
    @USE_TRANSACTION
    def handle_fetch_mail(self,session,req,resp,event):
        mails = session.query(TMail).filter(and_(TMail.to_user == req.header.user, TMail.id > req.body.max_mail_id)).order_by(desc(TMail.sent_time)).limit(100)

        item_ids = []

        for mail in mails:
            if mail.type == 1 and mail.items != None and mail.items != '':
                for s in mail.items.split(','):
                    item_ids.append(s[0])
            else:
                protohelper.set_mail(resp.body.mails.add(), mail)

        if len(item_ids) > 0:
            item_datas = ItemObject.get_items(session, item_ids)

        for mail in mails:
            if mail.type == 1 and mail.items != None and mail.items != '':
                pb_mail = resp.body.mails.add()
                protohelper.set_mail(pb_mail, mail)
                for item in mail.items.split(','):
                    for item_data in item_datas:
                        if int(item[0]) == int(item_data.id):
                            pb_item = pb_mail.items.add()
                            pb_item.id = item_data.id
                            pb_item.icon = item_data.icon
                            pb_item.name = item_data.name
                            pb_item.description = item_data.description
                            pb_item.count = int(item[2])
                            break

        resp.header.user = 0

    # 确认接收邮件
    @USE_TRANSACTION
    def handle_receive_mail(self,session,req,resp,event):
        mail = session.query(TMail).filter(TMail.id == req.body.mail_id).first()
        if mail == None or mail.state == 1:
            resp.header.result = RESULT_FAILED_MAIL
            return

        user_info = self.da.get_user(req.header.user)
        user_info.gold = user_info.gold + mail.gold
        user_info.diamond = user_info.diamond + mail.diamond
        user_info.flow_card = user_info.flow_card + mail.flow_card
        self.da.save_user(session,user_info)

        bag_obj = BagObject(session)
        if mail.items != None and mail.items != '' and len(mail.items) > 0:
            for item_str in mail.items.split(','): # 1-1,2-1,3-1
                bag_obj.save_user_item(session, req.header.user, item_str[0],item_str[2])
                item = ItemObject.get_item(session, item_str[0])

                item_add = resp.body.result.items_added.add()
                item_add.id = item.id
                item_add.name = item.name
                item_add.icon = item.icon
                item_add.count = int(item_str[2])
                item_add.description = item.description



        session.query(TMail).with_lockmode("update").filter(TMail.id == req.body.mail_id).update({
            TMail.state:1,
            TMail.received_time:int(time.time())
        })

        # 银行转账回执
        if mail.from_user != 10000:
            message = MAIL_CONF['transfer_gold_source'] % (user_info.nick, user_info.id, mail.gold)
            MessageManager.send_mail(session,
                                    mail.from_user,
                                    0,
                                    title='转账回执',
                                    content=message,
                                    type=0)
            MessageManager.push_notify_mail(self.redis, mail.from_user)


        resp.body.result.gold = user_info.gold
        resp.body.result.diamond = user_info.diamond
        resp.body.result.incr_gold = mail.gold
        resp.body.result.incr_diamond = mail.diamond
        resp.body.result.incr_flow_card = mail.flow_card
        resp.body.result.flow_card = user_info.flow_card
        resp.header.result = 0

    # 查询签到
    @USE_TRANSACTION
    def handle_query_signin(self,session,req,resp,event):
        signs = session.query(TRewardSignin).all()
        for item in signs:
            protohelper.set_signs(resp.body.rewards.add(), item)

        sign_log = session.query(TRewardSigninMonth).filter(TRewardSigninMonth.id == req.header.user).first()
        if sign_log.signin_days == -1 or sign_log.total_days == -1:
            resp.header.result = RESULT_FAILED_SIGN_ERROR
            return

        resp.body.signin_days = sign_log.signin_days
        resp.body.month_sigin_days = sign_log.total_days
        resp.header.result = 0


    # 确认接收签到
    @USE_TRANSACTION
    def handle_signin(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)
        sign_log = self.sign.get_sign_log(session, user_info.id)

        # 今日是否签到
        if self.sign.today_is_sign(sign_log):
            resp.header.result = RESULT_FAILED_TODAY_SIGNED
            return

        # 签到
        total_days,signin_days, sign_luck_max = self.sign.sign_now(session, sign_log, user_info)
        if total_days < 0  or signin_days < 0:
            resp.header.result = RESULT_FAILED_TODAY_SIGNED
            return
        # print 'vip======>',self.vip.to_level(user_info.vip_exp),user_info.vip_exp
        # print '---------------->11111|',total_days,signin_days, sign_luck_max
        # 签到奖励，需要判断vip等级
        incr_gold = 0
        incr_gold = self.sign.sign_reward(session, user_info, sign_luck_max)
        # print '---------------->222222|',incr_gold
        # print incr_gold
        add_item = {}
        # if self.vip.to_level(user_info.vip_exp) >= 1:
        incr_gold += self.sign.sign_reward_vip(session, user_info, sign_luck_max, incr_gold)
        add_item = self.sign.sign_reward_vip_item(session,user_info,sign_luck_max)

        if add_item is not None and len(add_item) >0:
            horn_item = self.item.get_item_by_id(session, add_item['horn_card'][0])
            horn_card = add_item['horn_card'].split('-')
            if int(horn_card[1]) > 0:
                protohelper.set_item_add(resp.body.result.items_added.add() ,{
                    'id':horn_item.id,
                    'icon':horn_item.icon,
                    'name':horn_item.name,
                    'description':horn_item.description,
                }, horn_card[1])
            kick_item = self.item.get_item_by_id(session, add_item['kick_card'][0])
            # print '---------->,send item 2',kick_item
            kick_card = add_item['kick_card'].split('-')
            if int(kick_card[1]) > 0:
                protohelper.set_item_add(resp.body.result.items_added.add() ,{
                   'id':kick_item.id,
                    'icon':kick_item.icon,
                    'name':kick_item.name,
                    'description':kick_item.description,
                },kick_card[1])
        # print '---------------->333333|',incr_gold
        # 累计签到，幸运日发送奖品
        item, count = self.sign.sign_luck_day(session, total_days, sign_log.id)
        if item != None and count > 0:
            if item.icon in [x.icon for x in resp.body.result.items_added]:
                for x in resp.body.result.items_added:
                    if x.icon == item.icon:
                        x.count += count
            else:
                protohelper.set_item_add(resp.body.result.items_added.add(), item, count)

        protohelper.set_result(resp.body.result, gold=user_info.gold, diamond=user_info.diamond, incr_gold=incr_gold)


        resp.header.result = 0


    # 查询大厅
    @USE_TRANSACTION
    def handle_query_hall(self,session,req,resp,event):
        if systemhelper.is_hall_close(req.header.user):
            resp.header.result = RESULT_FAILED_HALL_FIX
            return
        user_info = self.da.get_user(req.header.user, True)
        if self.hall.user_is_none(user_info):
            resp.header.result = RESULT_FAILED_ACCOUNT_EMPTY
            return

        user_gf = self.user_gf.get_user_gf(session, user_info.id)
        is_first_login = False
        if user_gf == None:
            # 需要创建该条记录,说明该用户为首次使用该游戏
            # 初始化 user_goldflowe表和bag_item表记录
            self.user_gf.add_user_gf(session, user_info.id, user_info.channel)
            self.bag.user_init(session, req.header.user)
            self.sign.sign_init(session, req.header.user)
            SystemAchievement(session, req.header.user).finish_first_login()
            self.userobj.new_user_broadcast(user_info)
            BankAccount(user_info).init_user_bank(session)

            is_first_login = True

        protohelper.set_brief_hall(resp.body.brief, user_info)

        # 获取用户大厅信息
        self.hall.load_user_hall(session, user_info, user_gf, req.body.max_announcement_id, req.body.max_mail_id, is_first_login)

        # 设置大厅protobuf
        protohelper.set_hall(resp.body, self.hall)




        # 有好友信息就推送出去
        # if self.hall.has_friend_count > 0:
            # self.friend.load_friend_message(user_info.id)
            # self.friend.send_friend_message(user_info.id)
        friend_messages = self.redis.hgetall('message_'+str(req.header.user))
        if friend_messages != None and len(friend_messages) > 0:
            # friend_messages = json.loads(friend_messages)
            for msg_id, message in friend_messages.items():
                message = json.loads(message)
                event = create_client_event(FriendMessageEvent)
                event.body.message.message_id = int(msg_id)
                event.body.message.from_user = int(message.get('from_user'))
                event.body.message.to = int(message.get('to'))
                event.body.message.time = int(message.get('time'))
                event.body.message.message = message.get('message')
                event.body.message.from_user_nick = message.get('from_user_nick', '')
                event.body.message.from_user_avatar = message.get('from_user_avatar', '')
                event.body.message.from_user_sex = message.get('from_user_sex', 0)
                self.sender.send_friend_message(event, event.body.message.to)

        resp.header.result = 0


    # 查询用户
    @USE_TRANSACTION
    def handle_query_user(self,session,req,resp,event):

        if req.body.uid <= 0 or req.body.uid == None:
            resp.header.result = -1
            return
        user_info = session.query(TUser).filter(TUser.id == req.body.uid).first()
        if user_info == None:
            resp.header.result = RESULT_FAILED_ACCOUNT_EMPTY
            return

        user_gf = session.query(TUserGoldFlower).filter(TUserGoldFlower.id == req.body.uid).first()
        if user_gf == None:
            resp.header.result = -1
            return

        account = session.query(TAccount).filter(TAccount.id == req.body.uid).first()
        if account is not  None and account.mobile is not None:
            resp.body.player.mobile = account.mobile

        is_friend = session.query(TFriend).filter(and_(TFriend.apply_uid == req.header.user, TFriend.to_uid == req.body.uid)).count()
        if is_friend > 0:
            resp.body.player.is_friend = True
        else:
            resp.body.player.is_friend = False


        avatar_verify_result = self.userobj.get_avatar_verify(session, user_info.id)

        gold_top_index = self.redis.zrank('rank_gold', user_info.id)
        protohelper.set_player(resp.body.player,gold_top_index,user_info,user_gf)
        resp.body.update_avatar_url = UPDATE_AVATAR_URL
        resp.body.is_charge = True if user_info.is_charge else False
        resp.body.flow_card = user_info.flow_card
        if avatar_verify_result != None:
            resp.body.avatar_verify = avatar_verify_result
        resp.header.result = 0
    # 更新用户
    @USE_TRANSACTION
    def handle_update_user(self,session,req,resp,event):
        if encryhelper.has_emoji(req.body.nick):
            resp.header.result = -1
            return
        if encryhelper.has_emoji(req.body.sign):
            resp.header.result = -1
            return
        user_info = self.da.get_user(req.header.user)

        if len(req.body.nick) > 0:
            # 任务-成就任务：修改昵称
            if req.body.nick != user_info.nick:
                SystemAchievement(session, user_info.id, is_notify = True, redis = self.redis).finish_change_nick()
            user_info.nick = req.body.nick
        if len(req.body.birthday) > 0:
            user_info.birthday = req.body.birthday
        if len(req.body.sign)  > 0:
            user_info.sign = req.body.sign
        if len(req.body.sex) > 0:
            user_info.sex = req.body.sex

        self.da.save_user(session, user_info)

        # 返回result标准格式
        # protohelper.set_result(resp.body.result, gold = user_info.gold,
        #                    diamond = user_info.diamond,
        #                    incr_gold = self.reward.result['incr_gold'])
        # for item in self.reward.result['items_add']:
        #     protohelper.set_item_add(resp.body.result.items_added.add(), item, item['count'])

        resp.header.result = 0

    # 查询奖励
    @USE_TRANSACTION
    def handle_rewards(self,session,req,resp,event):
        rewards = session.query(TRewardTask).order_by(desc(TRewardTask.is_daily)).all()

        items = self.item.get_itme_by_all(session)
        if len(rewards) <= 0:
            resp.header.result = -1
            return

        daily_task = self.daliy_task.get_daily_task(req.header.user)
        achievement_tasks = SystemAchievement(session, req.header.user)

        for reward in rewards:
            pb_reward = resp.body.rewards.add()
            protohelper.set_reward(pb_reward, reward)
            if reward.is_daily == 1:
                pb_reward.state = daily_task.get_task_state(reward.id)
            else:
                pb_reward.state = achievement_tasks.get_task_state(reward.id)
            if reward.items is None or reward.items == '':
                continue
            for split_item in reward.items.split(','):
                for item in items:
                    if item.id == int(split_item[0]):
                        protohelper.set_item_add(pb_reward.items.add(), {
                            'id':item.id,
                            'name':item.name,
                            'icon':item.icon,
                            'description':item.description,
                        }, split_item[2])


        resp.header.result = 0
    # 接收奖励
    @USE_TRANSACTION
    def handle_rewards_receive(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)
        # print '=====>before',user_info.gold,user_info.diamond
        # 给用户奖励
        result = self.reward.give_user_reward(session, user_info, req.body.reward_id)
        if result is None or len(result) <= 0:
            resp.header.result = RESULT_FAILED_INVALID_REWARD
            return

        # print '=====>after',user_info.gold,user_info.diamond
        # print '====>result',result
        # 返回result标准格式
        protohelper.set_result(resp.body.result, gold = user_info.gold,
                           diamond = user_info.diamond,
                           incr_gold = result.get('incr_gold',0),
                           incr_diamond = result.get('incr_diamond', 0),
                           incr_flow_card = result.get('incr_flow_card', 0),
                           flow_card = result.get('flow_card', 0))
        for item in result['items_add']:
            protohelper.set_item_add(resp.body.result.items_added.add(), item, item['count'])

        resp.header.result = 0

    # 发送聊天（牌桌内|牌桌外）
    @USE_TRANSACTION
    def handle_send_chat(self, session, req, resp, event):
        rs, ex_time = wordhelper.talk_no(self.redis, req.header.user)
        if rs:
            resp.header.result = RESULT_FAILED_NO_TALK
            # resp.body.no_talk_sec = ex_time # 禁言秒数，0=永久禁言
            return

        user_info = self.da.get_user(req.header.user)
        if user_info == None:
            return
        user_message = req.body.message

        user_message = chathelper.filter_chat(user_message)

        if req.body.chat_type == CHAT_WORD:  # broadcast


            # 世界聊天，需要具有聊天道具卡
            if self.bag.has_item(session, req.header.user, ITEM_MAP['horn'][0]) == False:
                resp.header.result = RESULT_FAILED_INVALID_BAG
                return

            if self.bag.use_horn_item(session, req.header.user, 1) > 0:
                self.bag.send_horn_item(self.redis.hkeys('online'), user_info, user_message)

            if '*' not in user_message or not encryhelper.has_emoji(user_message):
                horn_history_len = self.redis.llen('horn_history')
                if horn_history_len >= 20:
                    self.redis.lpop('horn_history')
                self.redis.rpush('horn_history', json.dumps(
                        {'message': user_message, 'uid': user_info.id, 'nick_id': user_info.id, 'nick': user_info.nick,
                         'vip_exp': user_info.vip_exp}))

            # 完成喊话任务
            DailyTaskManager(self.redis).use_horn(req.header.user)
        elif req.body.chat_type == CHAT_ZJH:
            # no_talk_ttl = wordhelper.talk_expire(self.redis, req.header.user, req.body.table_id)
            # if wordhelper.talk_expire(self.redis, req.header.user, req.body.table_id) == False:
            #    resp.header.result = RESULT_FAILED_NO_TALK
            #    resp.body.no_talk_sec = no_talk_ttl
            # return
            if wordhelper.talk_repeat(self.redis, user_info.id, req.body.message):
                self.notify_one(user_info.id, user_message, req.body.table_id, req.body.chat_type)
                resp.header.result = 0
                return
            keys = self.redis.keys("table_*_" + str(req.body.table_id))
            if len(keys) != 1:
                resp.header.result = -1
                return
            table = self.redis.hgetall(keys[0])
            if table != None:
                event = create_client_event(ChatEvent)
                event.body.sender = req.header.user
                event.body.table_id = req.body.table_id
                event.body.chat_type = req.body.chat_type
                event.body.message = user_message
                event_data = event.encode()
                users = table.keys()
                for user in users:
                    access_service = self.redis.hget("online", user)
                    if access_service == None:
                        continue
                    access_service = int(access_service)
                    user = int(user)
                    self.send_client_event(access_service, user, event.header.command, event_data)
        elif req.body.chat_type == CHAT_TEXAS:
            # no_talk_ttl = wordhelper.talk_expire(self.redis, req.header.user, req.body.table_id)
            # if wordhelper.talk_expire(self.redis, req.header.user, req.body.table_id) == False:
            #    resp.header.result = RESULT_FAILED_NO_TALK
            # resp.body.no_talk_sec = no_talk_ttl
            # return


            if wordhelper.talk_repeat(self.redis, user_info.id, req.body.message):
                self.notify_one(user_info.id, user_message, req.body.table_id, req.body.chat_type)
                resp.header.result = 0
                return
            keys = self.redis.keys("texas_*_" + str(req.body.table_id))
            if len(keys) != 1:
                resp.header.result = -1
                return
            table = self.redis.hgetall(keys[0])
            if table != None:
                event = create_client_event(ChatEvent)
                event.body.sender = req.header.user
                event.body.table_id = req.body.table_id
                event.body.chat_type = CHAT_TEXAS
                event.body.message = user_message
                event_data = event.encode()
                users = table.keys()
                for user in users:
                    access_service = self.redis.hget("online", user)
                    if access_service == None:
                        continue
                    access_service = int(access_service)
                    user = int(user)
                    self.send_client_event(access_service, user, event.header.command, event_data)
        elif req.body.chat_type == CHAT_WAR:  # 红黑大战聊天
            # if wordhelper.talk_expire(self.redis, req.header.user, req.body.table_id) == False:
            #        resp.header.result = RESULT_FAILED_NO_TALK
            #        return

            if wordhelper.talk_repeat(self.redis, user_info.id, req.body.message):
                self.notify_one(user_info.id, user_message, req.body.table_id, req.body.chat_type)
                resp.header.result = 0
                return
            if self.redis.exists("war_online"):
                event = create_client_event(ChatEvent)
                event.body.sender = req.header.user
                event.body.table_id = req.body.table_id
                event.body.chat_type = CHAT_WAR
                event.body.message = user_message
                event_data = event.encode()
                users = self.redis.hkeys("war_online")
                # print users, type(users)
                for user in users:
                    access_service = self.redis.hget("online", user)
                    if access_service == None:
                        continue
                    access_service = int(access_service)
                    user = int(user)
                    self.send_client_event(access_service, user, event.header.command, event_data)
        else:
            resp.header.result = -2
            return
        resp.header.result = 0

    # 奖励卷代码
    @USE_TRANSACTION
    def handle_code_reward(self,session,req,resp,event):
        reward_code = session.query(TRewardCode).filter(TRewardCode.code == req.body.code).first()

        if reward_code == None:
            resp.header.result = RESULT_FAILED_CODE
            return

        if time.mktime(reward_code.expired_at.timetuple()) <= time.time():
            resp.header.result = RESULT_FAILED_CODE_EXPIRED
            return

        if reward_code.total <= reward_code.used:
            resp.header.result = RESULT_FAILED_CODE_FILL
            return

        reward_code_log = session.query(TRewardCodeRecord).filter(and_(TRewardCodeRecord.code_id == reward_code.id, \
                                                                       TRewardCodeRecord.uid == req.header.user)).first()
        if reward_code_log != None:
            resp.header.result = RESULT_FAILED_CODE_USED
            return
        try:
            code_record = TRewardCodeRecord()
            code_record.code_id = reward_code.id
            code_record.uid = req.header.user
            code_record.create_time = time.strftime("%Y-%m-%d %H:%M:%S")
            session.add(code_record)

            session.query(TRewardCode).with_lockmode("update").filter(and_(TRewardCode.code == req.body.code, TRewardCode.total>TRewardCode.used)).update({
                        TRewardCode.used: TRewardCode.used + 1,
            })

            session.query(TUser).with_lockmode("update").filter(TUser.id == req.header.user).update({
                        TUser.gold: TUser.gold + reward_code.gold,
                        TUser.diamond: TUser.diamond + reward_code.diamond
            })

            user_info = self.da.get_user(req.header.user)
            user_info.gold = user_info.gold +reward_code.gold
            user_info.diamond = user_info.diamond +reward_code.diamond
            self.da.save_user(session, user_info)

            MessageManager.push_notify_mail(self.redis, req.header.user)
            MessageManager.send_mail(session, 
                                    req.header.user, 
                                    0, 
                                    title='兑奖码礼包领取', 
                                    content=MAIL_CONF['use_code'] % reward_code.description,
                                    type=0)

        except Exception as e:
            # print e.message
            resp.header.result = RESULT_FAILED_CODE
            return

        resp.body.result.gold = user_info.gold
        resp.body.result.diamond = user_info.diamond
        resp.body.result.incr_gold = reward_code.gold
        resp.body.result.incr_diamond = reward_code.diamond
        resp.header.result = 0
    # 查询商品
    @USE_TRANSACTION
    def handle_shop(self,session,req,resp,event):
        shopitem = session.query(TShopItem).all()
        items = session.query(TItem).all()
        for spi in shopitem:
            protohelper.set_shop_item(resp.body.items.add(), spi, items)
        resp.header.result = 0

    # 购买商品
    @USE_TRANSACTION
    def handle_shop_buy(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)

        if req.body.count <= 0:
            resp.header.result = RESULT_FAILED_SHOP
            return

        if self.shop.buy_item(session, user_info, req.body.shop_item_id, req.body.count) == False:
            resp.header.result = RESULT_FAILED_SHOP
            return

        # 每日任务
        DailyTaskManager(self.redis).buy_diamond(req.header.user)

        # type,1=金币，2=道具

        protohelper.set_result(resp.body.result, gold = user_info.gold, diamond = user_info.diamond,
                           incr_gold =(self.shop.shop_item.shop_gold + self.shop.shop_item.extra_gold), incr_diamond = -(self.shop.shop_item.total))

        protohelper.set_item_add(resp.body.result.items_added.add(),
                             self.shop.get_item_by_shop(session, req.body.shop_item_id),req.body.count)
        # 发送购买记录邮件
        self.shop.send_mail(session, user_info, req.body.shop_item_id, req.body.count)

        # 邮件提醒
        MessageManager.push_notify_mail(self.redis, user_info.id)
        # 强制更新用户信息，避免在红黑牌桌时不更新信息
        logging.info(u'ljq-用户%d购买金币增量：%d，总量 %d' % (user_info.id,resp.body.result.incr_gold,user_info.gold))
        self.da.get_user(req.header.user, True)
        # 更新用户信息队列
        self.redis.lpush('war_user_update', json.dumps({'uid':req.header.user,'gold':resp.body.result.incr_gold,'diamond':resp.body.result.incr_diamond,'vip_exp':user_info.vip_exp}))
        resp.header.result = 0


    # 查询交易记录
    @USE_TRANSACTION
    def handle_trade(self,session,req,resp,event):
        page = req.body.page
        page_size = req.body.page_size
        can_buy = req.body.can_buy
        user_info = self.da.get_user(req.header.user)


        data_count, items = self.shop.get_lists(session, req.body.page, req.body.page_size,user_info, req.body.can_buy, req.body.my_sell)



        # other data
        for item in items:
            protohelper.set_trades(resp.body.trades.add(), item,self.da.get_user(item.seller))
        resp.body.total = data_count
        resp.header.user = 0

    # 购买交易
    @USE_TRANSACTION
    def handle_trade_buy(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)


        # 权限验证，vip1及以上等级可在金币交易中购买金币交易
        if self.vip.denied_buy_gold( self.vip.to_level(user_info.vip_exp) ):
            resp.header.result = RESULT_FAILED_INVALID_AUTH
            return

        # 是否下架，验证
        trade = session.query(TTrade).filter(and_(TTrade.id == req.body.trade_id)).first()
        if trade.status == -1 or trade.status == 1:
            resp.header.result = RESULT_FAILED_INVALID_SHOP
            return

        # 出售商品验证
        trade = session.query(TTrade).filter(and_(TTrade.id == req.body.trade_id, TTrade.status == 0)).first()
        if trade is None or user_info.diamond < trade.diamond:
            resp.header.result = RESULT_FAILED_SHOP_DIAMOND
            return

        try:
            # 修改交易记录
            result = session.query(TTrade).with_lockmode("update").filter(and_(TTrade.id == req.body.trade_id, \
                                                                               TTrade.status != 1, TTrade.diamond <= user_info.diamond)).update({
                TTrade.buyer : user_info.id,
                TTrade.buy_time : time.strftime('%Y-%m-%d %H:%M:%S'),
                TTrade.status : 1,
            })
            if result != 1:
                resp.header.result = RESULT_FAILED_SHOP
                return
            # 修改出售者数据，通过邮件领取的方式
            # seller_info = self.da.get_user(trade.seller)
            # seller_info.diamond= seller_info.diamond + trade.diamond
            # self.da.save_user(session, seller_info)

            # 修改购买者数据
            user_info.gold = user_info.gold + trade.gold
            user_info.diamond = user_info.diamond - trade.diamond
            self.da.save_user(session,user_info)
        except Exception as e:
            # print e.message
            resp.header.result = RESULT_FAILED_SHOP
            return

        # 发送当前用户的消费记录
        t = time.time()
        content = MAIL_CONF['trade_buy_gold'] % (trade.diamond ,trade.gold)
        MessageObject.send_mail(session, user_info, 0, \
                                title=u'消费记录',
                                content=content,
                                type=0, ) # 不带附件
        MessageManager.push_notify_mail(self.redis, user_info.id)
        # 给挂售的用户发领取邮件
        content = MAIL_CONF['trade_sell_success'] % (trade.gold,trade.diamond)
        MessageObject.send_mail(session, trade.seller, 0,\
                                title=u'领取挂售钻石',
                                content=content,
                                type=1, # 带附件
                                diamond=trade.diamond)
        MessageManager.push_notify_mail(self.redis, trade.seller)
        resp.body.result.gold = user_info.gold
        resp.body.result.diamond = user_info.diamond
        resp.body.result.incr_gold = trade.gold
        resp.body.result.incr_diamond = -trade.diamond
        # 强制更新用户信息，避免在红黑牌桌时不更新信息
        self.da.get_user(req.header.user, True)
        # 更新用户信息队列
        self.redis.lpush('war_user_update', json.dumps({'uid':req.header.user}))
        resp.header.result = 0
    # 出售金币
    @USE_TRANSACTION
    def handle_sell_gold(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)

        if req.body.diamond <= 0 or req.body.gold <= 0:
            resp.header.result = RESULT_FAILED_SHOP
            return

        # 权限验证，vip2及以上等级可在金币交易中出售金币
        if self.vip.denied_sell_gold(self.vip.to_level(user_info.vip_exp)):
            resp.header.result = RESULT_FAILED_INVALID_AUTH
            return

        # 扣税
        if user_info.gold < (TAX_NUM * req.body.gold) + req.body.gold:
            resp.header.result = RESULT_FAILED_INVALID_GOLD
            return


        trade = TTrade()
        trade.seller = req.header.user
        trade.gold = req.body.gold
        trade.diamond = req.body.diamond
        trade.sell_time = time.strftime('%Y-%m-%d %H:%M:%S')
        trade.rate = float(req.body.diamond) / float(req.body.gold) * float(SELL_RATE)
        trade.fee = int(TAX_NUM * req.body.gold)
        trade.status = 0
        session.add(trade)

        tax_gold = int((TAX_NUM * req.body.gold) + req.body.gold)
        user_info.gold = user_info.gold - tax_gold
        self.da.save_user(session,user_info)

        # 广播，当前用户挂售金币成功
        self.shop.sell_gold_brodacast(user_info, req.body.gold, req.body.diamond)

        resp.body.result.gold = user_info.gold
        resp.body.result.diamond = user_info.diamond
        resp.body.result.incr_gold = -tax_gold
        # 强制更新用户信息，避免在红黑牌桌时不更新信息
        self.da.get_user(req.header.user, True)
        # 更新用户信息队列
        self.redis.lpush('war_user_update', json.dumps({'uid':req.header.user}))
        resp.header.result = 0
    # 下架金币
    @USE_TRANSACTION
    def handle_out_gold(self,session,req,resp,event):
        # -1 下架，0=交易中，1=被买走
        user_info = self.da.get_user(req.header.user)
        if self.shop.sell_out(session, user_info, req.body.trade_id) == False:
            resp.header.result = RESULT_FAILED_SHOP
            return

        trade = self.shop.get_trade(session, req.body.trade_id)
        protohelper.set_result(resp.body.result, gold = user_info.gold, diamond = user_info.diamond,
                               incr_gold = trade.gold, incr_diamond = 0)

        # 强制更新用户信息，避免在红黑牌桌时不更新信息
        self.da.get_user(req.header.user, True)
        self.redis.lpush('war_user_update', json.dumps({'uid':req.header.user}))

        resp.header.result = 0




    # 查询背包
    @USE_TRANSACTION
    def handle_bag(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)
        if user_info == None:
            resp.header.result = -1
            return

        items = session.query(TItem).all()
        # gifts = session.query(TGift).all()

        # load item
        user_items = session.query(TBagItem).filter(TBagItem.uid == req.header.user).all()
        for user_item in user_items:
            protohelper.set_bag_item(resp.body.items.add(), user_item, items)

        # load bag
        # user_gifts = session.query(TBagGift).filter(TBagGift.uid == req.header.user).all()
        # for user_gift in user_gifts:
        #     protohelper.set_bag_gift(resp.body.gifts.add(), user_gift, gifts)

        resp.header.result = 0

    # 使用背包内的道具
    @USE_TRANSACTION
    def handle_use_bag(self,session,req,resp,event):

        # 暂时只有vip经验卡能使用到该方法
        if self.bag.has_item(session, req.header.user, req.body.item_id, req.body.count) == False:
            resp.header.result = RESULT_FAILED_INVALID_BAG
            return

        # 使用道具
        result = self.bag.use_user_item(session, req.header.user, req.body.item_id, countof=req.body.count)
        if result <= 0:
            resp.header.result = RESULT_FAILED_INVALID_BAG
            return

        # 加vip经验
        user_info = self.da.get_user(req.header.user)
        user_info.vip_exp = 0 if user_info.vip_exp <= 0 else user_info.vip_exp
        old_vip_level = self.vip.to_level(user_info.vip_exp)
        for times in range(req.body.count):
            user_info.vip_exp = user_info.vip_exp + ItemObject.get_item_conf(req.body.item_id)[0]
        self.da.save_user(session, user_info)



        new_vip_level = self.vip.to_level(user_info.vip_exp)
        # vip升级广播
        if old_vip_level < new_vip_level:
            self.vip.level_up_broadcast(user_info.id, user_info.nick, user_info.vip_exp)
            # 完成vip任务
            SystemAchievement(session, user_info.id, is_notify = True, redis = self.redis).finish_upgrade_vip(new_vip_level)

        # 返回数据
        resp.body.result.vip_exp = user_info.vip_exp
        item = ItemObject.get_item(session, req.body.item_id)
        pb = resp.body.result.items_removed.add()
        pb.id = item.id
        pb.name = item.name
        pb.icon = item.icon
        pb.description = item.description
        pb.count = req.body.count
        # 强制更新用户信息，避免在红黑牌桌时不更新信息
        self.da.get_user(req.header.user, True)
        self.redis.lpush('war_user_update',json.dumps({'uid':user_info.id}))
        resp.header.result = 0

    # 查询银行
    @USE_TRANSACTION
    def handle_bank(self,session,req,resp,event):

        bank_account = session.query(TBankAccount).filter(TBankAccount.uid == req.header.user).first()

        user_info = self.da.get_user(req.header.user)

        resp.body.gold = bank_account.gold if bank_account != None else 0
        resp.body.limit = VIP_CONF[self.vip.to_level(user_info.vip_exp)]['bank_max']
        resp.body.next_vip_limit = VIP_CONF[-1]['bank_max'] if (self.vip.to_level(user_info.vip_exp) + 1) >= len(VIP_CONF) else VIP_CONF[self.vip.to_level(user_info.vip_exp) + 1]['bank_max']
        resp.header.user = 0
    # 存钱到银行
    @USE_TRANSACTION
    def handle_bank_save(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)

        # print '---->1'
        # vip 银行存款限制
        if self.vip.over_bank_max(self.vip.to_level(user_info.vip_exp), req.body.gold):
            resp.header.result = RESULT_FAILED_BANK_MAX
            return
        # print '---->2'
        if user_info.gold < req.body.gold:
            resp.header.result = RESULT_FAILED_INVALID_GOLD
            return
        # print '---->3'
        if VIP_CONF[self.vip.to_level(user_info.vip_exp)]['bank_max'] > 0:
            bank_account = session.query(TBankAccount).filter(TBankAccount.uid == req.header.user).first()
            if bank_account == None:
                bank_account = TBankAccount()
                bank_account.uid = req.header.user
                bank_account.gold = int(req.body.gold)
                bank_account.diamond = 0
                bank_account.update_time = datehelper.get_today_str()
                bank_account.create_time = datehelper.get_today_str()
                session.add(bank_account)
        # if bank_account == None or VIP_CONF[user_info.vip]['bank_max'] <= 0:
        # print '----->4'
        if req.body.gold < 0:
            if bank_account.gold < abs(req.body.gold):
                resp.header.result = RESULT_FAILED_INVALID_GOLD
                return
        else:
            if (bank_account.gold + req.body.gold) > VIP_CONF[self.vip.to_level(user_info.vip_exp)]['bank_max']:
                resp.header.result = RESULT_FAILED_INVALID_GOLD
                return

        session.query(TBankAccount).filter(TBankAccount.uid == req.header.user).update({
            TBankAccount.gold: TBankAccount.gold + req.body.gold
        })
        # print '----->5',user_info.gold,type(user_info.gold),req.body.gold,type(req.body.gold)
        if req.body.gold > 0:
            user_info.gold = user_info.gold - int(req.body.gold)
        elif req.body.gold < 0:
            user_info.gold = user_info.gold + int(abs(req.body.gold))
        # print '----->6',user_info.gold,type(user_info.gold),req.body.gold,type(req.body.gold)
        self.da.save_user(session, user_info)
        resp.body.result.gold = user_info.gold
        resp.body.result.diamond = user_info.diamond
        resp.header.result = 0
    # 重置牌桌奖励记数
    @USE_TRANSACTION
    def handle_reset_play_reward(self,session,req,resp,event):
        try:
            key = 'round_reward:'+str(req.header.user)
            self.redis.hmset(key, {'total':REWARD_PLAY_ROUND[0][0],'current':0})
            self.redis.expireat(key, int(datehelper.next_midnight_unix(delay_sec = 5)) )
        except Exception as e:
            # print e.message
            resp.header.result -1
            return
        resp.header.result = 0

    # 领取牌桌奖励
    @USE_TRANSACTION
    def handle_receive_play_reward(self,session,req,resp,event):
        key = 'round_reward:'+str(req.header.user)
        if self.redis.exists(key) == False:
            resp.header.result = RESULT_FAILED_RECEIVE_REWARD
            return

        record = self.redis.hgetall(key)
        if int(record['total']) != int(record['current']):
            resp.header.result = RESULT_FAILED_RECEIVE_REWARD
            return

        round_reward_conf = RewardObject.get_conf(int(record['total']))

        if round_reward_conf == None:
            resp.header.result = RESULT_FAILED_RECEIVE_REWARD
            return
        next_round_reward_conf = RewardObject.get_next_round(int(record['total']))

        self.redis.hmset(key,{'total':next_round_reward_conf[0],'current':0})
        user_info = self.da.get_user(req.header.user)
        user_info.gold = user_info.gold + random.randint(round_reward_conf[1],round_reward_conf[2])
        self.da.save_user(session, user_info)

        resp.body.next_round = next_round_reward_conf[0]
        resp.body.result.gold = user_info.gold
        resp.header.result = 0



    # 记录牌桌次数
    @USE_TRANSACTION
    def handle_record_play_reward(self,session,req,resp,event):
        key = 'round_reward:'+str(req.header.user)
        if self.redis.exists(key) == False:
            self.redis.hmset(key, {'total':REWARD_PLAY_ROUND[0][0],'current':0})
            self.redis.expireat(key, int(datehelper.next_midnight_unix(delay_sec = 5)) )

        total = int(self.redis.hget(key,'total'))
        current = int(self.redis.hget(key,'current'))
        if total > current:
            current = int(self.redis.hincrby(key, 'current'))
        resp.body.total = total
        resp.body.current = current
        resp.header.result = 0

    # 意见反馈
    @USE_TRANSACTION
    def handle_feedback(self,session,req,resp,event):
        if len(req.body.message) <= 0 or len(req.body.contact) <= 0:
            resp.header.result = RESULT_FAILED_INVALID_FEEDBACK
            return

        feedback = TFeedBack()
        feedback.uid = req.header.user
        feedback.message = req.body.message
        feedback.contact = req.body.contact
        feedback.create_time = datehelper.get_today_str()
        feedback.status = -1
        session.add(feedback)
        resp.header.result = 0


    @USE_TRANSACTION
    def handle_bind_mobile(self,session,req,resp,event):
        # todo ... 验证码验证




        # 绑定类型：1：新用户绑定（password必传）设置密码,  2：绑定新手机号（password不传）, 3：解绑旧手机资格校验（password不传）
        if req.body.bind_type == 1:
            verify_code = req.body.verify_code
            code = self.redis.get('sms_'+req.body.mobile)
            if code == None:
                resp.header.result = RESULT_FAILED_VERIFY_ERROR
                return

            if int(code) != int(verify_code):
                resp.header.result = RESULT_FAILED_VERIFY_ERROR
                return

            if req.body.password is None:
                resp.header.result = RESULT_FAILED_PASSWORD_EMPTY
                return

            user_mobile = session.query(TAccount).filter(TAccount.mobile == req.body.mobile).first()
            if user_mobile != None and user_mobile.mobile != None and len(user_mobile.mobile) > 0 and user_mobile.state == -2:
                resp.header.result = RESULT_FAILED_ACCOUNT_DISABLED
                return

            if user_mobile is not None:
                resp.header.result = RESULT_FAILED_MOBILE_EXISTS
                return

            self.profile.bind_mobile(session, req.header.user, req.body.mobile, req.body.password)

            SystemAchievement(session, req.header.user, is_notify = True, redis = self.redis).finish_bind_mobile()

        elif req.body.bind_type == 2:
            verify_code = req.body.verify_code
            code = self.redis.get('sms_'+req.body.mobile)
            if code == None:
                resp.header.result = RESULT_FAILED_VERIFY_ERROR
                return

            if int(code) != int(verify_code):
                resp.header.result = RESULT_FAILED_VERIFY_ERROR
                return

            user_mobile = session.query(TAccount).filter(TAccount.mobile == req.body.mobile).first()

            if user_mobile != None and user_mobile.mobile != None and len(user_mobile.mobile) > 0 and user_mobile.state == -2:
                resp.header.result = RESULT_FAILED_ACCOUNT_DISABLED
                return

            if user_mobile is not None:
                resp.header.result = RESULT_FAILED_MOBILE_EXISTS
                return

            self.profile.bind_mobile(session, req.header.user, req.body.mobile)

            SystemAchievement(session, req.header.user, is_notify = True, redis = self.redis).finish_bind_mobile()

        elif req.body.bind_type == 3:
            verify_code = req.body.verify_code
            code = self.redis.get('sms_'+req.body.mobile)
            if code == None:
                resp.header.result = RESULT_FAILED_VERIFY_ERROR
                return

            if int(code) != int(verify_code):
                resp.header.result = RESULT_FAILED_VERIFY_ERROR
                return

        elif req.body.bind_type == 4:
            user_mobile = session.query(TAccount).filter(TAccount.mobile == req.body.mobile).first()

            if user_mobile != None and user_mobile.mobile != None and len(user_mobile.mobile) > 0 and user_mobile.state == -2:
                resp.header.result = RESULT_FAILED_ACCOUNT_DISABLED
                return

            if user_mobile is not None:
                resp.header.result = RESULT_FAILED_MOBILE_EXISTS
                return

        resp.header.result = 0

    @USE_TRANSACTION
    def handle_pop_activity(self,session,req,resp,event):
        charge_item = session.query(TPopActivity).filter(and_(TPopActivity.start <= datehelper.get_today_str(),TPopActivity.end >= datehelper.get_today_str(),TPopActivity.status == 1)).first()

        if charge_item == None:
            resp.header.result = RESULT_FAILED_NO_ACTIVITY
            return

        used_activity = session.query(TPopActivityUser).filter(and_(TPopActivityUser.uid == req.header.user, TPopActivityUser.activity_id == charge_item.id)).first()
        if used_activity != None:
            resp.header.result = RESULT_FAILED_ACTIVITY
            return

        resp.body.id = charge_item.id
        resp.body.title = charge_item.title
        resp.body.desc = charge_item.description
        resp.body.gold = charge_item.gold
        resp.body.money = int(decimal.Decimal(charge_item.money) * 100)
        resp.body.end_time = int(time.mktime(charge_item.end.timetuple())) - int(time.time())
        resp.header.result = 0


    # 获取通用result结果
    def get_result(self,user,resp):
        resp.body.result.gold = user.gold
        resp.body.result.diamond = user.diamond


    # 官方消息推送
    def push_customer_message(self):
        while True:
            _,msgid_user = self.redis.brpop("customer_msgs")

            msg_id, user = msgid_user.split('_')
            message = self.redis.hget('message_'+str(user), msg_id)
            message = json.loads(message)
            event = create_client_event(FriendMessageEvent)
            event.body.message.message_id = int(msg_id)
            event.body.message.from_user = int(message.get('from_user'))
            event.body.message.to = int(message.get('to'))
            event.body.message.time = int(message.get('time'))
            event.body.message.message = message.get('message')
            event.body.message.from_user_nick = message.get('from_user_nick', '')
            event.body.message.from_user_avatar = message.get('from_user_avatar', '')
            event.body.message.from_user_sex = message.get('from_user_sex', 0)
            self.sender.send_friend_message(event, event.body.message.to)

    # 通用推送广播消息
    def queue_notification(self):
        while True:
            _,data = self.redis.brpop("notification_queue")
            json_object = json.loads(data)

            users = json_object['users']
            event = create_client_event(NotificationEvent)
            event.body.type = json_object['notifi_type']
            event.body.param1 = json_object['param1']
            event.body.param2 = json.dumps(json_object['param2'])

            self.sender.send_event(users,event)


    def get_order_sn(self, uid):
        return time.strftime('%Y%m%d')+str(random.randint(10000,99999))+str(uid)

    def notify_one(self, user, message, table_id, chat_type):

        event = create_client_event(ChatEvent)
        event.body.sender = user
        event.body.table_id =  table_id
        event.body.chat_type = chat_type
        event.body.message = message
        event_data = event.encode()

        access_service = self.redis.hget("online",user)
        if access_service == None:
            return

        access_service = int(access_service)
        user = int(user)
        self.send_client_event(access_service,user,event.header.command,event_data) 


if __name__ == "__main__":
    pass

