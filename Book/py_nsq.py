# import nsq
#
# def handler(message):
#     print(message)
#     return True
#
# r = nsq.Reader(message_handler=handler,lookupd_http_addresses=['http://192.168.0.216:47686'],
#                topic='nsq_reader',channel='asdf',
#                lookupd_poll_interval=15)
# nsq.run()

# import functools
# import tornado.httpserver
# import tornado.ioloop
# import tornado.options
# import tornado.web
# from nsq import Writer, Error
# from tornado.options import define, options
#
# class MainHandler(tornado.web.RequestHandler):
#     @property
#     def nsq(self):
#         return self.application.nsq
#
#     def get(self):
#         topic = 'log'
#         msg = 'Hello world'
#         msg_cn = 'Hello 世界'
#
#         self.nsq.pub(topic, msg) # pub
#         self.nsq.mpub(topic, [msg, msg_cn]) # mpub
#         self.nsq.dpub(topic, 60, msg) # dpub
#
#         # customize callback
#         callback = functools.partial(self.finish_pub, topic=topic, msg=msg)
#         self.nsq.pub(topic, msg, callback=callback)
#
#         self.write(msg)
#
#     def finish_pub(self, conn, data, topic, msg):
#         if isinstance(data, Error):
#             # try to re-pub message again if pub failed
#             self.nsq.pub(topic, msg)
#
# class Application(tornado.web.Application):
#     def __init__(self, handlers, **settings):
#         self.nsq = Writer(['127.0.0.1:4150'])
#         super(Application, self).__init__(handlers, **settings)



import nsq
import tornado.ioloop
import time


def pub_message():
    writer.pub('topic1', time.strftime('%H:%M:%S').encode("utf-8"), finish_pub)


def finish_pub(conn, data):
    print(data)



# writer = nsq.Writer(nsqd_tcp_addresses=['10.80.0.185:30191'])
writer = nsq.Writer(['127.0.0.1:4150'])
tornado.ioloop.PeriodicCallback(pub_message, 1000).start()
nsq.run()