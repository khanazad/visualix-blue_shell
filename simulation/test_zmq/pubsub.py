# -*- coding:utf-8 -*-
'''
Author: Dan Cook
The client method sub takes the argument zip_filter.
If the server method publishes anything related to the zip_filter,
then the client will aggregate this information. After it collections 5 different updates, it will spit out the mean.
'''

import argparse, sys, zmq
from random import randrange

def pub(port):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:%s" %port)
    while True:
        zipcode = randrange(1, 100000)
        temperature = randrange(40, 85)
        relhumidity = randrange(10, 60)
        socket.send_string("%i %i %i" % (zipcode, temperature, relhumidity))

def sub(port, filter):
    #  Socket to talk to server
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    print("Collecting updates from server...")
    socket.connect("tcp://localhost:%s" %port)
    # Subscribe to zip code filter, default is Philadelphia, 19152
    socket.setsockopt_string(zmq.SUBSCRIBE, filter)
    # Process 5 updates
    total_temp = 0
    for update_nbr in range(5):
        string = socket.recv_string()
        zipcode, temperature, relhumidity = string.split()
        total_temp += int(temperature)
    print("Average temperature for zipcode %s was %dF" % (filter, total_temp/update_nbr))

if __name__ == '__main__':
    choices = {'pub': pub, 'sub': sub}
    parser = argparse.ArgumentParser(description='Publish / Subscribe to a stream of (fake) temperature data')
    parser.add_argument('role', choices=choices, help='which role to take')
    parser.add_argument('--port', metavar='port', type=str, default='5556', help='Port of the localhost publisher')
    parser.add_argument('--filter', metavar='filter', type=str, default='19152', help='Zipcode to subsribe to.')
    args = parser.parse_args()
    if args.role == 'pub':
        function = choices[args.role]
        function(args.port)
    else:
        function = choices[args.role]
    function(args.port, args.filter)
