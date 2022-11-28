import gevent.monkey
gevent.monkey.patch_all()

import socket
import re
import gevent

from requests import Session
from signalr import Connection

with Session() as session:
    #create a connection
    connection = Connection("https://cluesocket.azurewebsites.net", session)

    #get chat hub
    chat = connection.register_hub('chathub')

    #start a connection
    connection.start()

    #create new chat message handler
    def print_received_message(data):
        print('received: ', data)

    #create new chat topic handler
    def print_topic(topic, user):
        print('topic: ', topic, user)

    #create error handler
    def print_error(error):
        print('error: ', error)

    #receive new chat messages from the hub
    chat.client.on('newMessageReceived', print_received_message)

    #change chat topic
    chat.client.on('topicChanged', print_topic)

    #process errors
    connection.error += print_error

    #start connection, optionally can be connection.start()
    with connection:

        #post new message
        print("test2")
        chat.server.invoke('Send2', 'Conn1', 'Python is here')

        #change chat topic
##        chat.server.invoke('setTopic', 'Welcome python!')

        #invoke server method that throws error
##        chat.server.invoke('requestError')

        #post another message
##        chat.server.invoke('Send2', 'Bye-bye!')

        #wait a second before exit
        connection.wait(1)
