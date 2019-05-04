#coding: utf-8
'''
Created on 2012-2-20

@author: Administrator
'''

from gevent import monkey;monkey.patch_all()

import importlib
import time,traceback
import threading
import sys,logging

from db.connect import *
from message.base import *
import socket

from proto.access_pb2 import *
from proto.constant_pb2 import *
from proto.game_pb2 import *
from proto.hall_pb2 import *
from proto.chat_pb2 import *
from proto.reward_pb2 import *
from proto.trade_pb2 import *
from proto.bag_pb2 import *
from proto.bank_pb2 import *
from proto.mail_pb2 import *
from proto.friend_pb2 import *
from proto.struct_pb2 import *
from proto.rank_pb2 import *
from proto.war_pb2 import *
from proto.lottery_pb2 import *
from proto.texas_pb2 import *
from testbasecard import *



def fast_login_game(client,device_id,imei,imsi,token):
    try:
        MessageMapping.init()
        resp = client.fast_test_enter_server(device_id,imei,imsi,token)

        req = create_client_message(ConnectGameServerReq)
        req.header.user = resp.header.user
        req.body.session = resp.body.session

        client.socket.send(req.encode())

        resp2 = client.get_message()
        print '1111111111111111111111111111111111111111111'

        req2 = create_client_message(QueryHallReq)
        req2.header.user = resp.header.user
        req2.body.max_mail_id = 0
        req2.body.max_announcement_id = 0
        client.socket.send(req2.encode())
        client.get_message()
        # req2 = create_client_message(QueryUserReq)
        # req2.header.user = resp2.header.user
        # req2.body.uid = resp2.header.user
        # client.socket.send(req2.encode())
        # client.get_message()
    except:
        traceback.print_exc()
    finally:
        pass

def register_game(client,mobile,password,verify_code,imei,imsi,device_id,channel):
    try:
        MessageMapping.init()
        resp = client.register_test_enter_server(mobile,password,verify_code,imei,imsi,device_id,channel)
        # RESULT_FAILED_NAME_EXISTED
        if resp.header.result == 5:
            print 'RESULT_FAILED_NAME_EXISTED'
            return

        if resp.header.result == 8:
            print 'RESULT_FAILED_ACCOUNT_DISABLED'
            return


        req = create_client_message(ConnectGameServerReq)
        req.header.user = resp.header.user
        req.body.session = resp.body.session
        client.socket.send(req.encode())

        result = client.get_message()
        #
        # req = create_client_message(QueryHallReq)
        # req.header.user = result.header.user
        # req.body.max_mail_id = 0
        # req.body.max_announcement_id = 0
        # client.socket.send(req.encode())
    except:
        traceback.print_exc()
    finally:
        pass

