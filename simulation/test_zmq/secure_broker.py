#!/usr/bin/env python

import argparse
import os
import random
import threading
import time
import zmq
import zmq.auth
from zmq.auth.thread import ThreadAuthenticator

import uuid
import shutil

SCRIPT_DIRNAME, SCRIPT_FILENAME = os.path.split(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.dirname(SCRIPT_DIRNAME)


class BrunoLocate(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.private_key = \
            os.path.join(SCRIPT_DIRNAME, "private_keys", "bruno.key_secret")
        base_dir = os.path.join(SCRIPT_DIRNAME, 'secure-locate-certs')
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
        public_keys_dir = os.path.join(base_dir, 'public_keys')
        if not os.path.exists(public_keys_dir):
            os.mkdir(public_keys_dir)
        self.allowed_certs_dir = public_keys_dir

    def run(self):
        context = zmq.Context.instance()
        auth = ThreadAuthenticator(context)


        frontend = context.socket(zmq.ROUTER)
        foo, bar = zmq.auth.load_certificate(self.private_key)
        frontend.curve_publickey = foo
        frontend.curve_secretkey = bar
        frontend.curve_server = True

        print("Allowing keys in {}".format(self.allowed_certs_dir))
        auth.start()
        auth.allow('127.0.0.1')
        auth.configure_curve(domain='*', location=self.allowed_certs_dir)

        frontend.bind("tcp://127.0.0.1:5792")



        backend = context.socket(zmq.DEALER)
        # backend.curve_publickey = foo
        # backend.curve_secretkey = bar
        # backend.curve_server = True
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

    # def reconfigure_curve(self):
    #

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
        self.client_id = str(uuid.uuid4())
        self.gen_cert()

    def run(self):
        context = zmq.Context.instance()
        pub, priv = zmq.auth.load_certificate(self.secret_key)
        socket = context.socket(zmq.DEALER)
        socket.curve_publickey = pub
        socket.curve_secretkey = priv

        session_id = u'%s' % self.session_id
        socket.identity = session_id.encode('ascii') # what does this do?!
        server_pub, _ = zmq.auth.load_certificate(
            os.path.join(SCRIPT_DIRNAME, "public_keys", "bruno.key")
        )

        socket.curve_serverkey = server_pub
        socket.connect('tcp://127.0.0.1:5792')
        print('Client %s started with sessions_id %s' % (self.client_id, session_id))
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

    def gen_cert(self, base_dir=SCRIPT_DIRNAME):
        ''' Generate client CURVE certificate files'''
        base_dir = os.path.join(base_dir, 'secure-locate-certs')
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)

        keys_dir = os.path.join(base_dir, 'certificates')
        if not os.path.exists(keys_dir):
            os.mkdir(keys_dir)

        public_keys_dir = os.path.join(base_dir, 'public_keys')
        if not os.path.exists(public_keys_dir):
            os.mkdir(public_keys_dir)

        secret_keys_dir = os.path.join(base_dir, 'private_keys')
        if not os.path.exists(secret_keys_dir):
            os.mkdir(secret_keys_dir)

        # create new keys in certificates dir
        client_public_file, client_secret_file = zmq.auth.create_certificates(
            keys_dir, self.client_id
        )

        # move public keys to public_keys directory
        for key_file in os.listdir(keys_dir):
            if key_file.endswith(".key"):
                shutil.move(os.path.join(keys_dir, key_file),
                            os.path.join(public_keys_dir, '.'))

        # move secret keys to private_keys directory
        for key_file in os.listdir(keys_dir):
            if key_file.endswith(".key_secret"):
                shutil.move(os.path.join(keys_dir, key_file),
                            os.path.join(secret_keys_dir, '.'))

        self.keys_dir = keys_dir
        self.public_keys_dir = public_keys_dir
        self.secret_keys_dir = secret_keys_dir
        self.pub_key = os.path.join(public_keys_dir, self.client_id+".key")
        self.secret_key = os.path.join(secret_keys_dir,
            self.client_id+".key_secret"
        )


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Router dealer with curve'
    )

    parser.add_argument(
        "role",
        metavar="role",
        type=str,
        help="",
    )

    args = parser.parse_args()
    role = args.role

    if role == "server":
        server = BrunoLocate()
        server.start()

    if role == "client":
        for clients in range(3):
            session_id = str(random.randint(1, 100000))
            client = UnityLocate(session_id)
            client.start()
        client.join()
