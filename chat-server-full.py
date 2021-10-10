# Chat-server-client: educative chat client/server programs
#     Copyright (C) 2021 ALLAUD Emmanuel

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

# email: eallaud@gmail.com

#network imports
import socket
import select

#database imports
import sqlite3
from sqlite3 import Error

#files imports
import os

#time imports
import time

class client:
    def __init__(self,cmds_sock,ID):
        self.cmds_sock = cmds_sock
        self.waiting_ack = False
        self.msg_list = []
        self.addr=cmds_sock.getpeername()
        self.ID = ID
        self.nick = None
        self.msgs_sock = None
        self.db_id=None

    def new_msg(self,msg):
        print("before msg list=",self.msg_list)
        self.msg_list.append(msg)
        print("after msg list=",self.msg_list)
        self.process()

    def process(self):
        print("process()")
        #print("before",self.waiting_ack)
        if not self.waiting_ack:
            if self.msg_list:

                print("will send",self.msg_list[0],"to ",self.msgs_sock.getpeername())
                sent=True
                try:
                    self.waiting_ack = True
                    if self.msgs_sock is not None:
                        self.msgs_sock.send(self.msg_list[0].encode('utf-8'))
                except socket.error:
                    print("Send error")
                    sent=False
                if sent:
                    self.msg_list.pop(0)
        #print("after",self.waiting_ack)

    def ack(self):
        if self.waiting_ack:
            self.waiting_ack = False
            self.process()
        else:
            if self.msgs_sock is not None:
                print("got ack while not waiting for ",self.msgs_sock.getpeername())
            #pass

class channel:
    def __init__(self,name):
        self.name = name
        self.clients = []
        self.db_id = None

    def new_msg(self,emitter,msg,include_emitter=False):
        for c in self.clients:
            #dispatch msg to all other socks
            if c!=emitter or include_emitter:
                c.new_msg(msg)

    def still_in_use(self):
        return len(self.clients)>0


def get_clients_ready():
    """
    return a list of clients who have sent something, needing to be read then
    """
    to_delete=[]
    for i in range(len(clients_read_list)):
        s=clients_read_list[i]
        if s.fileno()==-1:
            to_delete.append(i)
    to_delete.reverse()
    for i in to_delete:
        print("Delete from client_read_list",i)
        clients_read_list.pop(i)
    try:
        ready_to_read,ready_to_write,in_error = select.select(clients_read_list,[],[],0)
    except:
        for s in clients_read_list:
            print(s,"fileno=",s.fileno())
        return []

    return ready_to_read

# client connects to the command socket first
def new_client_first_step():
    global controlsock_connected
    global last_ID

    clientsocket,addr = serversocket_cmd.accept()
    clients_read_list.append(clientsocket)

    address = (str(addr).split("'"))[1]
    print("Got a connection from",address,"to the command socket, ID is set to ", last_ID)

    #first client to connect is the controlsock one
    if not controlsock_connected:
        #make sure we treat control socket differently from "normal" clients
        controlsock_connected = True
        print("control socket is connected")
        last_ID+=1
        return

    #send the ID associated to the client; it will use it to connect to the messages socket
    clientsocket.send(("/ID "+str(last_ID)).encode('utf-8'))

    #create the client object and add it to the dictionnary commands sockets <--> client objects
    cl = clients[clientsocket] = client(clientsocket,last_ID)

    last_ID+=1

def second_step_new_client():

    clientsocket,addr = serversocket_msgs.accept()
    clients_read_list.append(clientsocket)

    waiting_msgs_socks.append(clientsocket)
    address = (str(addr).split("'"))[1]
    print("Got a connection from",address," on messages socket")

def delete_client_from_channels(client):
    global controlsock_cmds
    to_delete=""
    for ch in channels:
        if client in ch.clients:
            #database update
            deconnect_channel_client_db(ch,client)
            ch.clients.remove(client)
            if not ch.still_in_use():
                to_delete+=" "+ch.name

    print("delete client from channels",to_delete)
    if to_delete!="":
        controlsock_cmds.append("/deletechannels"+to_delete)
        print(controlsock_cmds)

