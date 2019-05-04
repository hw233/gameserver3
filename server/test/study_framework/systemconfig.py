import re
from ConfigParser import *

def itemsToOptions(items):
    options = {}
    for item in items:
        options[item[0]] = item[1]
    return options
    
class SystemConfig:
    def __init__(self,file,myselfName):
        self.file = file
        self.servers = []
        self.services = {}
        self.myself = None
        self.myselfName = myselfName
        self.parse()
        
        
    def get_redis_config(self,name):
        system_config = self.system_config
        host = system_config.get(name,"host")
        port = system_config.getint(name,"port")
        db = system_config.getint(name,"db")
        password = system_config.get(name,'password') if system_config.has_option(name,'password') else None
        return host,port,db,password
        
    def get_database_config(self,db_name):
        system_config = self.system_config
        user = system_config.get(db_name,"user")
        password = system_config.get(db_name,"password")
        if system_config.has_option(db_name,"db_host"):
            host = system_config.get(db_name,"db_host")
        else:
            host = "localhost"
        if system_config.has_option(db_name,"db_port"):       
            port = system_config.getint(db_name,"db_port")
        else:
            port = None
        database = system_config.get(db_name,"database")
        if system_config.has_option(db_name,"pool_size"): 
            pool_size = system_config.getint(db_name,"pool_size")        
        else:
            pool_size = 5

        return user,password,database,host,port,pool_size
        
    def parse(self):
        self.servers = []
        self.myself = None
        cp = ConfigParser()
        cp.read(self.file)
        self.system_config = cp
        self.options = itemsToOptions(cp.items("system"))
        if self.myselfName == None:
            return
        srv_names = cp.get("system","servers").split(" ")
        myselfName = self.myselfName
        for name in srv_names:
            srv_conf = ServerConfig(name, cp.get(name,"ip"), 
                                    cp.getint(name,"port"), itemsToOptions(cp.items(name)))
            self.servers.append(srv_conf)
            self.parseServer(srv_conf, cp)
            if (name == myselfName):
                self.myself = srv_conf
        
        if (self.myself == None):
            raise "Need set myself variable"

    def parseServer(self, srv_conf, parser):
        services = parser.get(srv_conf.name, "services").split(" ")
        for service in services:
            service = service.strip()
            if service == "":
                continue
            re_match = re.match(r"(\w+)\((\d+)\)",service)
            if re_match == None:
                id = parser.getint(service, "id")
            else:
                service = re_match.group(1)
                id = parser.getint(service, "id") + int(re_match.group(2))
            
            options = itemsToOptions(parser.items(service))
            service_config = ServiceConfig(srv_conf, id, service, options)
            srv_conf.addService(service_config)
            if self.services.get(service_config.service) == None:
                self.services[service_config.service] = [service_config]
            else:
                self.services[service_config.service].append(service_config)
            
            
    def __repr__(self):
        return self.myself.name + "->"  + str(self.servers)

class ServerConfig:
    def __init__(self,name,ip,port,options):
        self.name = name
        self.ip = ip
        self.port = port
        self.services = {}
        self.options = options
        
    def addService(self,serviceConfig):
        self.services[serviceConfig.id] = serviceConfig
        
    def __repr__(self):
        return self.name + str(self.services)

    
class ServiceConfig:
    def __init__(self,host,id,name,options):
        self.host = host
        self.id = id
        self.name = name
        handler = options.get("handler",None)
        if handler == None:
            n0 = name[0].upper()
            n1 = name[1:]
            handler = name + "." + name + "service." + n0 + n1 + "Service"
            options["handler"] = handler
        if options.get("service",None) == None:
            self.service = handler[handler.rindex(".")+1:]
        else:
            self.service = options.get("service")
        self.options = options
        
    def __repr__(self):
        return "host=" + self.host.name + " name=" + self.name + " id=" + str(self.id)

if __name__ == "__main__":
    import os,sys
    os.chdir(sys.path[0])

    config = SystemConfig("system.ini")
    
