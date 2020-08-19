#!/usr/bin/env python

'''
secure_pubsub uses the "CURVE" security mechanism.
This gives us strong encryption on data, and (as far as we know) unbreakable
authentication. Stonehouse is the minimum you would use over public networks,
and assures clients that they are speaking to an authentic server, while
allowing any client to connect.

Original stonehouse.py from Chris Laws modified by Dan Cook

See: https://pyzmq.readthedocs.io/en/latest/api/zmq.auth.html

Usage:
    python secure_pubsub.py pub
    # open a new terminal
    python secure_pubsub.py secure_sub

Known issue:
    Subscription breaks for all future secure subscribers
    if a subscriber attempts to connect to the
    secure publisher without using a key, or using the wrong key.
    Not sure if this is true for c++ or c...
    cf. https://github.com/zeromq/libzmq/issues/882

'''

import logging
import os
import sys
import time
import argparse
import zmq
import zmq.auth
from signal import signal, SIGINT
from zmq.auth.thread import ThreadAuthenticator
import time

# These directories are generated by the generate_certificates script
BASE_DIR = os.path.dirname(__file__)
KEYS_DIR = os.path.join(BASE_DIR, 'certificates')
PUBLIC_KEYS_DIR = os.path.join(BASE_DIR, 'public_keys')
SECRET_KEYS_DIR = os.path.join(BASE_DIR, 'private_keys')

if not (os.path.exists(KEYS_DIR) and \
    os.path.exists(PUBLIC_KEYS_DIR) and \
    os.path.exists(SECRET_KEYS_DIR)):
    logging.critical("Certificates are missing: run gen_certs.py script first")
    sys.exit(1)

def secure_publisher():
    """
    This is the unity client.
    The unity client already knows the IP address of bruno.
    It will make a request over https for the server's public key.
    """
    context = zmq.Context.instance()
    # Start an authenticator for this context.
    auth = ThreadAuthenticator(context)
    auth.start()
    auth.allow('127.0.0.1')
    # Tell the authenticator how to handle CURVE requests
    # The client needs to know bruno's public key which is here placed
    # in the PUBLIC_KEYS_DIR
    auth.configure_curve(domain='*', location=PUBLIC_KEYS_DIR)
    socket = context.socket(zmq.PUB)
    unity_secret_file = os.path.join(SECRET_KEYS_DIR, "unity.key_secret")
    unity_public, unity_secret = zmq.auth.load_certificate(unity_secret_file)
    socket.curve_secretkey = unity_secret
    socket.curve_publickey = unity_public
    socket.curve_server = True  # must come before bind/connect
    socket.connect('tcp://127.0.0.1:9000')
    def exit_handler(signal_received, frame):
        # Handle any cleanup here
        logging.info('SIGINT or CTRL-C detected. Exiting gracefully')
        auth.stop()
        sys.exit(0)
    signal(SIGINT, exit_handler)
    while True:
        msg = "Hello world!"
        socket.send_string(msg)
        logging.info(msg)
        time.sleep(1.0)


def secure_subscriber():
    context = zmq.Context.instance()
    auth = ThreadAuthenticator(context)
    auth.start()
    socket = context.socket(zmq.SUB)
    bruno_secret_file = os.path.join(SECRET_KEYS_DIR, "bruno.key_secret")
    bruno_public, bruno_secret = zmq.auth.load_certificate(bruno_secret_file)
    socket.curve_secretkey = bruno_secret
    socket.curve_publickey = bruno_public
    # This step is critical.
    # Bruno must know the client's public key to make the CURVE connection.
    publisher_public_file = os.path.join(PUBLIC_KEYS_DIR, "unity.key")
    publisher_public, _ = zmq.auth.load_certificate(publisher_public_file)
    socket.curve_serverkey = publisher_public
    socket.bind('tcp://127.0.0.1:9000')
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    def exit_handler(signal_received, frame):
        # Handle any cleanup here
        logging.info('SIGINT or CTRL-C detected. Exiting gracefully')
        auth.stop()
        sys.exit(0)
    signal(SIGINT, exit_handler)
    while True:
        msg = socket.recv_string()
        logging.info("Got a message: '{}'".format(msg))

def exit_handler(signal_received, frame):
    # Handle ctrl-c cleanup here for terminating the while loops in pub and sub
    logging.info('SIGINT or CTRL-C detected. Exiting gracefully')
    auth.stop()
    sys.exit(0)

if __name__ == '__main__':
    if zmq.zmq_version_info() < (4,0):
        raise RuntimeError("Security is not supported in libzmq "+\
            "version < 4.0. libzmq version {0}".format(zmq.zmq_version()))
    level = logging.INFO
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")
    choices = {'pub': secure_publisher, 'sub': secure_subscriber}
    parser = argparse.ArgumentParser(description='Publish / Subscribe securely')
    parser.add_argument('role', choices=choices, help='which role to take')
    args = parser.parse_args()
    function = choices[args.role]
    function()