def deconnect_client(sock):
    """
    deconnects the client
    """
    global clients_read_list,clients
    msgs_sock = None
    #check if a channel is now empty, in that case send a delete message
    if sock in clients:
        print("Client (ID",clients[sock].ID,") at",clients[sock].addr, "is now deconnected!")
        deconnect_client_db(clients[sock])
        delete_client_from_channels(clients[sock])
        #Here remember to clean the dictionaries
        nick = clients[sock].nick
        msgs_sock = clients[sock].msgs_sock
        del clients[sock]
        if nick is not None:
            broadcast("/disconnected "+nick)

    if sock in clients_read_list:
        clients_read_list.remove(sock)
    sock.close()
    if msgs_sock is not None:
        if msgs_sock in clients_read_list:
            clients_read_list.remove(msgs_sock)
        msgs_sock.close()

def broadcast(msg):
    print("broadcasting",msg)
    for s,c in clients.items():
        if c!=None:
            c.new_msg(msg)

def set_nick(sock,nick):
    new = (clients[sock].nick==None)
    for s,c in clients.items():
        if c.nick == nick and s!=sock:
            sock.send("/NOK nickname already in use".encode('utf-8'))
            return
    sock.send("/OK".encode('utf-8'))
    if new:
        msg = "/new "+nick
    else:
        msg = "/changed "+clients[sock].nick+" "+nick
    clients[sock].nick=nick
    broadcast(msg)
    update_client_nick_db(clients[sock])

def new_channel(chan):
    print("new channel created",chan)
    broadcast("/new "+chan)
    ch = channel(chan)
    return ch

def join_channel(sock,chan):
    if chan=='':
        return
    new = True
    if chan[0]!="#" or " " in chan:
        sock.send("/NOK bad channel name".encode('utf-8'))
        return
    for ch in channels:
        if chan==ch.name:
            if clients[sock] in ch.clients:
                sock.send("/NOK already in channel".encode('utf-8'))
                return
            new = False
            break
    sock.send("/OK".encode('utf-8'))
    if new:
        ch = new_channel(chan)
        channels.append(ch)
        add_to_channels_table(ch,clients[sock])
    ch.clients.append(clients[sock])
    ch.new_msg(clients[sock],"/joined "+ch.name+" "+clients[sock].nick,True)
    add_channel_client_db(ch,clients[sock])

def find_channel(name):
    for ch in channels:
        if ch.name == name:
            return ch
    return None

def find_client_from_ID(ID):
    for s,c in clients.items():
        if c.ID==ID:
            return c
    return None

def find_msgs_sock_client(sock):
    for s,c in clients.items():
        if c.msgs_sock == sock:
            return c
    return None

