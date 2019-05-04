# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import json,sys,redis,time,os,os.path,decimal
import hashlib
import zipfile
import logging
import urlparse
import subprocess
from flask import Flask,request,render_template,redirect, url_for,jsonify,make_response,abort,flash,get_flashed_messages
from flask import session as flask_session
from werkzeug import secure_filename

from conf import DevConfig


from db.connect import *
from db.order import *
from db.mail import *
from db.bag_item import *
from db.charge_item import *
from db.mail import *
from db.reward_user_log import *
from db.customer_service_log import *
from db.user import *
from db.pop_activity import *
from db.pop_activity_user import *
from db.lucky import *
from db.avatar_verify import *
from config.var import *
from config.rank import *

from helper import datehelper
from sqlalchemy import and_
from sqlalchemy.sql import desc

# from web.upload import *
# from web.avatar import *

# from config.var import *
# from config.vip import *
from hall.hallobject import *
from task.achievementtask import *
from rank.chargetop import *
from hall.rank import *
from dal.core import *
from hall.charge_order import *
from hall.messagemanager import *
from hall.customerservice import *
from hall.flow import *
from hall.mail import *
from activity.luckywheel import *
from helper import wordhelper

from util.commonutil import set_context,get_context


from order.orderhandler import receive_order_callback,create_charge_order

reload(sys)
sys.setdefaultencoding('utf-8')

app = Flask(__name__, static_path='',static_folder='',template_folder='web/templates')
app.config.from_object(DevConfig)
app.secret_key = 'Wgc!@##@!2017'

session = Session()
r = redis.Redis(**WEB_REDIS)
da = DataAccess(r)
STATIC_PATH = 'web/static/'
# uploader = Uploader(STATIC_PATH)
vip = VIPObject(None)
customer_service = CustomerService(r)



# CPID：jjcq20170223_141_312
# CPKEY：d5ff856beccf4c472831c3f16c376e28
# CP_KEY = 'd5ff856beccf4c472831c3f16c376e28'

# VIP_UP=u'玩家%s一掷千金，成功升级为%s，成为人生赢家！(VIP1+)'
UPLOAD_FOLDER = 'web/static/avatar'
UPGRADE_FOLDER = 'web/static/upgrade'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','zip'])
REAL_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'web/static/avatar')
UPGRADE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'web/static/upgrade')
BACK_UP = 'backup'
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def demo():
    return 'hello world!123123'

@app.route('/flow')
def flow():
    code = int(request.args.get('code'))
    msg = request.args.get('msg')
    req_id = request.args.get('req_id')
    Flow.callback_flow(session, req_id, code, msg, da, r)
    return jsonify({'code':1,'text':'','error':{}})

@app.route('/activity')
def activity():
    return render_template('activity.html',GO_BACK=ACTIVITY_BACK_URL)

@app.route('/activity/back')
def activity_back():
    MessageManager.push_h5_back(r, int(request.args.get('uid')), {'data':{}})
    return jsonify({'code':0,'msg':'success','ext':{}})

@app.route('/activity/create_order')
def activity_create_order():

    result = create_charge_order(session, r, da, int(request.args.get('uid')), int(request.args.get('shop_id')), request.args.get('comment'))

    if result:
        MessageManager.push_h5_create_order(r, int(request.args.get('uid')), {'data':{
            'order':{
                'order_sn':result['order_sn'],
                'money':result['money'],
                'callback':result['callback'],
                'name':result['name']
            }
        }})
        return jsonify({'code':0,'msg':'success','ext':{
                'order_sn':result['order_sn'],
                'money':result['money'],
                'callback':result['callback'],
            }})
    return jsonify({'code':-1,'msg':'error','ext':{}})


@app.route('/wheel')
def wheel():
    uid = request.args.get('uid')
    if uid == None or uid <= 0:
        return 404
    activity =  ActivityManager(session, da, r)
    activity_user = activity.load_activity_user(uid)

    data = {}
    if activity_user == None:
        data['play_count'] = 0
    else:
        user_params = activity.prase_activity_params(activity_user.params)
        data['play_count'] = user_params['wheel']['play_count']

    data['wheel_reward'] = json.loads(r.get('activity_wheel_info'))
    progress_list = r.lrange('activity_wheel_code',0,-1)
    data['progress'] = int(len(progress_list) / float(data['wheel_reward']['wheel_len']) * 100)
    data['my_progress'] = len([1 for x in progress_list if x.split('_')[0] == uid])
    data['ACTIVITY_CREATE_URL'] = ACTIVITY_CREATE_URL
    data['ACTIVITY_PLAY'] = ACTIVITY_PLAY

    # 2.读取最新一期的宝物数据
    return render_template('wheel.html',data=data)

