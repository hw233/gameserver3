# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from db.connect import *
from db.user import *
from db.robot import *
from datetime import datetime,date
import random
session = Session()
session.begin()
for i in range(10082,11035):
    rb = TRobot()
    rb.uid = i
    rb.online_times = '0:30-22:30|75500-75600'
    rb.type = random.randint(1,3)
    rb.win_gold = 0
    rb.state = 1
    rb.create_time = datetime.now()
    session.add(rb)
session.commit()
