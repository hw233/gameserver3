#coding:utf8

import json

from hall.messagemanager import *

DT_LOGIN 		= 8
DT_HORN			= 86
DT_GAMES_3 		= 87
DT_GAMES_30 	= 88
DT_WIN_3		= 89
DT_WIN_30		= 90
DT_BET_10		= 91
DT_SHOW_HAND	= 92
DT_DIAMOND		= 93
DT_WARTABLE		= 95
DT_ALL			= 94

ALL_TASKS = (DT_HORN,DT_GAMES_3,DT_GAMES_30,DT_WIN_3,DT_WIN_30,DT_BET_10,DT_SHOW_HAND,DT_DIAMOND,DT_WARTABLE,)

TASK_STATE_FINISHED = 0
TASK_STATE_RECEIVED = 1
TASK_STATE_ONGOING  = 2

class DailyTask:
	def __init__(self,data):
		if data == None: 
			self.tasks = {}
			self.values = {}
		else:
			self.tasks,self.values = json.loads(data)
	
	def to_str(self):
		return json.dumps([self.tasks,self.values])
		
	def get_value(self,name,default):
		value = self.values.get(name,None)
		return default if value == None else value
		
	def set_value(self,name,value):
		self.values[name] = value 
		return value
	
	def inc_value(self,name):
		value = self.values.get(name,0)
		self.values[name] = value + 1
		return value+1
		
	def is_task_finished(self,task_id):
		task_id = str(task_id)
		return task_id in self.tasks and self.tasks[task_id] in (TASK_STATE_FINISHED,TASK_STATE_RECEIVED)
		
	def is_task_received(self,task_id):
		task_id = str(task_id)
		return task_id in self.tasks and self.tasks[task_id] == TASK_STATE_FINISHED
		
	def set_task_finished(self,task_id):
		task_id = str(task_id)
		self.tasks[task_id] = TASK_STATE_FINISHED
		for tid in ALL_TASKS:
			if not self.is_task_finished(tid):
				return

		self.tasks[DT_ALL] = TASK_STATE_FINISHED
		
	def set_task_received(self,task_id):
		task_id = str(task_id)
		self.tasks[task_id] = TASK_STATE_RECEIVED
		
	def get_task_state(self,task_id):
		task_id = str(task_id)
		return self.tasks[task_id] if task_id in self.tasks else TASK_STATE_ONGOING

class DailyTaskManager:
	def __init__(self,redis):
		self.redis = redis
		self.is_notify  = True

	def get_finished_not_received(self, user):
		tasks = self.get_daily_task(user)
		counter = 0
		for task_status in tasks.tasks.values():
			if int(task_status) == TASK_STATE_FINISHED:
				counter += 1
		return counter
		
	def get_daily_task(self,uid):
		data = self.redis.hget("DailyTasks",uid)
		return DailyTask(data)
		
	def update_daily_task(self,uid,task):
		json_str = task.to_str()
		self.redis.hset("DailyTasks",uid,json_str)	
		
	def login(self,uid):
		daily_task = self.get_daily_task(uid)
		if not daily_task.is_task_finished(DT_LOGIN):
			daily_task.set_task_finished(DT_LOGIN)
			self.update_daily_task(uid,daily_task)
			
		
	def use_horn(self,uid):
		daily_task = self.get_daily_task(uid)
		if not daily_task.is_task_finished(DT_HORN):
			self.notify(uid)
			daily_task.set_task_finished(DT_HORN)
			self.update_daily_task(uid,daily_task)
			
		
	def finish_game(self,winner,all_uids):
		for uid in all_uids:
			daily_task = self.get_daily_task(uid)
			games = daily_task.inc_value("games")
			if not daily_task.is_task_finished(DT_GAMES_3) and games >= 3:
				self.notify(uid)
				daily_task.set_task_finished(DT_GAMES_3)
			if not daily_task.is_task_finished(DT_GAMES_30) and games >= 30:
				self.notify(uid)
				daily_task.set_task_finished(DT_GAMES_30)
			
			if uid == winner.uid:
				win_games = daily_task.inc_value("win_games")
				if not daily_task.is_task_finished(DT_WIN_3) and win_games >= 3:
					self.notify(uid)
					daily_task.set_task_finished(DT_WIN_3)
				if not daily_task.is_task_finished(DT_WIN_30) and win_games >= 30:
					self.notify(uid)
					daily_task.set_task_finished(DT_WIN_30)
			self.update_daily_task(uid,daily_task)
				
	def bet_gold(self,uid,gold):
		if gold < 100000:
			return
		daily_task = self.get_daily_task(uid)
		if not daily_task.is_task_finished(DT_BET_10):
			self.notify(uid)
			daily_task.set_task_finished(DT_BET_10)
			self.update_daily_task(uid,daily_task)

	def bet_wartable(self,uid):
		daily_task = self.get_daily_task(uid)
		wartable_bets = daily_task.inc_value('wartable_bets')
		if not daily_task.is_task_finished(DT_WARTABLE) and wartable_bets >= 8:
			daily_task.set_task_finished(DT_WARTABLE)
		self.update_daily_task(uid, daily_task)
		
	def bet_show_hand(self,uid):
		daily_task = self.get_daily_task(uid)
		if not daily_task.is_task_finished(DT_SHOW_HAND):
			self.notify(uid)
			daily_task.set_task_finished(DT_SHOW_HAND)
			self.update_daily_task(uid,daily_task)
	
	def buy_diamond(self,uid):
		daily_task = self.get_daily_task(uid)
		if not daily_task.is_task_finished(DT_DIAMOND):
			self.notify(uid)
			daily_task.set_task_finished(DT_DIAMOND)
			self.update_daily_task(uid,daily_task)	
	
	def set_task_received(self,uid,task_id):
		daily_task = self.get_daily_task(uid)
		if not daily_task.is_task_finished(task_id):
			return -1
		if daily_task.is_task_received(task_id):
			return -2
		daily_task.set_task_received(task_id)	
		self.update_daily_task(uid,daily_task)	
		
	def get_task_state(self,uid,task_id):
		daily_task = self.get_daily_task(uid)	
		return daily_task.get_task_state(task_id)
		
	def get_all_task_states(self,uid):
		daily_task = self.get_daily_task(uid)	
		states = {}		
		for task_id in ALL_TASKS:
			states[task_id] = daily_task.get_task_state(task_id)
		return states

	def notify(self, uid):
		if self.is_notify:
			MessageManager.push_notify_reward(self.redis, uid)