@app.route('/wheel/play')
def wheel_play():
    if get_context('session') == None:
        set_context('session', session)
    am = ActivityManager(session, da, r)
    uid = request.args.get('uid')
    flag, result = am.get_handle('wheel',uid)
    if flag:
        activity_game = result
        if activity_game.can_play():
            activity_game.handle()
            am.save_game_result(activity_game)

            data = {}
            data['play_count'] = activity_game.params['wheel']['play_count']
            data['lucky_val'] = activity_game.result[1]
            data['lucky_code'] = activity_game.result[3]
            data['lucky_key'] = activity_game.result[4]
            data['index'] = activity_game.result[2]

            data['wheel_reward'] = json.loads(r.get('activity_wheel_info'))
            progress_list = r.lrange('activity_wheel_code',0,-1)
            data['progress'] = int(len(progress_list) / float(data['wheel_reward']['wheel_len']) * 100)
            data['progress'] = data['progress'] if data['progress'] > 1 else 1
            data['my_progress'] = len([1 for x in progress_list if x.split('_')[0] == uid])

            return jsonify({'code':0,'msg':'success','ext':data})
        else:
            return jsonify({'code':-1, 'msg':u'当前可用次数为0，请充值','ext':{}})
    else:
        return jsonify(result)

@app.route('/wheel/history')
def wheel_history():
    if request.args.get('uid'):
        lists = []
        logs = session.query(TActivityWheelLog,TUser)\
            .join(TUser,TActivityWheelLog.uid == TUser.id)\
            .filter(TActivityWheelLog.uid == request.args.get('uid'))\
            .order_by(TActivityWheelLog.create_time.desc())\
            .limit(20)\
            .all()

        for log in logs:
            lists.append({'title':log[0].reward_item,'create_time':log[0].create_time.strftime('%Y-%m-%d %H:%M:%S'),'nick':log[1].nick,'round':log[0].round})

        # return render_template('wheel_history.html', lists=lists, uid=request.args.get('uid'))
        return jsonify({
            'code':0,
            'msg':'success',
            'ext':{'lists':lists}
        })

    logs = session.query(TActivityWheelLog,TUser)\
            .join(TUser,TActivityWheelLog.uid == TUser.id)\
            .order_by(TActivityWheelLog.create_time.desc())\
            .limit(20)\
            .all()

    lists = []
    for log in logs:
        lists.append( {'title':log[0].reward_item,'create_time':log[0].create_time.strftime('%Y-%m-%d %H:%M:%S'),'nick':log[1].nick,'round':log[0].round} )

    # return render_template('wheel_history.html', lists=lists)
    return jsonify({
        'code':0,
        'msg':'success',
        'ext':{'lists':lists}
    })