def parse(sock,msg):
    """
    parse msg (coming from sock)
    """
    global controlsock_cmds

    #check first if this sock is a messages socket not yet associated with a client trying to finish the connection procedure
    if sock in waiting_msgs_socks:
        #msg should be /connect ID
        if msg.startswith("/connect"):
            ID=-1
            try:
                ID = int(msg[len("/connect"):].lstrip())
            except:
                print("No ID returned from messages sock!")
            cl = find_client_from_ID(ID)
            if cl is not None:
                #OK Found it, finish connection procedure
                cl.msgs_sock = sock
                waiting_msgs_socks.remove(sock)
                sock.send("/OK".encode('utf-8'))
                add_to_clients_table(cl)
                return
            else:
                #ID not found
                print("Client ID (",ID,") was not found!")
                sock.send("/NOK ID not found".encode('utf-8'))
        else:
       	    print("Malformed ID response!")
            sock.send("/NOK Malformed ID response".encode('utf-8'))
            return

    #check if its a message sock ack
    cl = find_msgs_sock_client(sock)
    if cl is not None:
        if msg=="/OK":
            cl.ack()
        else:
            print("Malformed ACK from client at ",cl.msgs_sock.getpeername())
        return
    #normal command message
    print(msg)
    if msg[0]=="/":
        params = msg[1:].split(' ')
        print(params)
        if params[0]=="OK":
            if sock in clients:
                clients[sock].ack()
        elif params[0]=="nick":
            set_nick(sock,msg[6:])
        elif params[0]=="disconnect":
            sock.send(("/disconnected "+clients[sock].nick).encode('utf-8'))
            deconnect_client(sock)
        elif params[0] == "deletechannels":
            if sock.getsockname()!=controlsock.getpeername():
                print("/NOK unauthorized command")
                sock.send("/NOK unauthorized command".encode('utf-8'))
                return
            print("deleting channels",params[1:])
            for ch in params[1:]:
                channel = find_channel(ch)
                if channel is None:
                    print("control socket error: channel to delete does not exist:"+ch)
                else:
                    deconnect_channel_db(channel)
                    channels.remove(channel)
                    print(len(channels)," channels available")
                    broadcast("/deletedchannel "+ch)
        else:
            if sock==serversocket_cmd:
                print("serversocket in parse",msg);
            elif sock==controlsock:
                print("control socket in parse",msg)
            if params[0]=="join":
                if clients[sock].nick==None:
                    sock.send("/NOK client with no nickname".encode('utf-8'))
                    return
                join_channel(sock,msg[6:])
            elif params[0]=="msg":
                if clients[sock].nick==None:
                    sock.send("/NOK client with no nickname".encode('utf-8'))
                    return

                if len(params)<3:
                    sock.send("/NOK empty or malformed msg command".encode('utf-8'))
                    return
                if params[1].startswith("#"):
                    ch = find_channel(params[1])
                    if ch==None:
                        clients[sock].new_msg("/NOK unknown channel "+params[1])
                        return
                    if clients[sock] not in ch.clients:
                        sock.send(("/NOK you have not joined channel "+params[1]).encode('utf-8'))
                        return

                    print("msg to channel",ch.name,"=",' '.join(params[2:]))
                    ch.new_msg(clients[sock],"/received "+clients[sock].nick+" "+' '.join(params[2:]))
                    sock.send("/OK".encode('utf-8'))
                else:
                    found = False
                    for s,c in clients.items():
                        if c.nick == params[1]:
                            found = True
                            break
                    if not found:
                        sock.send("/NOK unknown nickname".encode('utf-8'))
                    else:
                        c.new_msg("/received "+clients[sock].nick+" "+" ".join(params[2:])) # send to destination
                        sock.send("/OK".encode('utf-8')) #send to origin
            elif params[0]=="list":
                sock.send("/OK".encode('utf-8'))
                msg="/list"
                for ch in channels:
                    msg+=" "+ch.name
                clients[sock].new_msg(msg)
            elif params[0]=="names":
                ch=None
                if len(params)==2:
                    ch = find_channel(params[1])
                    if ch==None:
                        sock.send("/NOK unknown channel".encode('utf-8'))
                        return
                sock.send("/OK".encode('utf-8'))
                msg = "/names"
                if ch is not None:
                    msg+=" "+ch.name

                for s,c in clients.items():
                    if c.nick != None:
                        if ch == None or c in ch.clients:
                            msg+=" "+c.nick
                clients[sock].new_msg(msg)
            elif params[0]=="part":
                if clients[sock].nick==None:
                    sock.send("/NOK client with no nickname".encode('utf-8'))
                    return

                ch = find_channel(params[1])
                if ch==None:
                    sock.send("/NOK unknown channel".encode('utf-8'))
                    return
                if clients[sock] not in ch.clients:
                    sock.send(("/NOK you have not joined channel "+params[1]).encode('utf-8'))
                    return
                #update channel <-> client relation (deletion time)
                deconnect_channel_client_db(ch,clients[sock])
                
                if ch.still_in_use():
                    #this channel wont be closed, there are other clients in it
                    ch.new_msg(clients[sock],"/parted "+params[1]+" "+clients[sock].nick,True)

                sock.send("/OK".encode('utf-8'))
                ch.clients.remove(clients[sock])
                if not ch.still_in_use():
                    #delete channel
                    controlsock_cmds.append("/deletechannels "+ch.name)
                    print("will remove unused channel",ch.name)

