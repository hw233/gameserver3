#coding:utf8

import json,time

from db.system_achievement import *
from db.game_achievement import *
from db.reward_user_log import *

from hall.messagemanager import *

AT_BIND_MOBILE        = 6
AT_UPLOAD_AVATAR      = 7
AT_FIRST_LOGIN 		= 8
AT_BAOZI			= 18
AT_235_WIN_BAOZI	= 19
AT_CHANGE_NICK      = 9


AT_EXP_CONFIG = {
	# id : exp
	101:3,
	102:31,
    103:201,
    104:1001,
    105:3001,
    106:8001,
    107:15001,
    108:30001,
    109:50001,
    110:100001,
}

AT_PLAY_CONFIG = {
	# id : play_games
	201 : 10,
	202 : 50,
	203 : 200,
	204 : 1000,
	205 : 3000,
	206 : 6000,
	207 : 10000,
	208 : 20000,
	209 : 35000,
	210 : 60000,
}

AT_WIN_CONFIG = {
	# id : win_games
	301 : 5,
	302 : 25,
	303 : 100,
	304 : 500,
	305 : 1500,
	306 : 3000,
	307 : 5000,
	308 : 10000,
	309 : 17500,
    310 : 30000,
}

AT_WIN_GOLD_CONFIG = {
	# id : gold
    401 : 100000,
	402 : 500000,
	403 : 2000000,
	404 : 10000000,
	405 : 30000000,
	406 : 60000000,
	407 : 100000000,
	408 : 200000000,
	409 : 350000000,
    410 : 600000000,
}


AT_VIP_CONFIG = {
	# id : vip_level
    501 : 1,
	502 : 2,
	503 : 3,
	504 : 4,
	505 : 5,
	506 : 6,
	507 : 7,
	508 : 8,
	509 : 9,
    510 : 10,
	511 : 11,
	512 : 12,
	513 : 13,
	514 : 14,
	515 : 15,
	516 : 16,
	517 : 17,
	518 : 18,

}



ACHIEVEMENT_FINISHED = 0
ACHIEVEMENT_RECEIVED = 1
ACHIEVEMENT_NOT_FINISHED = 2

class BaseAchievement(object):
	def __init__(self,session,uid,table):
		self.session = session
		self.uid = uid
		self.table = table
		data = session.query(table).filter(table.uid == uid).first()
		
		if data != None:
			self.achievements = json.loads(str(data.achievements))
			self.values = json.loads(str(data.values))
		else:
			self.achievements = {}
			self.values = {}
			
	def inc_value(self,name,added = 1):
		value = self.values.get(name,0)
		self.values[name] = value + added
		return value + added
		
	def get_value(self,name,default):
		value = self.values.get(name,None)
		return default if value == None else value
		
	def set_value(self,name,value):
		self.values[name] = value 
		return value		
			
	def save(self):
		data = self.session.query(self.table).filter(self.table.uid == self.uid).first()
		if data == None:
			data = self.table()
			data.uid = self.uid
			data.achievements = json.dumps(self.achievements)
			data.values = json.dumps(self.values)
			self.session.add(data)
			self.session.flush()
		else:
			data.achievements = json.dumps(self.achievements)
			data.values = json.dumps(self.values)
			
	def get_finished_not_received(self):
		counter = 0
		for achievement_status in self.achievements.values():
			if int(achievement_status) == ACHIEVEMENT_FINISHED:
				counter += 1
		return counter

	def get_task_state(self, achievement_id):
		achievement_id = str(achievement_id)
		return self.achievements[achievement_id] if achievement_id in self.achievements else ACHIEVEMENT_NOT_FINISHED

	def is_achievement_finished(self,achievement_id):
		achievement_id = str(achievement_id)
		return achievement_id in self.achievements and self.achievements[achievement_id] in (ACHIEVEMENT_FINISHED,ACHIEVEMENT_RECEIVED)
		
	def is_achievement_received(self,achievement_id):
		achievement_id = str(achievement_id)
		return achievement_id in self.achievements and self.achievements[achievement_id] == ACHIEVEMENT_FINISHED
		
	def set_achievement_finished(self,achievement_id):
		achievement_id = str(achievement_id)
		self.achievements[achievement_id] = ACHIEVEMENT_FINISHED

	def set_achievement_received(self,achievement_id):
		achievement_id = str(achievement_id)
		self.achievements[achievement_id] = ACHIEVEMENT_RECEIVED