@app.route('/avatar', methods=['GET', 'POST'])
def upload_avatar():

    if request.method == 'POST':

        file = request.files['file']
        uid = request.form['uid']
        device_id = request.form['device_id']

        if file == None or uid == None or device_id == None:
            return jsonify(result=0,message='error,file or uid or device_id is empty!')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            savefolder = time.strftime('%Y-%m-%d')
            savepath = REAL_PATH+os.sep+time.strftime('%Y-%m-%d')
            if not os.path.isdir(savepath):
                os.mkdir(savepath)
            img_hard_path = os.path.join(savepath, uid+'_'+device_id+'_'+filename)
            file.save(img_hard_path)
            # return redirect(url_for('uploaded_file', filename=filename))
            full_filename ='/'+uid+'_'+device_id+'_'+filename
            path_url = request.url_root+UPLOAD_FOLDER+'/'+savefolder+full_filename

            # delete old avatar
            user = da.get_user(uid)
            if user.avatar != '' and len(user.avatar) > 0:
                old_avatar = user.avatar
                old_avatar_path = os.getcwd()+urlparse.urlparse(old_avatar).path
                if os.path.exists(old_avatar_path) and os.path.isfile(old_avatar_path):
                    os.remove(old_avatar_path)

            # update new avatar to db
            av = TAvatarVerify()
            av.uid = uid
            av.avatar = path_url
            av.allow = 1
            av.add_time = datehelper.get_today_str()
            session.merge(av)
            session.flush()

            return jsonify(result=0, message='success,message:'+full_filename+',path:'+path_url,url=path_url)

            # result = session.query(TUser).filter(TUser.id == uid).filter(TUser.id == int(uid)).update({
            #     TUser.avatar:path_url
            # })

            # compress_image(img_hard_path)

            # if result > 0:
            #     修改头像换缓存
                # if r.exists('u'+str(uid)):
                #     r.hset('u'+str(uid), 'avatar', path_url)
                # sys_achi = SystemAchievement(session,uid)
                # if not sys_achi.is_achievement_finished(AT_UPLOAD_AVATAR):
                #     sys_achi.finish_upload_avatar()
                #     MessageManager.push_notify_reward(r, uid)
                # session.flush()
                # return jsonify(result=0,message='success,message:'+full_filename+',path:'+path_url,url=path_url)
            # return jsonify(result=-1,message='error:upload return false')

    pathDir =  os.listdir(REAL_PATH)
    html = ''
    for allDir in pathDir:
        # child = os.path.join('%s%s' % (REAL_PATH, allDir))
        html +='<li><a href="'+request.url_root+UPLOAD_FOLDER+'/'+allDir+'">'+request.url_root+UPLOAD_FOLDER+'/'+allDir+'</a></li>'
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new <span style='color:green;'>avatar</span></h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
      <input type=text name=uid placeholder=uid>
      <input type=text name=device_id placeholder=device_id>
         <input type=submit value=Upload>
    </form>
    <ol>
    %s
    </ol>
    ''' % html
# ''' % "<br>".join(os.listdir(app.config['UPLOAD_FOLDER'],))

def compress_image(file_path_url):
    cmd = '/usr/bin/pngquant --force --ext=.png --verbose --skip-if-larger --quality=50-90 %s' % file_path_url
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    retval = p.wait()

@app.route('/avatar_verify', methods=['GET', 'POST'])
def avatar_verify():
    if request.method == 'GET':
        lists = session.query(TAvatarVerify).filter(TAvatarVerify.allow == 0).all()
        return render_template('avatar_verify.html',lists=lists)

    is_allow = int(request.form['send'])
    uid = int(request.form['uid'])

    row = session.query(TAvatarVerify).filter(TAvatarVerify.uid == uid).first()


    if is_allow:
        row.allow = 0
        row.allow_time = datehelper.get_today_str()
        session.add(row)

        result = session.query(TUser).filter(TUser.id == int(uid)).update({
            TUser.avatar:row.avatar
        })

        if result > 0:
            if r.exists('u'+str(uid)):
                r.hset('u'+str(uid), 'avatar', row.avatar)
            sys_achi = SystemAchievement(session,uid)
            if not sys_achi.is_achievement_finished(AT_UPLOAD_AVATAR):
                sys_achi.finish_upload_avatar()
                MessageManager.push_notify_reward(r, uid)

            MessageManager.send_mail(session, uid, 0, title='头像审核', content='头像审核成功', type=0)
            MessageManager.push_notify_mail(r, uid)
    else:
        row.allow = -1
        row.allow_time = datehelper.get_today_str()
        session.add(row)

        MessageManager.send_mail(session, uid, 0, title='头像审核', content='头像审核失败', type=0)
        MessageManager.push_notify_mail(r, uid)
    session.flush()
    return redirect('/avatar_verify')




