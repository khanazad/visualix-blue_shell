
# -*- coding:utf-8 -*-
'''
Simulate the different ports of bruno and the client communication with those
ports.
'''

import argparse, json, random, sys, threading, time, zmq

MULTI_SUBSCRIBERS = False

class BrunoMap(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print("Starting subscriber")
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.setsockopt(zmq.RCVTIMEO, -1)
        socket.setsockopt(zmq.SNDTIMEO, -1)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt_string(zmq.SUBSCRIBE, '')
        if MULTI_SUBSCRIBERS: # this way does not allow for multiple clients
            # to publish mapping data to the same bruno at the same time
            # but it allows for multiple servers to receive a single clients
            # mapping data simultaenously, which can provide for fault
            # tolerance
            socket.connect("tcp://127.0.0.1:5791")
        else: # The current way it is done does not allow multiple brunos
            # to receive mapping data of the same client simultaneously.
            # However, many clients can push to the same bruno at the same time.
            socket.bind("tcp://127.0.0.1:5791")
        while True:
            string = socket.recv_string()
            vals = json.loads(string)
            print(vals)

class BrunoLocate(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        context = zmq.Context()
        frontend = context.socket(zmq.ROUTER)
        frontend.bind("tcp://127.0.0.1:5792")
        backend = context.socket(zmq.DEALER)
        backend.bind('inproc://backend')
        # Call bruno computer vision logic here...
        workers = []
        n_workers = 5
        for worker_n in range(n_workers):
            worker = BrunoWorker(context, str(worker_n))
            worker.start()
            workers.append(worker)
        zmq.proxy(frontend, backend)
        frontend.close()
        backend.close()
        context.term()

class BrunoWorker(threading.Thread):

    def __init__(self, context, thread_id):
        threading.Thread.__init__(self)
        self.context = context
        self.thread_id = thread_id

    def run(self):
        worker = self.context.socket(zmq.DEALER)
        #worker.setsockopt_string(zmq.IDENTITY, self.thread_id)
        worker.connect('inproc://backend')
        while True:
            # get the client's session-id and message
            session_id, msg = worker.recv_multipart()
            print(
                'Bruno worker-{} received {} from client-{}'.format(
                    self.thread_id,
                    msg.decode('utf-8'),
                    session_id.decode('utf-8')
                )
            )
            # simulate some processing time
            time.sleep(random.random())
            # return the response to the client-session-id
            response = "Worker-{} served request {} from client-{}".format(
                self.thread_id,
                msg.decode('utf-8'),
                session_id.decode('utf-8')
            )
            time.sleep(random.random())
            print(response)
            worker.send_multipart([session_id, response.encode("utf-8")])
        worker.close()

class UnityLocate(threading.Thread):

    def __init__(self, session_id):
        self.session_id = session_id
        threading.Thread.__init__(self)

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.DEALER)
        session_id = u'%s' % self.session_id
        socket.identity = session_id.encode('ascii') # what does this do?!
        socket.connect('tcp://localhost:5792')
        print('Client started with sessions_id %s' % (session_id))
        poll = zmq.Poller()
        poll.register(socket, zmq.POLLIN)
        reqs = 0
        while True:
            reqs = reqs + 1
            print(
                'sent=req#%d, session=%s' %(reqs,self.session_id)
            )
            socket.send_string(u'{"req#": "%d", "id": "%s"}' %(reqs, self.session_id))
            for i in range(5):
                sockets = dict(poll.poll(1000))
                if socket in sockets:
                    msg = socket.recv()
                    print('recv=[%s], session=%s' %(msg.decode('utf-8'), self.session_id))
        socket.close()
        context.term()

class UnityMap(threading.Thread):

    def __init__(self, session_id):
        self.session_id = session_id
        threading.Thread.__init__(self)

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket.setsockopt(zmq.LINGER, 0)
        if MULTI_SUBSCRIBERS:# The client binds itself to an address
            # so that we can have multiple servers subscribing to the client's
            # updates about itself
            socket.bind("tcp://127.0.0.1:5791")
        else: # In the current set-up, however,
            # the client connects to a subscribers bind socket
            # so this is really like a push and not a pub
            # it allows multiple clients to push to same bruno
            # at the same time. I don't know why that is desired.
            # https://stackoverflow.com/questions/47495910/what-is-the-difference-between-using-zmq-pub-with-connect-or-bind-methods
            socket.connect("tcp://127.0.0.1:5791")
        socket.setsockopt(zmq.RCVTIMEO, -1)
        for sample in range(10):
            socket.send_string(json.dumps({"hello": "world", "client": self.session_id}))
            time.sleep(.5)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Bruno comm socket testing'
    )

    parser.add_argument(
        "role",
        metavar="role",
        type=str,
        help="",
    )

    parser.add_argument(
        "func",
        metavar="func",
        type=str,
        help="",
    )

    args = parser.parse_args()
    role = args.role
    func = args.func

    if role == "server" and func == "map":
        server = BrunoMap()
        server.start()

    if role == "server" and func == "locate":
        server = BrunoLocate()
        server.start()

    if role == "client" and func == "map":
        for clients in range(3):
            session_id = str(random.randint(1, 100000))
            client = UnityMap(session_id)
            client.start()
        client.join()

    if role == "client" and func == "locate":
        for clients in range(3):
            session_id = str(random.randint(1, 100000))
            client = UnityLocate(session_id)
            client.start()
        client.join()