class SystemAchievement(BaseAchievement):
	def __init__(self,session,uid, is_notify = False, redis = None):
		super(SystemAchievement,self).__init__(session,uid,TSystemAchievement)
		self.is_notify = is_notify
		self.redis = redis
		
	def finish_first_login(self):
		if self.is_achievement_finished(AT_FIRST_LOGIN) is False:
			self.set_achievement_finished(AT_FIRST_LOGIN)
			self.save()

	def finish_upload_avatar(self):
		if self.is_achievement_finished(AT_UPLOAD_AVATAR) is False:
			self.set_achievement_finished(AT_UPLOAD_AVATAR)
			self.notify()
			self.save()

	def finish_bind_mobile(self):
		if self.is_achievement_finished(AT_BIND_MOBILE) is False:
			self.set_achievement_finished(AT_BIND_MOBILE)
			self.notify()
			self.save()

	def finish_change_nick(self):
		if self.is_achievement_finished(AT_CHANGE_NICK) is False:
			self.set_achievement_finished(AT_CHANGE_NICK)
			self.notify()
			self.save()
		
	def finish_upgrade_vip(self,vip):
		if vip == 0:
			return
		for at_id,vip_level in AT_VIP_CONFIG.items():
			if vip >= vip_level and not self.is_achievement_finished(at_id):
				self.notify()
				self.set_achievement_finished(at_id)
		self.save()

	def notify(self):
		if self.is_notify:
			MessageManager.push_notify_reward(self.redis, self.uid)


class GameAchievement(BaseAchievement):
	def __init__(self,session,uid,  redis):
		super(GameAchievement,self).__init__(session,uid,TSystemAchievement)
		self.is_notify = True
		self.redis = redis

	def finish_baozi_pokers(self):
		if not self.is_achievement_finished(AT_BAOZI):
			self.set_achievement_finished(AT_BAOZI)
			self.notify()
			self.save()
	

	def finish_235_win_baozi(self):
		if not self.is_achievement_finished(AT_235_WIN_BAOZI):
			self.set_achievement_finished(AT_235_WIN_BAOZI)
			self.notify()
			self.save()
		
	
	def finish_game(self,user_gf,win_gold, redis):
		need_update = False
		
		total_exp = user_gf.exp
		for at_id,exp in AT_EXP_CONFIG.items():
			if total_exp >= exp and not self.is_achievement_finished(at_id):
				self.set_achievement_finished(at_id)
				need_update = True
				MessageManager.push_exp_upgrade(redis, user_gf.id)
				self.notify()
		
		total_games = user_gf.total_games
		for at_id,games in AT_PLAY_CONFIG.items():
			if total_games >= games and not self.is_achievement_finished(at_id):
				self.set_achievement_finished(at_id)
				need_update = True
				self.notify()
		
		if win_gold > 0:
			win_games = user_gf.win_games
			for at_id,games in AT_WIN_CONFIG.items():
				if win_games >= games and not self.is_achievement_finished(at_id):
					self.set_achievement_finished(at_id)
					need_update = True
					self.notify()
			
			total_gold = self.inc_value("gold",win_gold)
			need_update = True

			for at_id,gold in AT_WIN_GOLD_CONFIG.items():
				if total_gold >= gold and not self.is_achievement_finished(at_id):
					self.set_achievement_finished(at_id)
					need_update = True
					self.notify()

			
		if need_update:
			self.save()

	def notify(self):
		if self.is_notify:
			MessageManager.push_notify_reward(self.redis, self.uid)
if __name__ == "__main__":
    import sys,os
    sys.path.append(os.path.dirname(__file__) + os.sep + '..//')


    from db.connect import *
    from db.system_achievement import *
    from db.game_achievement import *
    from db.reward_user_log import *

    session = Session()
    uid = 10020
    vip = 1
    SystemAchievement(session, uid).finish_first_login()
    SystemAchievement(session,uid).finish_upgrade_vip(vip)
	
	
	
	