@app.route('/upgrade', methods=['GET', 'POST'])
def upgrade():
    allow_ips = ['218.17.162.125']

    remote = request.headers['X-Forwarded-For']

    if remote not in (allow_ips):
        abort(403)

    if request.method == 'POST':

        file = request.files['file']
        if file == None:
            return jsonify(result=0,message='error,file or uid or device_id is empty!')

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            backup_file = os.path.join(os.path.join(UPGRADE_PATH, BACK_UP), filename)

            if os.path.exists(backup_file):
                os.remove(backup_file)
            file.save(backup_file)

            if os.path.exists(os.path.join(UPGRADE_PATH, filename.split('.')[0])):
                __import__('shutil').rmtree(os.path.join(UPGRADE_PATH, filename.split('.')[0]))

            unzip_file(filename, UPGRADE_PATH)
            #     return jsonify(result=0,message='success,message:'+full_filename+',path:'+path_url,url=path_url)
            # return jsonify(result=-1,message='error:upload return false')
            # if execute(conn, "UPDATE `user` SET `avatar` = '%s' WHERE `id`=%d" % (path_url, int(uid))):
            #     return jsonify(result=0,message='success,message:'+full_filename+',path:'+path_url,url=path_url)
            # return jsonify(result=-1,message='error:upload return false')
            #return jsonify(rr=0,mm='success,message:'+full_filename+',path:'+path_url,uu=path_url)

    pathDir =  os.listdir(UPGRADE_PATH)
    html = ''
    for allDir in pathDir:
        # child = os.path.join('%s%s' % (REAL_PATH, allDir))
        html +='<li><a href="'+request.url_root+UPGRADE_FOLDER+'/'+allDir+'">'+request.url_root+UPGRADE_FOLDER+'/'+allDir+'</a></li>'
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new <span style='color:red;'>App</span></h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    <ol>
    %s
    </ol>
    ''' % html

@app.route('/customer/robot_send_msg')
def customer_robot_send_msg():
    user = request.args['user']
    content = request.args['content']
    to = request.args['to']

    user_talk = customer_service.get_talk_user(user+'_'+to, 'talk_robot_session')
    
    user_talk.add_talk(user, content, img = '', is_new = False, is_self = True)
    user_talk.set_back()
    customer_service.update_talks(user+'_'+to, user_talk, 'talk_robot_session')
    msg_id = r.incr('message_id')
    db_session = get_context('session')
    if db_session == None:
        set_context('session', session)    

    from_robot = da.get_user(to)
    r.hset('message_'+str(user), msg_id, json.dumps({
        'from_user': from_robot.id,
        'to':user,
        'message':content,
        'time':int(time.time()),
        'from_user_nick':from_robot.nick,
        'from_user_avatar':from_robot.avatar
        }))
    r.rpush('customer_msgs', str(msg_id)+'_'+user)

    resp = make_response(jsonify(code=200))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'  

    return resp

@app.route('/robot/lists', methods=['GET', 'POST'])
def robot_lists():
    lists = customer_service.get_talks('talk_robot_session')
    resp = make_response(jsonify([x.talk for x in lists]))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/customer/lists', methods=['GET', 'POST'])
def customer_lists():
    lists = customer_service.get_talks()
    resp = make_response(jsonify([x.talk for x in lists]))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/talk', methods=['GET', 'POST'])
def talk():
    if request.method == 'POST':
        wordhelper.set_user_no_talk(r, int(request.form['uid']), int(request.form['timeout']))
        return redirect(url_for('talk'))
    no_talk_users = r.keys('talk_no:*')
    no_talk_html = []
    for user in no_talk_users:
        timeout = r.ttl(user)
        if timeout == None:
            no_talk_html.append('<p>user=%s , timeout=0</p>' % user)
        else:
            no_talk_html.append('<p>user=%s , timeout=%s</p>' % (user, timeout))
	#print user,type(user),timeout,type(timeout)
        #no_talk_html.append('<p>user=%s , timeout=%s</p>' % (user, timeout)) 
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>talk</title></head><body>' \
           '<div style="background:#00CC66;padding:10px;max-width:500px;margin:0 auto;border-radius: 10px;border: 1px solid #cecece;">' \
           '<form method="post" action="/talk" name="no_talk">' \
	   '<input type="text" placeholder="用户的UID" name="uid" /><input type="text" placeholder="0永久，>0指定秒数" name="timeout" /><input type="submit" value="提交" />' \
           '</form>' \
           '%s' \
           '</div></body></html>' % "".join(no_talk_html)

@app.route('/black', methods=['GET', 'POST'])
def black():
    if request.method == 'POST':
	uid = int(request.form['uid'])
        if int(request.form['cancel']) > 0:
	    r.lpush('sys_kick',json.dumps({'uid':uid,'cancel':1}))
            r.hdel('sys_blacklist',uid)
        else:
            r.lpush('sys_kick',json.dumps({'uid':uid,'cancel':0}))
            r.hset('sys_blacklist',uid,1)
	return redirect(url_for('black'))
    blacklist_user = [int(x) for x in r.hkeys('sys_blacklist')]
    blacklist_user_html = []
    for user in blacklist_user:
        blacklist_user_html.append('<p>user=%s' % user)
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>blacklist</title></head><body>' \
           '<div style="background:#00CCCC;padding:10px;max-width:500px;margin:0 auto;border-radius: 10px;border: 1px solid #cecece;">' \
           '<form method="post" action="/black" name="black">' \
           '<input type="text" placeholder="用户的UID" name="uid" /><label>撤销<input name="cancel" type="radio" value="1" /></label><label>加入<input name="cancel" checked="checked" type="radio" value="0" /></label><input type="submit" value="提交" />' \
           '</form>' \
           '%s' \
           '</div></body></html>' % "".join(blacklist_user_html)

@app.route('/customer/send_msg')
def customer_send_msg():
    user = request.args['user']
    content = request.args['content']

    user_talk = customer_service.get_talk_user(user)
    user_talk.add_talk(user, content, img = '', is_new = False, is_self = True)
    user_talk.set_back()
    customer_service.update_talks(user, user_talk)
    msg_id = r.incr('message_id')
    r.hset('message_'+str(user), msg_id, json.dumps({
        'from_user':10000,
        'to':user,
        'message':content,
        'time':int(time.time()),
        'from_user_nick':u'客服',
        'from_user_avatar':u''
        }))
    r.rpush('customer_msgs', str(msg_id)+'_'+user)

    resp = make_response(jsonify(code=200))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'  

    return resp

    # items = session.query(TCustomerServiceLog).order_by(desc(TCustomerServiceLog.send_time)).limit(20)
    # for item in items:
    #     key = 'u'+str(item.from_user)
    #     user_info = r.hgetall(key)
    #     print '============>'
    #     print user_info
    #     item.from_user_nick = user_info.get('nick')
    #     item.from_user_avatar = user_info.get('avatar')
    # return render_template('customer.html',items = items)

@app.route('/war')
def war():
    file = 'war_tools.py'
    file_dir = '/data/backend/code/tools'
    file_path = file_dir+os.path.sep+file
    p = subprocess.Popen('python %s' % file_path,stdout=subprocess.PIPE,shell=True)
    table_info = p.stdout.readlines()
    p = None
    s = ''
    for x in list(table_info):
        s += '<p>'+x+'</p>'
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>war</title></head><body><div style="background:#CCFFCC;padding:10px;max-width:500px;margin:0 auto;border-radius: 10px;border: 1px solid #cecece;">' \
           '%s' \
           '</div></body></html>' % s

@app.route('/texas')
def texas():
    to = r.hgetall('texas_online')
    s = ''
    for k,v in to.items():
        s += '<p>%s === %s</p>' % (k, v)
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>texas</title></head><body><div style="background:#CCFFCC;padding:10px;max-width:500px;margin:0 auto;border-radius: 10px;border: 1px solid #cecece;">' \
           '%s' \
           '</div></body></html>' % s

def run_game_cmd(cmd):
    # file_dir = '/data/backend/sh/' #qa
    file_dir = '/data/projects/backend/sh/' #dev
    cmd_path = os.path.join(file_dir,cmd)
    execute_str = '%s.sh reload' % cmd_path
    p = subprocess.Popen(execute_str, stdout=subprocess.PIPE,shell=True)
    return p.stdout.readlines()

@app.route('/table')
def table():
    file = 'online_stat.py'
    file_dir = '/root/tools'
    file_path = file_dir+os.path.sep+file
    p = subprocess.Popen('python %s' % file_path,stdout=subprocess.PIPE,shell=True)
    table_info = p.stdout.readlines()
    p = None
    s = ''
    for x in list(table_info):
        s += '<p>'+x+'</p>'
    return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>table</title></head><body><div style="background:#BBF6FF;padding:10px;max-width:500px;margin:0 auto;border-radius: 10px;border: 1px solid #cecece;">' \
           '%s' \
           '</div></body></html>' % s

@app.route('/broadcast', methods=['GET','POST'])
def broadcast():
    allow_ips = ['218.17.162.125']

    if request.remote_addr not in (allow_ips):
        abort(403)
    if request.method == 'GET':
        html_str = '<form method="post" name="list_form"><div style="background:#E2C846;padding:10px;max-width:800px;margin:0 auto;border-radius: 10px;border: 1px solid #cecece;">' \
                   '<textarea name="broadcast_textarea" id="txt" style="width:100%;height:300px;margin-bottom:4px;">'
        broadcast_json = json.loads(r.get('broadcast_json'))
        html_str += json.dumps(broadcast_json, ensure_ascii=False)
        html_str += '</textarea></form>'
        html_str += '<div style="text-align:right;"><input type="submit" style="text-align:right" name="btn_save" value="保存并推送"/></div>'
        html_str += '</div>'
        html_str += '<form method="post" name="new_form"><div style="background:#ccc;padding:10px;;max-width:800px;margin:10px auto;border-radius: 10px;border: 1px solid #cecece;">' \
                    '<input type="text" required name="broadcast_new" style="width:100%;margin-bottom:4px;"  />' \
                    '<div style="text-align:right;"><input type="submit" name="btn_save_push" value="保存并推送"/>' \
                    '<input type="submit" name="btn_fix_push" disabled="disabled" value="维护模式推送"/></div>' \
                    '</div></form>'

        flash_str = ''
        messages =get_flashed_messages()
        if messages:
            flash_str = '<div style="max-width:800px;margin:0 auto;">'
            for msg in messages:
                flash_str += '<p style="background:#d9edf7;padding:15px;">'
                flash_str += msg
                flash_str +='</p>'
            flash_str += '</div>'

        return '<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>broadcast</title><style>.hover:hover{background:#06f;}</style></head>' \
               '<body>' \
               '%s' \
               '%s' \
               '<script>var txt = document.getElementById("txt").value;document.getElementById("txt").value=JSON.stringify(JSON.parse(txt),null,4);</script></body></html>' % (flash_str, html_str)

    if 'btn_save' in request.form:
        broadcast_json = json.loads(request.form['broadcast_textarea'])
        r.set('broadcast_json', json.dumps(broadcast_json))
        flash(u'保存列表消息成功')
        return redirect(url_for('broadcast'))
    elif 'btn_save_push' in request.form:
        broadcast_new = request.form['broadcast_new']
        broadcast_json = json.loads(r.get('broadcast_json'))
        broadcast_json.append({'message':broadcast_new})
        r.set('broadcast_json', json.dumps(broadcast_json))
        flash(u'新增消息并推送成功')
        MessageManager.push_message(r, r.hkeys('online'),PUSH_TYPE['sys_broadcast'],{'message':broadcast_new})
        return redirect(url_for('broadcast'))
    elif 'btn_fix_push' in request.form:
        broadcast_new = request.form['broadcast_new']
        broadcast_json = json.loads(r.get('broadcast_json'))
        broadcast_json.append({'message':broadcast_new})
        r.set('broadcast_json', json.dumps(broadcast_json))
        flash(u'推送维护消息成功')
        MessageManager.push_message(r, r.hkeys('online'),PUSH_TYPE['fix_broadcast'],{'message':broadcast_new})
        return redirect(url_for('broadcast'))
    # else:
    #     return redirect(url_for('broadcast'))

@app.route('/pay_result_new', methods=['POST'])
def pay_result_new():
    data = json.loads(request.form['data'])
    sign = request.form['sign']
    # data['private'] = json.loads(data['private'])

    # 校验
    # if data['private']['privateInfo'] != get_md5(data['private']['order']+CHARGE_KEY+data['private']['other']):
    #     return json.dumps({'status':'FAIL'})
    # if get_sign(request.form['data']) != sign:
    #     return json.dumps({'status':'FAIL'})
    if get_context('session') == None:
        set_context('session', session)
    if receive_order_callback(session, r, da, data):
        return json.dumps({
            'status':'SUCCESS'
        })
    else:
        return json.dumps({
            'status':'FAIL'
        })

@app.route('/pay_result', methods=['POST'])
def pay_result():

    data = json.loads(request.form['data'])
    sign = request.form['sign']
    data['private'] = json.loads(data['private'])

    # 校验
    if data['private']['privateInfo'] != get_md5(data['private']['order']+CHARGE_KEY+data['private']['other']):
        return json.dumps({
            'status':'FAIL'
        })


    if get_sign(request.form['data']) != sign:
        return json.dumps({
            'status':'FAIL'
        })


    order_handle = OrderHandle(session)
    order_handle.get_order(data['private']['order'], data['private']['other'])
    print '--------->!!!!order',order_handle.order
    if order_handle.order_is_none():
        return json.dumps({
            'status':'FAIL'
        })
    order = order_handle.order

    print '==============>3'

    # 加载旧的充值排行
    rank_upp = RankUpper(session)
    rank_upp.get_old_index(order.uid)


    charge_money = decimal.Decimal( data['money'] )
    # 充值金额相等时
    status = 0
    if decimal.Decimal(order.money) != charge_money:
        # 充值金额不相等时
        status = 1

    charge_money = order_handle.order.money
    order_handle.update_order_status(data['private']['order'],data['order_sn'], charge_money, status)

    data['uid'] = order.uid
    print '======================>5',data
    mail = TMail()
    mail.from_user = 10000
    mail.to_user = order.uid
    mail.sent_time = time.time()
    mail.title = u'充值'

    mail.type = 0
    mail.diamond = 0
    mail.gold = 0
    mail.state = 1
    item_price = 0
    if order.shop_id > 0 and order.shop_id < 2000:
        shop_item = session.query(TChargeItem).filter(TChargeItem.id == order.shop_id).first()
        item_price = int(shop_item.money)
        mail.content = u'成功充值%.2f元' % (charge_money)
        if shop_item.type is not None and shop_item.type == 'gold':
            mail.content += u'，购买%d金币' % (shop_item.gold)
        if shop_item.type is not None and shop_item.type == 'diamond':
            mail.content += u'，购买%d个钻石' % (shop_item.diamond)
        if shop_item.extra_diamond is not None and shop_item.extra_diamond > 0:
            mail.content += u'，赠送%d个钻石' % shop_item.extra_diamond
    elif order.shop_id >= 2000:
        pop_activity = session.query(TPopActivity).filter(TPopActivity.id == order.shop_id).first()
        mail.content = pop_activity.description
    elif order.shop_id == 0:
        item_price = (FRIST_CHARGE['money'] / 100)
        mail.content = u'首冲成功%.2f元，获得%d万金币，%d个张喇叭卡，%d张踢人卡，%d张vip经验卡' %\
                       (item_price,FRIST_CHARGE['gold'] ,FRIST_CHARGE['hore'],FRIST_CHARGE['kicking_card'],FRIST_CHARGE['vip_card'])
    else:
        quick_charge = QUICK_CHARGE[abs(order.shop_id)-1]
        item_price = quick_charge[0] / 100
        mail.content = u'快充成功%.2f元，获得%d万金币' % (item_price ,quick_charge[1]  )

    mail.content += u'，获得%d张流量券' % int(charge_money)
    print 'shop_id--->',order.shop_id
    session.add(mail)
    session.flush()

    # Mail(from_user=10000, to_user=order.uid, title=u'流量卡', content=).send_mail(session)
    print 'mail_id--->',mail.id
    user_info = session.query(TUser).filter(TUser.id == order.uid).first()

    # 加vip经验
    vip_exp_log = ''
    old_vip_exp = 0 if user_info.vip_exp <= 0 else user_info.vip_exp
    old_vip_level = vip.to_level(old_vip_exp)
    vip_exp_log = 'old: %d, vip:%d, exp:%d \n' % (user_info.id, old_vip_level, old_vip_exp)
    new_vip_exp = old_vip_exp + item_price
    vip_exp_log += 'new: %d, exp:%d, item_price:%s' % (user_info.id, new_vip_exp,str(item_price))
    vip_exp_log += '---------------------------------------------\n'
    session.query(TUser).filter(TUser.id == user_info.id).update({
        TUser.vip_exp:new_vip_exp
    })
    user_info.vip_exp = new_vip_exp
    session.flush()
    new_vip_level = vip.to_level(user_info.vip_exp)
    with open('vip.log', 'a') as fp:
        fp.write(vip_exp_log)
    # vip升级送金币、道具、发广播
    if old_vip_level < new_vip_level:
        diff_level = new_vip_level - old_vip_level
        if diff_level > 0:
            print 'diff------------------->item_price',diff_level,item_price
            push_message(r,r.hkeys('online'),2,{'nick':user_info.nick,'vip_exp':user_info.vip_exp})
            print 'tolevel------>',vip.to_level(user_info.vip_exp)
            SystemAchievement(session,user_info.id).finish_upgrade_vip(vip.to_level(user_info.vip_exp))
            session.flush()
    # 通知用户充值成功
    push_message(r,[user_info.id],0,'',N_CHARGE)


    # if r.exists('u'+str(order.uid)):
    #     r.delete('u'+str(order.uid))


    gold = 0
    diamond = 0
    user_info = session.query(TUser).filter(TUser.id == order.uid).first()
    if order.shop_id == 0 and user_info.is_charge == 0:
        gold = FRIST_CHARGE['gold']
        diamond = FRIST_CHARGE['diamond']
        session.query(TUser).with_lockmode("update").filter(TUser.id == order.uid, TUser.is_charge == 0).update({
            TUser.is_charge:1,
            TUser.gold:TUser.gold + gold * 10000,
            TUser.diamond:TUser.diamond + diamond,
            TUser.money:TUser.money + charge_money,
        })


        for item in FRIST_CHARGE['items'].split(','):
            arr_item = item.split('-')
            save_countof(session, {
                'uid':order.uid,
                'stuff_id':arr_item[0],
                'countof':arr_item[1],
            })
    elif order.shop_id < 0:
        gold = quick_charge[1] * 10000
        session.query(TUser).with_lockmode("update").filter(TUser.id == order.uid).update({
            TUser.gold:TUser.gold + gold,
            TUser.money:TUser.money + charge_money,
        })
    elif order.shop_id >= 2000:
        gold = pop_activity.gold
        money = pop_activity.money
        session.query(TUser).with_lockmode("update").filter(TUser.id == order.uid).update({
            TUser.gold : TUser.gold + gold,
            TUser.money : TUser.money + money,
        })
        new_pop_activity_user = TPopActivityUser()
        new_pop_activity_user.uid = user_info.id
        new_pop_activity_user.activity_id = pop_activity.id
        session.add(new_pop_activity_user)
        session.flush()
    else:
        gold = shop_item.gold
        diamond = shop_item.diamond + shop_item.extra_diamond
        session.query(TUser).with_lockmode("update").filter(TUser.id == order.uid).update({
            TUser.gold:TUser.gold + gold,
            TUser.diamond:TUser.diamond + diamond,
            TUser.money:TUser.money + charge_money,
        })
    session.flush()
    session.query(TLucky).filter(TLucky.uid == order.uid).update({
        TLucky.lucky: TLucky.lucky + (charge_money * 10)
    })
    ChargeTop.save_rank(session, order.uid, gold,diamond, charge_money)
    rank_upp.get_new_index(order.uid)
    print '-------------->',rank_upp.before_index,rank_upp.after_index,type(rank_upp.before_index),type(rank_upp.after_index),user_info
    if rank_upp.is_up():
        MessageManager.push_message(r, r.hkeys('online'),PUSH_TYPE['sys_broadcast'],{'message':BORADCAST_CONF['charge_top'] % (user_info.nick, rank_upp.after_index)})


    print 'status, success'
    new_user_info = da.get_user(order.uid, True)

    # 更新用户信息队列
    r.lpush('war_user_update',json.dumps({'uid':order.uid}))

    print 'update user info gold,old_gold:%d,new_gold:%d' % (user_info.gold, new_user_info.get_gold())
    return json.dumps({
        'status':'SUCCESS'
    })

def get_sign(data):
    return hashlib.md5(PAY_CALLBACK_NEW+data+CP_KEY).hexdigest()

def get_md5(s):
    return hashlib.md5(s).hexdigest()


def save_countof(session, fields):
    insert_stmt = "INSERT INTO bag_item(uid,item_id,countof) VALUES (:col_1,:col_2,:col_3) ON DUPLICATE KEY UPDATE countof = countof + :col_3;"
    session.execute(insert_stmt, {
        'col_1':fields['uid'],
        'col_2':fields['stuff_id'],
        'col_3':fields['countof']
    })
    session.flush()

def save_charge_top(session, fields):
    insert_stmt = "INSERT INTO rank_charge_top(add_date,uid,charge_money) VALUES (:col_1,:col_2,:col_3) ON DUPLICATE KEY UPDATE charge_money = charge_money + :col_3;"
    session.execute(insert_stmt, {
        'col_1':time.strftime('%Y-%m-%d'),
        'col_2':fields['uid'],
        'col_3':fields['charge_money']
    })
    session.flush()

# push_message(r,[user_info.id],0,'',N_CHARGE)
# push_message(r,r.hkeys('online'),2,{'nick':user_info.nick,'vip_exp':user_info.vip_exp})
def push_message(r,users,p1,p2,notifi_type = 1):
    item = {'users':users,'notifi_type':notifi_type}
    if p1 is not None:
        item['param1'] = p1
    if p2 is not None:
        item['param2'] = p2

    r.lpush('notification_queue', json.dumps(item))

def unzip_file(zipfilename, unziptodir):

    zfobj = zipfile.ZipFile(os.path.join(os.path.join(unziptodir,BACK_UP),zipfilename))

    for name in zfobj.namelist():
        name = name.replace('\\','/')

        if name.endswith('/'):
            os.mkdir(os.path.join(unziptodir, name))
        else:
            ext_filename = os.path.join(unziptodir, name)
            ext_dir= os.path.dirname(ext_filename)
            if not os.path.exists(ext_dir) : os.mkdir(ext_dir,0777)
            outfile = open(ext_filename, 'wb')
            outfile.write(zfobj.read(name))
            outfile.close()

if __name__ == '__main__':
    # Entry the application
    app.run()