# -*- coding: utf-8 -*-
__author__ = 'Administrator'

# -*- coding: utf-8 -*-
import os
import time
import json
import re
import random
import itertools
from helper.encryhelper import md5_encry

curr_dir = os.path.dirname(os.path.abspath(__file__))
filtered_words_txt_path = os.path.join(curr_dir,'filtered_words.txt')
import chardet

def filter_replace(string):
    string = string.decode("utf-8")
    filtered_words = []
    with open(filtered_words_txt_path) as filtered_words_txt:
        lines = filtered_words_txt.readlines()
        for line in lines:
            filtered_words.append(line.strip().decode("utf-8"))
    return replace(filtered_words, string)

def replace(filtered_words,string):
    new_string = string
    for words in filtered_words:
        if words in string:
            new_string = string.replace(words,"*"*len(words))
    if new_string == string:
        return new_string
    else:
        return replace(filtered_words,new_string)


def talk_repeat(r, uid, message):
    json_msg = json.loads(message)
    content = md5_encry(str(json_msg['content']))
    suid = str(uid)
    key = 'talk_repeat:'+suid
    if r.exists('no_talk_repeat:'+suid):
        return True

    if not r.exists(key):
        r.rpush(key, content)
        r.expire(key, 86400)
        return False

    talks = r.lrange(key,0,-1)
    if len(talks) >= 4:
        if all([True if x == content else False for x in talks ]):
            r.set('no_talk_repeat:'+suid, 86400)
            r.expire('no_talk_repeat:'+suid, 86400)
            return True
        else:
            r.lpop(key)
            r.rpush(key, content)
    else:
        r.rpush(key, content)
        return False

# 重复发言处理
def talk_expire(r, uid, table_id):
    talk_key = 'talk_'+str(uid)+'_'+str(table_id)
    talk_table_count = r.get(talk_key)
    if talk_table_count == None:
        r.incr(talk_key)
        r.expire(talk_key, 60)
    else:
        if int(talk_table_count) >= 3:
            return False
        else:
            r.incr(talk_key)
    return True

def talk_no(r,uid):
    if r.exists('talk_no:'+str(uid)):
        expire_time = r.ttl('talk_no:'+str(uid))
        if expire_time > 0:
            return True, expire_time
        else:
            return True,0
    return False,-1

def set_user_no_talk(r,uid, sec):
    if sec == 0:
        r.set('talk_no:'+str(uid),sec)
    else:
        r.set('talk_no:'+str(uid),sec)
        r.expire('talk_no:'+str(uid), sec)


def replace_number(message):
    user_message = str(message)
    if len(user_message) >= 6:
        list_message = list(user_message)

        replace_count = round(len(list_message) * 0.3)
        replace_num = 0
        for index, character in enumerate(list_message):
            if replace_num >= replace_count:
                break
            if character.isalnum():
                replace_num += 1
                list_message[index] = '*'
        return "".join(list_message)
    return user_message

def replace_alpha_number(message):
    if isinstance(message, unicode):
        message = message.encode('utf-8')

    s1 = re.search('\w.*\w', message)
    if s1 == None:
        return message

    s2 = re.sub('[^\w\d]+','',s1.group())
    if s2 == None:
        return message

    s3 = re.match('[\w\d]{6,}',s2)
    if s3 != None:
        list_message = list(message)
        s3_alpha = s3.group()


        some_alpha = []
        for x in s3_alpha:
            if x not in some_alpha:
                some_alpha.append(x)

        if len(some_alpha) == 1:
            replace_count = round(len(s3_alpha) * 0.3)
            replace_num = 0
            for index, character in enumerate(list_message):
                if replace_num >= replace_count:
                    break
                if character.isalnum() and character == some_alpha[0]:
                    replace_num += 1
                    list_message[index] = '*'
            return "".join(list_message)

        replace_count = int(round(len(s3_alpha) * 0.3))
        replace_str = []

        for index, character in enumerate(list_message):
            if character.isalnum():
                if len(replace_str) >= replace_count:
                    break
                if random.choice([True, False]):
                    continue
                if character not in replace_str:
                    replace_str.append(character)
                    list_message[index] = '*'

        message = "".join(list_message)
    return message

if __name__ == '__main__':
    # print filter_replace(raw_input("Type:"))
    # print replace_alpha_number('【客服QQ】添加客服QQ【906320861】为好友吧，反馈~吐槽~抱怨~')
    pass