# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import random
import time

from db.connect import *
from db.robot import *
from db.account import *
from db.user import *
from db.user_goldflower import *
from db.robot_war import *

class Robot(object):
	"""docstring for Robot"""
	def __init__(self):
		super(Robot, self).__init__()
		self.account = TAccount()
		self.user = TUser()
		self.user_gf = TUserGoldFlower()

class RobotCreater(object):
	"""docstring for RobotCreater"""
	def __init__(self, begin_id):
		super(RobotCreater, self).__init__()
		self.begin_id = begin_id
		self.robot = None
		self.counter = 0
		self.max = 1300
		self.choice_exp = {
			20:[0, 64],
			60:[0, 24],
			100:[0, 16],
			200:[0, 8],
			500:[0, 4],
			100:[0, 2],
		}
		self.account_ids = []

	def creat(self, session):
		for x in xrange(0,self.max):
			# if self.counter == 151:
			# 		self.counter = 501

			account_id = 0
			if self.begin_id is not None:
				account_id = self.get_new_uid(self.begin_id)

			if account_id == 0:
				break

			robot = Robot()
			self.init_account(robot, account_id)
			session.add(robot.account)
			# print robot.account
			self.init_user(robot, account_id)
			session.add(robot.user)
			# print robot.user
			self.init_user_gf(robot, account_id)
			session.add(robot.user_gf)
			# print robot.user_gf
			self.account_ids.append(account_id)

			print '------------------------------------->', self.counter,x
			
			self.counter += 1
		with open('ids', 'w') as f:
			f.write(str(self.account_ids))
			f.close()
			
		session.flush()

	def init_account(self, robot, account_id):
		robot.account.id = account_id
		robot.account.state = -1
		robot.account.device_id = 'robot_' + str(account_id)

	def init_user(self, robot, account_id):
		robot.user.id = account_id
		# robot.user.nick = u'游客'+str(self.get_nick())
		robot.user.nick = self.get_nick()

		# robot.user.avatar = self.get_avatar()
		robot.user.avatar = ''
		robot.user.gold = self.get_gold()
		# robot.user.diamond = self.get_dimaond()
		robot.user.diamond = 0
		# robot.user.vip = self.get_vip()
		robot.user.vip = 0
		# robot.user.vip_exp = self.get_vip_exp(robot.user.avatar)
		robot.user.vip_exp = 0
		robot.user.money = 0
		robot.user.type = 0
		robot.user.charm = 0
		robot.user.brithday = '2000-01-01'
		robot.user.sign = u'这家伙很懒，什么也没留下。'
		# robot.user.sex = self.get_gender()
		robot.user.sex = 0
		robot.user.address = ''
		robot.user.channel = 'robot'
		robot.user.create_time = time.strftime('%Y-%m-%d')
		robot.user.is_charge = 0

	def init_user_gf(self, robot, account_id):
		robot.user_gf.id = account_id
		robot.user_gf.channel = 'robot'
		robot.user_gf.exp = 0
		robot.user_gf.win_games = 0
		robot.user_gf.total_games = 0
		robot.user_gf.best = ''
		robot.user_gf.wealth_rank = 0
		robot.user_gf.win_rank = 0
		robot.user_gf.charm_rank = 0
		robot.user_gf.charge_rank = 0
		robot.user_gf.create_time = time.strftime('%Y-%m-%d')
		robot.user_gf.max_bank = 0
		robot.user_gf.max_items = 0
		robot.user_gf.max_gifts = 0
		robot.user_gf.signin_days = 0
		robot.user_gf.last_signin_day = '2000-01-01'
		robot.user_gf.online_time = 0
		robot.user_gf.login_times = 0
		robot.user_gf.login_times = 0

	def get_nick(self):
		nick = ['游客','赌客','来宾']
		return random.choice(nick)+str(random.randint(1000,9999))

	def get_avatar(self):

		if self.counter > 0 and self.counter <= 150:
			return 'http://121.201.69.204/web/static/avatar/robot/'+str(self.counter)+'.png'
		elif self.counter >= 501 and self.counter < 551:
			return 'http://121.201.69.204/web/static/avatar/robot/'+str(self.counter)+'.png'
		else:
			return ''

	def get_dimaond(self):
		return 0

	def get_vip(self):
		return 0

	def get_vip_exp(self, avatar):
		if avatar == None and len(avatar) == 0:
			return 0

		print self.choice_exp

		vip_exp = random.choice(self.choice_exp.keys())
		item_vip_exp = self.choice_exp.get(vip_exp)
		if self.check_vip_exp(item_vip_exp):
			self.choice_exp[vip_exp][0] += 1
			return vip_exp
		return 0

	def check_vip_exp(self, item_vip_exp):
		if item_vip_exp[0] >= item_vip_exp[1]:
			return False
		return True

	def get_gender(self):
		if self.counter >= 1 and self.counter <= 150:
			return 1
		return 0

	def get_gold(self):
		return random.randint(30000, 400000)

	def get_new_uid(self, uid):
		# r_id = random.randint(2,5)
		# self.begin_id= uid + r_id
		self.begin_id += 1
		return self.begin_id