#            elif params[0]=="partall":
#                nb = 0
#                for ch in channels:
#                    if clients[sock] in ch.clients:
#                        nb+=1
#                        ch.new_msg(clients[sock],"/parted "+ch.name+" "+clients[sock].nick)
#                        ch.clients.remove(clients[sock])
#                if nb==0:
#                    clients[sock].new_msg("/NOK you have joined no channel yet", True)
#                    return
#                else:
#                    delete_client_from_channels(clients[sock])
#                    clients[sock].new_msg("/parted "+str(nb)+" channel(s)",True)
            elif params[0]=="amsg":
                if clients[sock].nick==None:
                    sock.send("/NOK client with no nickname".encode('utf-8'))
                    return

                nb = 0
                for ch in channels:
                    if clients[sock] in ch.clients:
                        ch.new_msg(clients[sock],"/msg "+clients[sock].nick+" "+' '.join(params[1:]))
                        nb+=1
                if nb==0:
                    sock.send("/NOK you have joined no channel yet".encode('utf-8'))
                    return
                else:
                    clients[sock].new_msg("/sent "+' '.join(params[1:])+" in "+str(nb)+" channel(s)")
            else:
                sock.send("/NOK bad command".encode('utf-8'))
    else:
        sock.send("/NOK bad command".encode('utf-8'))

def get_local_IP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

#database related functions

def create_db(connection):
    #query to create the clients table
    queries = ["""
    CREATE TABLE IF NOT EXISTS clients (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      client_ID INT,
      nick TEXT DEFAULT NULL,
      addr TEXT NOT NULL,
      connection DATETIME,
      deconnection DATETIME DEFAULT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS channels (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      creation DATETIME,
      deletion DATETIME DEFAULT NULL,
      creator_id INT,
      FOREIGN KEY (creator_id) REFERENCES clients(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS clientschannels (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      channel_id INT,
      client_id INT,
      creation DATETIME,
      deletion DATETIME,
      FOREIGN KEY (channel_id) REFERENCES channels(id) FOREIGN KEY (client_id) REFERENCES clients(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS msgstochannels (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      from_client INT,
      to_channel INT,
      message TEXT NOT NULL,
      FOREIGN KEY (to_channel) REFERENCES channels(id) FOREIGN KEY (from_client) REFERENCES clients(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS msgstoclients (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      from_client INT,
      to_client INT,
      message TEXT NOT NULL,
      FOREIGN KEY (to_client) REFERENCES clients(id) FOREIGN KEY (from_client) REFERENCES clients(id)
    );
    """]
    for query in queries:
        if not execute_query(connection,query):
            return False
    return True

def add_to_clients_table(cl):
    query="""
    INSERT INTO clients(client_id,nick,addr,connection,deconnection)
    VALUES
    """
    if cl.nick is None:
        nick = ""
    else:
        nick = cl.nick
    query+=" ("+str(cl.ID)+",'"+nick+"','"+cl.addr[0]+"','"+time.strftime("%Y%m%dT%X")+"','');"
    cl.db_id = execute_query_PK(db_connection,query)

def update_client_nick_db(cl):
    query="UPDATE clients SET nick='"+cl.nick+"' WHERE id="+str(cl.db_id)
    execute_query(db_connection,query)

def deconnect_client_db(cl):
    query="UPDATE clients SET deconnection='"+time.strftime("%Y%m%dT%X")+"' WHERE id="+str(cl.db_id)
    execute_query(db_connection,query)

def add_to_channels_table(channel,client):
    #create channel in the channels table
    query="""
    INSERT INTO channels(name,creation,deletion,creator_id)
    VALUES
    """
    t = time.strftime("%Y%m%dT%X")
    query+=" ('"+channel.name+"','"+t+"','',"+str(client.db_id)+");"
    channel.db_id = execute_query_PK(db_connection,query)

def add_channel_client_db(channel,client):
    #add the channel<->client relation
    query="""
    INSERT INTO clientschannels(channel_id,client_id,creation,deletion)
    VALUES
    """
    t = time.strftime("%Y%m%dT%X")
    query+=" ("+str(channel.db_id)+","+str(client.db_id)+",'"+t+"','');"
    execute_query(db_connection,query)

