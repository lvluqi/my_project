import redis
import time
from threading import Thread
from prometheus_client import CollectorRegistry,Gauge,push_to_gateway


class MonitorRedis:
    def __init__(self,addr,password,port=6379):
        self.addr = addr
        self.password = password
        self.port = port

    def connect(self):
        client = redis.Redis(self.addr, password=self.password)
        return client

    def run(self,redis_list,job_name = "redis_list"):
        while True:
            registry = CollectorRegistry()
            for l in redis_list:
                # if client.llen(l) == 0:continue
                # print(registry)
                g = Gauge('redis_%s' % l, 'Last time a batch job successfully finished', registry=registry)
                client = self.connect()
                g.set(client.llen(l))
                push_to_gateway('10.0.20.216:9091', job=job_name, registry=registry)
                print "Push data successful"
            time.sleep(5)

def run(addr,password,redis_list,job_name):
    s = MonitorRedis(addr=addr,password=password)
    s.run(redis_list,job_name=job_name)

if __name__ == '__main__':

    stage_addr = 'r-bp1169460aee8dc4.redis.rds.aliyuncs.com'
    stage_password = "DevStageRedis2C3pQ5rpldkl98"
    stage_redis_list = ["php_redis_logstash_es","stage_redis_mq","stage_redis_es_batch_async_queue_v2","stage_redis_es_batch_async_queue"]
    stage_job_name = "stage_redis_list"

    live_addr = '773139e5e0a04b94.redis.rds.aliyuncs.com'
    live_password = 'AliyunRedis2C3pQ5rpldkl98'
    live_job_name = "live_redis_list"
    live_redis_list = ["app_redis_mq", "app_redis_es_batch_async_queue_v2", "app_redis_es_batch_async_queue"]


    p1 = Thread(target=run,args=(stage_addr,stage_password,stage_redis_list,stage_job_name))
    p2 = Thread(target=run,args=(live_addr,live_password,live_redis_list,live_job_name))


    p1.start()
    p2.start()