class RobotSetting(object):
	"""docstring for RobotSetting"""
	def __init__(self):
		super(RobotSetting, self).__init__()
		self.robot_setting = TRobot()

class RobotSettingCreater(object):
	"""docstring for RobotSettingCreater"""
	def __init__(self, ids):
		super(RobotSettingCreater, self).__init__()
		self.ids = ids
		self.choice_online = [
			'06:01-12:00|2800-5600,18:01-23:59|3600-7200',
			'00:01-06:00|2400-4800,12:01-18:00|3200-6400',
		]
		self.choice_type = {
			1:[0,600],
			2:[0,400],
			3:[0,300],
		}

	def create(self, session):

		for index, sid in enumerate(self.ids):
			robot_set = RobotSetting()
			robot_set.robot_setting.uid = sid
			if index >=650:
				robot_set.robot_setting.online_times = self.choice_online[0]
			else:
				robot_set.robot_setting.online_times = self.choice_online[1]

			robot_set.robot_setting.type = self.get_type()
			robot_set.robot_setting.win_gold = 0
			robot_set.robot_setting.state = 1
			robot_set.robot_setting.create_time = time.strftime('%Y-%m-%d')
			print sid,'=',self.choice_type
			session.add(robot_set.robot_setting)
		session.flush()
	
	def get_online_time(self):

		return random.choice(self.choice_online)
		
	def get_type(self):
		type_val = random.choice(self.choice_type.keys())
		
		type_item = self.choice_type.get(type_val)
		
		if type_item[0] >= type_item[1]:
			type_s = self.get_type()
			return type_s
		self.choice_type[type_val][0] += 1
		return type_val

class Robot2Robotwar:
	def __init__(self):
		pass

	def trans(self, session):
		robots = session.query(TRobot).all()
		robot_ids = [x.uid for x in robots]
		robot_war_ids = []
		for x in range(1300):
			robot_war_id = random.choice(robot_ids)
			robot_war_ids.append(robot_war_id)
			robot_ids.remove(robot_war_id)
		
		session.begin()
		for robot_war_id_new in robot_war_ids:
			robot = self.get_robot(robot_war_id_new,robots)
			robot_war = TRobotWar()
			robot_war.uid = robot.uid
			robot_war.online_times = robot.online_times
			robot_war.type = robot.type
			robot_war.win_gold = robot.win_gold
			robot_war.state = 1
			robot_war.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
			session.add(robot_war)
			session.delete(robot)
		session.commit()
	def get_robot(self, uid, robots):
		for x in robots:
			if uid == x.uid:
				return x


if __name__ == '__main__':
	session = Session()
	#creater = RobotCreater(48200)
	#creater.creat(session)

	#with open('ids', 'r') as f:
	 	#ids = f.read()
    #
	 	#ids = ids[1:-1].split(',')
	 	#ids = [int(sid) for sid in ids]
    #
	# 	# for id in ids:
	# 	# 	print id.strip(),len(id.strip())
    #
	 	#creater = RobotSettingCreater(ids)
	 	#creater.create(session)
		
        r2w = Robot2Robotwar()
	r2w.trans(session)