def deconnect_channel_client_db(channel,client):
    #update the channel<->client relation deletion time
    t = time.strftime("%Y%m%dT%X")
    query="UPDATE clientschannels SET deletion='"
    query+=t+"' WHERE channel_id="+str(channel.db_id)+" AND client_id="+str(client.db_id)
    execute_query(db_connection,query)
  
def deconnect_channel_db(channel):
    query="UPDATE channels SET deletion='"+time.strftime("%Y%m%dT%X")+"' WHERE id="+str(channel.db_id)
    execute_query(db_connection,query)

def execute_query(connection,query):
    if connection is None:
        return True
    
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query,",query,"executed successfully")
    except Error as e:
        print(f"The error '{e}' occurred for query",query)
        return False
    return True

#execute query and return the primary key of the last row
def execute_query_PK(connection,query):
    if connection is None:
        return True
    
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query,",query,"executed successfully")
    except Error as e:
        print(f"The error '{e}' occurred for query",query)
        return None
    return cursor.lastrowid

#database connection - create a new file each time and save the last one
db_filename = "chat_server_db.sqlite"
if os.path.isfile(db_filename):
    print("renaming old db file to",db_filename+time.strftime("%y%m%d_%X"))
    os.rename(db_filename,db_filename+time.strftime("%y%m%d_%X"))

#database creation
db_connection = None

try:
    db_connection = sqlite3.connect(db_filename)
    print("Connection to SQLite DB successful")
except Error as e:
    print(f"The error '{e}' occurred")
    print("no database will be used to log the session")

if not create_db(db_connection):
    db_connection.close()
    db_connection = None

#create the db tables: clients, channels, clients_channles, messages_to_channels, messages_to_clients

# create 2 sockets, one for commands from the clients (and the answer from the server)
serversocket_cmd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# the other one is for the messages form the server to the client (and the ACK from the client)
serversocket_msgs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# this socket is used to inject commandes into the server
controlsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# get local machine name
host = get_local_IP()
#ask for first port (command port, the messages port will be up by one
port = int(input("Base port?"))

# bind to the port
serversocket_cmd.bind((host, port))
print("server listening on ",host," at port ",port, "[command port]")
serversocket_msgs.bind((host, port+1))
print("server listening on ",host," at port ",port+1, "[messages port]")


# queue up to 5 requests
serversocket_cmd.listen(5)
serversocket_msgs.listen(5)

#connect control socket (used to inject commands from the server)
controlsock.connect((host,port))
print("controlsock:",controlsock)
controlsock_cmds=[]

#clients_read_list: should contain all clients sockets
#contains also the server sockets the clients use to connect to the server
clients_read_list=[serversocket_cmd,serversocket_msgs]

#dictionary of pairs:(socket,nicks)
clients = {}

#lists of messages socks not yet associated to a client (waiting to finish the connection procedure)
waiting_msgs_socks = []
#Transmit_queue list (channels)
channels = []

last_msg = {}
controlsock_connected = False
last_ID = 0 # always contains the ID of the last client, incremented by one for each new client

while True:
    ready_to_read = get_clients_ready()
    for sock in ready_to_read:
        #print('ready to read',sock)
        #if the serversocket_msgs is ready to be read that means someone
        #is trying to connect
        if sock == serversocket_cmd:
            #the client must first connect to the command socket
            new_client_first_step()
        elif sock == serversocket_msgs:
            #then it completes its connection by connecting to the messages socket
            second_step_new_client()
        else:
            #else someone is sending a message
            try:
                buf = sock.recv(200).decode('utf8')
                print("received=",buf," from ",sock.getpeername())
            except socket.error:
                #print("recv error")
                buf = ""
            if buf=="":
                #if the message is empty that means the client is deconnecting
                deconnect_client(sock)
            else:
                parse(sock,buf)
    #check if there are new commands ready on the controlsock commands list, if yes send the next one
    if controlsock_cmds:
        controlsock.send(controlsock_cmds.pop(0).encode('utf-8'))

#make sure we close the database
if db_connection is not None:
    db_connection.close()