def normal_login_game_server_time(client,mobile,password,device_id):
    try:
        MessageMapping.init()
        print mobile,password,device_id
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        time.sleep(3)
        req = create_client_message(GetServerTimeReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def normal_logout(client,mobile,password,token):
    try:
        MessageMapping.init()

        resp = client.fast_test_enter_server(token,'','','')
        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body
        time.sleep(2)
        print 'now logout------------------------------------'
        resp = client.normal_logout_server(mobile,password,token, result.header.user)
        print resp
        print '#####################'
        print resp.header.user,'=',resp.header.result
        time.sleep(2)
        req = create_client_message(QueryHallReq)
        req.header.user = result.header.user
        req.body.max_mail_id = 0
        req.body.max_announcement_id = 0
        client.socket.send(req.encode())

    except:
        traceback.print_exc()
    finally:
        pass

def update_user(client,mobile,password,device_id):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        time.sleep(1)
        print '33333333333333333333333333333333333'
        req = create_client_message(UpdateUserReq)
        req.header.user = result.header.user
        req.body.sign = u'33333311111111111111111111111111111111签名喔~~~'
        req.body.nick = u'x11231111x'
        req.body.birthday = '1911-01-11'
        req.body.avatar = 'https://www.baid111.c1om/img111111111/bd11_111111logo1.pn123123g'
        print req.header.user,'=',req.header.result
        client.socket.send(req.encode())

        print '4444444444444444444444444444444444'




    except:
        traceback.print_exc()
    finally:
        pass

def get_annoucments(client,mobile,password,token):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server('13412311111','123456','device_id_333')

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        req = create_client_message(QueryAnnouncementsReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def send_chat_world(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        # req = create_client_message(QueryHallReq)
        # req.header.user = result.header.user
        # req.body.max_mail_id =  0
        # req.body.max_announcement_id =  0
        # client.socket.send(req.encode())
        # time.sleep(2)
        req2 = create_client_message(SendChatReq)
        req2.header.user = result.header.user
        req2.body.table_id = 0
        req2.body.message = u'xxxxxx在Python中使用protocol buffers参考指南！！#￥%……&*（'
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def send_chat_room(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        req = create_client_message(QueryHallReq)
        req.header.user = result.header.user
        req.body.max_mail_id =  0
        req.body.max_announcement_id =  0
        client.socket.send(req.encode())
        time.sleep(2)
        req2 = create_client_message(SendChatReq)
        req2.header.user = result.header.user
        req2.body.table_id = 0
        req2.body.message = u'在Python中使用protocol buffers参考指南！！#￥%……&*（'
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_rewards(client,mobile,password,device_id):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        req = create_client_message(QueryRewardsReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

        # req2 = create_client_message(QueryRewardsResp)
        # req2.header.user = result.header.user
        # client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def revice_rewards(client,mobile,password,device_id):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

        req2 = create_client_message(ReceiveRewardReq)
        req2.header.user = result.header.user
        req2.body.reward_id = 94
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass


def get_hall_query(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryHallReq)
        req.header.user = result.header.user
        req.body.max_mail_id = 0
        req.body.max_announcement_id = 0
        client.socket.send(req.encode())

        req = create_client_message(QueryUserReq)
        req.header.user = result.header.user
        req.body.uid = result.header.user
        client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def query_player(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        # print '3333333333333333333333333333333333'
        # req = create_client_message(QueryHallReq)
        # req.header.user = result.header.user
        # req.body.max_mail_id = 0
        # req.body.max_announcement_id = 0
        # client.socket.send(req.encode())

        req = create_client_message(QueryUserReq)
        req.header.user = result.header.user
        req.body.uid = 11183
        client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def use_code(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        # print '3333333333333333333333333333333333'
        # req = create_client_message(QueryHallReq)
        # req.header.user = result.header.user
        # req.body.max_mail_id = 0
        # req.body.max_announcement_id = 0
        # client.socket.send(req.encode())

        req = create_client_message(ReceiveCodeRewardReq)
        req.header.user = result.header.user
        req.body.code = '0755'
        client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_signs(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        # resp = client.normal_test_enter_server(mobile,password,device_id)
        resp = client.fast_test_enter_server(device_id,'','','')
        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryHallReq)
        req.header.user = result.header.user
        req.body.max_mail_id = 0
        req.body.max_announcement_id = 0
        client.socket.send(req.encode())

        time.sleep(1)
        req = create_client_message(QuerySigninRewardReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def today_sign(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        # resp = client.normal_test_enter_server(mobile,password,device_id)
        resp = client.fast_test_enter_server(device_id,'','','')

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryHallReq)
        req.header.user = result.header.user
        req.body.max_mail_id = 0
        req.body.max_announcement_id = 0
        client.socket.send(req.encode())
        print '444444444444444444444444444444444444444444'
        time.sleep(1)
        # req = create_client_message(QuerySigninRewardReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())
        # time.sleep(3)
        print '5555555555555555555555555555555555555555555'
        req = create_client_message(SigninReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())
      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_register_code(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()

        req = create_client_message(GetVerifyCodeReq)
        req.header.user = -99
        req.body.mobile = '17727853917'
        req.body.token = '123123'
        print '111111111111111111111111111111111'
        client.login_socket.send(req.encode())

        resp = client.get_message(client.login_socket)
        print resp.body
        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_shop_item(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryShopReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def buy_shop_item(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(BuyItemReq)
        req.header.user = result.header.user
        req.body.shop_item_id = 3
        req.body.count = 3
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def trade_page_list(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryTradeReq)
        req.header.user = result.header.user
        req.body.page = 1
        req.body.page_size = 5
        req.body.can_buy = False
        req.body.my_sell = False
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass
def trade_buy(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(BuyTradeReq)
        req.header.user = result.header.user
        req.body.trade_id = 260
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def trade_sell(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SellGoldReq)
        req.header.user = result.header.user
        req.body.gold = 1000000
        req.body.diamond = 10
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass
def trade_out(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(OutGoldReq)
        req.header.user = result.header.user
        req.body.trade_id = 49
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def query_user_bag(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryBagReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass
def use_user_bag(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(UseItemReq)
        req.header.user = result.header.user
        req.body.item_id = 4
        req.body.count = 1
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def query_bank(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryBankReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def active_bank_gold(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SaveMoneyReq)
        req.header.user = result.header.user
        req.body.gold = 500
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_mails(client,mobile = '13412341777',password= '123456',device_id='d_9444',act = ''):
    try:
        MessageMapping.init()
        # resp = client.normal_test_enter_server(mobile,password,device_id)
        resp = client.fast_test_enter_server(device_id,'','','')
        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(FetchMailReq)
        req.header.user = result.header.user
        req.body.max_mail_id = 0
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def receive_mails(client,mobile = '13412341777',password= '123456',device_id='d_9444',act = ''):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(ReceiveAttachmentReq)
        req.header.user = result.header.user
        req.body.mail_id = 30
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def receive_friend_message(client,mobile = '13412341777',password= '123456',device_id='d_9444',act = ''):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        time.sleep(3)
        req = create_client_message(QueryHallReq)
        req.header.user = result.header.user
        req.body.max_mail_id = 0
        req.body.max_announcement_id = 0
        client.socket.send(req.encode())

        print '3333333333333333333333333333333333'
        time.sleep(5)
        req = create_client_message(ReceiveFriendMessageReq)
        req.header.user = result.header.user
        req.body.message_id = 13
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def handle_friend(client,mobile = '13412341777',password= '123456',device_id='d_9444',act = ''):
    MessageMapping.init()
    resp = client.normal_test_enter_server(mobile,password,device_id)

    print '1111111111111111111'
    print resp.header.user,'=',resp.header.result
    print resp.body

    client.setup_socket()
    result = client.connect_game_server(resp.header.user, resp.body.session, 1)
    print '2222222222222222222'
    print result.header.user,'=',result.header.result
    print result.body

    print '3333333333333333333333333333333333'
    time.sleep(3)
    req = create_client_message(HandleFriendApplyReq)
    req.header.user = result.header.user
    req.body.apply_id = 180
    req.body.accept = True
    client.socket.send(req.encode())

def send_mail(client,mobile = '13412341777',password= '123456',device_id='d_9444',act = ''):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SendMailReq)
        req.header.user = result.header.user
        req.body.to = 10018
        req.body.title = '测试标题'
        req.body.content = '测试正文内容'
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_friends(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        # resp = client.normal_test_enter_server(mobile,password,device_id)
        resp = client.fast_test_enter_server('117627af0e87e92d','868586022072002','','')
        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(GetFriendsReq)
        req.header.user = result.header.user
        req.body.page = 3
        req.body.page_size = 50
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_friends_apply(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(GetFriendAppliesReq)
        req.header.user = result.header.user
        req.body.page = 1
        req.body.page_size = 10
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def make_friends_apply(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        # resp = client.normal_test_enter_server(mobile,password,device_id)
        resp = client.fast_test_enter_server(device_id,'','','')
        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(MakeFriendReq)
        req.header.user = result.header.user
        req.body.target = 11301
        req.body.message = 'xxxxxxxxxx111111111111xxxxxxxxxxxxxxxxxxx'
        # gift = req.body.gifts.add()
        # gift.id = 66
        # gift.name = '88 flowers'
        # gift.icon = '88flower'
        # gift.count = 2
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def remove_friends_apply(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(RemoveFriendMessageReq)
        req.header.user = result.header.user
        req.body.friend_id = 10158

        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def send_friends_message(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SendFriendMessageReq)
        req.header.user = result.header.user
        req.body.friend_id = 10000
        req.body.message = '88 flowers for you'

        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_rank(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

# // 排行榜类型
# enum RankType {
# 	RANK_WEALTH = 1;
# 	RANK_CHARGE = 2;
# 	RANK_CHARM = 3;
# 	RANK_MAKE_MONEY = 4;
# 	RANK_WAR = 5;
# 	RANK_TEXAS = 6;
# 	RANK_LOTTERY = 7;
# }
#
# // 排行榜参数
# enum RankTime{
# 	RANK_ALL_TIME = 0;
# 	RANK_YESTERDAY = 1;
# 	RANK_TODAY = 2;
# 	RANK_LAST_MONTH = 3;
# 	RANK_THIS_MONTH = 4;
# 	RANK_LAST_WEEK = 5;
# 	RANK_THIS_WEEK = 6;
# }
        print '3333333333333333333333333333333333'
        req = create_client_message(QueryRankReq)
        req.header.user = result.header.user
        req.body.rank_type = 7
        req.body.rank_time = 1
        client.socket.send(req.encode())


# // 排行榜类型
# enum RankType {
# 	RANK_WEALTH = 1;
# 	RANK_CHARGE = 2;
# 	RANK_CHARM = 3;
# 	RANK_MAKE_MONEY = 4;
# }
#
# // 排行榜参数
# enum RankTime{
# 	RANK_ALL_TIME = 0;
# 	RANK_YESTERDAY = 1;
# 	RANK_TODAY = 2;
# 	RANK_LAST_MONTH = 3;
# 	RANK_THIS_MONTH = 4;
# 	RANK_LAST_WEEK = 5;
# 	RANK_THIS_WEEK = 6;
# }
        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def receive_broke(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(ReceiveBankcruptRewardReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_broke(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryBankcruptRewardReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def upgrade_check(client,device_id,imei,imsi):
    try:
        MessageMapping.init()


        client.setup_socket()
        req = create_client_message(CheckUpgradeReq)
        req.header.user = -1
        req.body.version = 1
        req.body.channel = 'channel1'

        client.login_socket.send(req.encode())
        resp = client.get_message(client.login_socket)
        # self.user = resp.body.uid
        return resp

    except:
        traceback.print_exc()
    finally:
        pass


def receive_table(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(ReceivePlayRewardReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass




def bind_mobile(client,uid,type,mobile,password):
    try:
        MessageMapping.init()
        resp = client.fast_test_enter_server('8182c3e0943d05be','','','')

        req = create_client_message(ConnectGameServerReq)
        req.header.user = resp.header.user
        req.body.session = resp.body.session

        client.socket.send(req.encode())

        resp2 = client.get_message()
        print '1111111111111111111111111111111111111111111'

        req2 = create_client_message(BindMobileReq)
        req2.header.user = resp.header.user
        req2.body.uid = 11201
        req2.body.mobile = '17727853917'
        req2.body.verify_code = '3822'
        req2.body.bind_type = 1
        req2.body.password = '123456'
        client.socket.send(req2.encode())
        # client.get_message()
        # req2 = create_client_message(QueryUserReq)
        # req2.header.user = resp2.header.user
        # req2.body.uid = resp2.header.user
        # client.socket.send(req2.encode())
        # client.get_message()
    except:
        traceback.print_exc()
    finally:
        pass


def reset_login(client,mobile,password,verify):
    try:
        MessageMapping.init()

        resp = client.reset_login(mobile,password,verify)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body


    except Exception as e:
        traceback.print_exc()
    finally:
        pass



def get_charge(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryChargeReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass


def get_order(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(CreateOrderReq)
        req.header.user = result.header.user
        req.body.shop_id = 1001
        req.body.comment = 'reward_box'
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_gold_top(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryRankReq)
        req.header.user = result.header.user
        req.body.rank_type = 1
        req.body.rank_time = 0
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_charge_top(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(QueryRankReq)
        req.header.user = result.header.user
        req.body.rank_type = 2
        req.body.rank_time = 2
        client.socket.send(req.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass


def send_emoji(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SitTableReq)
        req.header.user = result.header.user
        req.body.table_id = 146
        req.body.table_type = 2
        client.socket.send(req.encode())

        time.sleep(3)
        req = create_client_message(SendEmojiReq)
        req.header.user = result.header.user
        req.body.emoji = 'kiss'
        req.body.count = 3
        req.body.other = 11294

        client.socket.send(req.encode())


    except Exception as e:
        traceback.print_exc()
    finally:
        pass


def feed_back(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(FeedBackReq)
        req.header.user = result.header.user
        req.body.message = u'哈哈哈'
        req.body.contact = 'aaaaaaaa'


        client.socket.send(req.encode())


    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def send_customer(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SendFriendMessageReq)
        req.header.user = result.header.user
        req.body.friend_id = 10000
        req.body.message = u'测试，测试一下，噢噢噢噢啊啊啊aaaa'


        client.socket.send(req.encode())


    except Exception as e:
        traceback.print_exc()
    finally:
        pass


def query_pop_activity(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(PopActivityReq)
        req.header.user = result.header.user

        client.socket.send(req.encode())


    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def sit_table(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SitWarTableReq)
        req.header.user = result.header.user

        client.socket.send(req.encode())


    except Exception as e:
        traceback.print_exc()
    finally:
        pass
    
def bet_action(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        req = create_client_message(SitWarTableReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        time.sleep(1)
        req = create_client_message(WarBetActionReq)
        req.header.user = result.header.user
        req.body.action_type = 1
        req.body.chip.gold = 1000
        client.socket.send(req.encode())

        time.sleep(1)
        req = create_client_message(WarBetActionReq)
        req.header.user = result.header.user
        req.body.action_type = 0
        req.body.chip.gold = 2000
        client.socket.send(req.encode())


    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def trend(client,mobile = '13412341777',password= '123456',device_id='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,device_id)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body

        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())

        time.sleep(1)
        req = create_client_message(QueryTrendReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())



    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def chat_war(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        req = create_client_message(SitWarTableReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        time.sleep(3)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(SendChatReq)
        req2.header.user = result.header.user
        req2.body.table_id = -10
        req2.body.message = u'在Python中使用protocol buffers参考指南！！#￥%……&*（'
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def query_pool(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())

        time.sleep(3)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(QueryPoolRankResp)
        req2.header.user = result.header.user
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass


def query_flow(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())

        time.sleep(3)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(QueryFlowReq)
        req2.header.user = result.header.user
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def buy_flow(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())

        time.sleep(3)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(BuyFlowItemReq)
        req2.header.user = result.header.user
        req2.body.shop_item_id = 10
        req2.body.mobile = 17727853917
        req2.body.desc = 'ljq'
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def reward_box(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())


        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def get_lottery_reward(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())

        time.sleep(3)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(BigRewardReq)
        req2.header.user = result.header.user
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def lottery_open(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())

        time.sleep(3)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(LotteryOpenReq)
        req2.header.user = result.header.user
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def lottery_close(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        # req = create_client_message(SitWarTableReq)
        # req.header.user = result.header.user
        # client.socket.send(req.encode())

        time.sleep(3)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(BigRewardReq)
        req2.header.user = result.header.user
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def lottery_bet(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        req = create_client_message(LotteryOpenReq)
        req.header.user = result.header.user
        client.socket.send(req.encode())

        time.sleep(1)
        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        req2 = create_client_message(LotteryBetReq)
        req2.header.user = result.header.user

        time.sleep(2)
        bet1 = req2.body.bet.add()
        bet1.poker_type = P_DAN
        bet1.bet_gold = 5000

        bet2 = req2.body.bet.add()
        bet2.poker_type = P_DUI
        bet2.bet_gold = 50000

        bet3 = req2.body.bet.add()
        bet3.poker_type = P_BAOZI
        bet3.bet_gold = 2000

        req2.body.auto_bet_number = 0
        client.socket.send(req2.encode())

        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def texas_sit(client,mobile = '13412341235',password= '123456',token='d_9444'):
    try:
        MessageMapping.init()
        resp = client.normal_test_enter_server(mobile,password,token)

        print '1111111111111111111'
        print resp.header.user,'=',resp.header.result
        print resp.body

        client.setup_socket()
        result = client.connect_game_server(resp.header.user, resp.body.session, 1)
        print '2222222222222222222'
        print result.header.user,'=',result.header.result
        print result.body


        print '3333333333333333333333333333333333'
        req = create_client_message(TexasSitTableReq)
        req.header.user = result.header.user
        req.body.table_id = -1
        client.socket.send(req.encode())



        print ''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        resp = client.get_message(client.socket)
        # tb_id = resp.body.table.id
        # print 'user=%d wait bet READY' % resp.header.user
        # time.sleep(4)
        # req2 = create_client_message(TexasLeaveTableReq)
        # req2.header.user = result.header.user
        # req2.body.table_id = resp.body.table.id
        # print 'leave table now'
        # req2.body.bet_type = BET
        # req2.body.texas_status = TEXAS_START
        # req2.body.action_gold = 1000
        # req2.body.bet_reward_gold = 1000
        # resp = client.socket.send(req2.encode())
        #
        # print resp
        # time.sleep(3)
        # print 'user=%d now hand bet pass go public_3' % req.header.user
        #
        # req3 = create_client_message(TexasBetActionReq)
        # req3.header.user = result.header.user
        # req3.body.table_id = tb_id
        # req3.body.bet_type = PASS
        # req3.body.texas_status = TEXAS_HAND
        # req3.body.action_gold = 1000
        # req3.body.bet_reward_gold = 1000
        # client.socket.send(req3.encode())
        # time.sleep(3)
        # print 'user=%d bet PLUS_GOLD' % req.header.user
        # req3 = create_client_message(TexasBetActionReq)
        # req3.header.user = result.header.user
        # req3.body.table_id = resp.body.table.id
        # req3.body.bet_type = ADD_BET
        # req3.body.texas_status = TEXAS_HAND
        # req3.body.action_gold = 1000
        # req3.body.bet_reward_gold = 1000
        # client.socket.send(req3.encode())
        # req = create_client_message(QueryUserReq)
        # req.header.user = result.header.user
        # req.body.uid = result.header.user
        # client.socket.send(req.encode())

      # client.socket.send(req.encode())

    except Exception as e:
        traceback.print_exc()
    finally:
        pass

def test_card(imei,imsi,token,need_idle,*args):
    resp = None
    try:
        MessageMapping.init()
        client = TestClient(str(999999),str(999998), 'token_123')

        texas_sit(client, '13480879974', '123456', '94879ac9253746f6')

        # lottery_open(client, '18688775086', '123456', 'b0f0dec5c9dc6222')
        # lottery_close(client, '17727853917', '111111', 'd971ed2bfbb1bd91')
        # lottery_bet(client, '18688775086', '123456', 'b0f0dec5c9dc6222')


        # get_lottery_reward(client, '17727853917', '111111', 'd971ed2bfbb1bd91')
        # get_order(client, '15919430507','12345678', 'ec747b72aa193c53')
        # reward_box(client, '17727853917','111111', '359901057716157')
        # buy_flow(client, '17727853917','111111', '359901057716157')
        # query_flow(client, '17727853917','111111', '359901057716157')
        # sit_table(client, '13480879974', '123456', '94879ac9253746f6')
        # sit_table(client, '13112345671', '123456', '209707aeb43af5f1')
        

        # bet_action(client, '15815052888', '123456', '65ac1c5fb1ed7bd')


        # trend(client, '15815052888', '123456', '65ac1c5fb1ed7bd')
        # query_pool(client, '15815052888', '123456', '65ac1c5fb1ed7bd')
        # chat_war(client,'13112345671', '123456', '209707aeb43af5f1')


        # reset_login(client, '13480879974', '222222', 0000)
        # handle_friend(client, '17712345678', '123456', 'f07b71a305ce16e4')

        # make_friends_apply(client, '17712345678', '123456', '117627af0e87e92d')
        # get_rank(client, '17727853917', '111111', 'd971ed2bfbb1bd91')

        # send_customer(client,'13480879974', '654321','8182c3e0943d05be')
        

        # feed_back(client,'11122223333', '123456','device_id_001')
        # fast_login_game(client,'device_i_006','ime_006','ims_006', 'toke_006')
        #  register_game(client, '22233334444','123456','0','imei_002','imsi_002','device_id_002','channel_002')

        # normal_login_game_server_time(client, '13480879974','666666', 'fd56d414984b4b03')
        # upgrade_check(client, '17727853917','111111', '359901057716157')
        # get_friends_apply(client, 'lxk','123456', '359901057716157')
        # get_friends(client, '13466557799','123456', '209707aeb43af5f5')
        # query_bank(client, '13488889999','123456', '865372020475361')

        # active_bank_gold(client, '13488889999','123456', '865372020475361')

        # buy_shop_item(client, '13480879974','123456', 'f07b71a305ce16e4')
        # normal_login_game_server_time(client, '13412341777','123456', '88899111121')
        # trade_page_list(client, '15919430507','wang0000', '359901057716157')

        # trade_sell(client, '15919430507','wang0000', '359901057716157')
        # trade_out(client, '13488889999','123456', '865372020475361')
        # query_user_bag(client, '13488889999','123456', '865372020475361')
        # use_user_bag(client, '13412311111','123456', '351702077470363')
        # query_player(client, '13466557799','123456', '865372020475361')


        # get_hall_query(client,'15919430507','12345678','356156076240308')
        # bind_mobile(client, '','','','')
        # normal_logout(client, '15919430507','wang0000', '865372020475361')
        # update_user(client, '15815052843','987654', '865647020556892')
        # send_chat_world(client,'15815052843', '987654', '865647020556892')
        # revice_rewards(client, '15815052843','987654', '865647020556892')
        # trade_buy(client, '13433334444','123456', '865372020475362')
        # get_annoucments(client, str(999999),str(999998), 'token_123')

        # use_code(client, '13751623680', '123123', '209707aeb43af5f1')

        # get_signs(client, '13480879974', '123456', '4b4e47a70688e136')
        # today_sign(client, '13480879974', '123456', 'a649afdb3fd717b2')

        # send_chat_room(client,'13412311111', '123456', 'device_id_333')
        # get_rewards(client, '13466557799','123456', '865372020475361')

        # get_shop_item(client, '13412311111','123456', 'device_id_333')
        # get_register_code(client,'177', '123456', 'device_id_333')

        # get_mails(client, '13412311111','123456', 'A00000568CD11')

        # send_mail(client, '13412311111','123456', 'device_id_333')

        if need_idle:
            client.idle()
        else:    
            resp = client.get_message()  
            print "== result ==>",resp.header.result
          
    except:
        traceback.print_exc()
    finally:
        pass
    return resp


if __name__ == "__main__":
    if sys.argv[1] != "-w":
        test_card(sys.argv[1],"123456",'',True,*sys.argv[2:])
    else:
        test_card(sys.argv[2],"123456",'',True,*sys.argv[3:])
    print "Done"
