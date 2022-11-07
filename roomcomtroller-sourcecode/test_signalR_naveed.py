from requests import Session
from signalr import Connection

with Session() as session:
    #create a connection
    connection = Connection("https://devapi.cluemaster.io", session)

    #get chat hub
    chat = connection.register_hub('chatHub')

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
    chat.client.on('Send2', print_received_message)

    

    #process errors
    connection.error += print_error

    #start connection, optionally can be connection.start()
    with connection:

        #post new message
        chat.server.invoke('Send2', 'Python is here')

        #change chat topic
        chat.server.invoke('Send2', 'Welcome python!')

    
        #post another message
        chat.server.invoke('Send2', 'Bye-bye!')

        #wait a second before exit
        connection.wait(1)
