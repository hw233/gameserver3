#coding: utf-8
'''
Created on 2012-2-20

@author: Administrator
'''

from gevent import monkey;monkey.patch_all()


from testbase import *

class TestCase:
    def __init__(self):
        self.client = None
        self.user = -1


    def test(self,user,password,need_idle,*args):
        try:
            MessageMapping.init()
            self.client = TestClient(user,password)
            resp = self.client.test_enter_server()
            self.user = resp.header.user
            it = iter(args)
            message = None
            message_args = []
            while True:
                try :
                    arg = it.next()
                except:
                    break
                    print '================>'
                    print args
                if arg.endswith("Req"):
                    proto = it.next()
                    if message != None:
                        resp = self.client.call_message_by_name(self.user,proto,message,*message_args)
                    message = arg
                    message_args = []
                elif arg.startswith("-t"):
                    #time.sleep(int(arg[2:]))
                    pass
                else:
                    message_args.append(arg)

            resp = self.client.call_message_by_name(self.user,proto,message,*message_args)

            if need_idle:
                self.client.idle(self.handle_message)
            print "== result ==>",resp.header.result
        except:
            traceback.print_exc()
        finally:
            pass


    def handle_message(self,message):
        if message.header.command == GameTurnEvent.ID and self.user == message.body.current:
            print "====> send back bet action"
            req = create_client_message(BetActionReq)
            req.header.user = self.user
            req.body.table_id = message.body.table_id
            req.body.action = ADD
            req.body.gold = 2000
            req.body.other = -1

            self.client.socket.send(req.encode())

if __name__ == "__main__":
    tc = TestCase()
    if sys.argv[1] != "-w":
        #test_defaultuser(sys.argv[1],"123456",False,*sys.argv[2:])
        tc.test(sys.argv[1],"123456",False,*sys.argv[2:])
    else:
        tc.test(sys.argv[2],"123456",True,*sys.argv[3:])
    print "Done"