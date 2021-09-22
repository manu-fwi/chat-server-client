# client.py
import socket,time

#function to "guess" the IP of the computer
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

def new_connection(host,port):
    #This function creates a pair of sockets connected to the chat server
    # create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # connection to hostname on the port.
    s.connect((host, port))
    m = s.recv(200).decode('utf-8')
    print("received:",m)
    #get ID
    ID = int(m[len("/ID "):])
    #connect to second port and send command to finish the connection
    s2.connect((host,port+1))
    s2.send(("/connect "+str(ID)).encode('utf-8'))
    print(s2.recv(200).decode('utf-8'))
    
    #now set the s2 socket (the one receiving asynchronous messages from the server)
    #to a small timeout so it does not block waiting for a message from the server
    s2.settimeout(0.1)

    #return the pair of sockets
    return (s,s2)
    

# get local machine name
host = get_local_IP()
port = int(input("port?"))

#socks is the list of pair of sockets that handle the connections to the server
socks=[]
for i in range(5):
    socks.append(new_connection(host,port))

#Fake users connections
counter = 1
for s1,s2 in socks:
    s1.send(("/nick test"+str(counter)).encode("utf-8"))
    s1.recv(200)
    s1.send(("/join #testchannel"+str(counter)).encode('utf-8'))
    s1.recv(200)
    counter+=1

last_time=time.time()
counter = 1
try:
    while True:
        for s1,s2 in socks:
            try:
                msg = s2.recv(200).decode('utf-8')
                print()
                print("Received: ",msg)
                s2.send("/OK".encode("utf-8"))
            except socket.timeout:
                pass
        #send messages every 5 seconds
        if last_time<time.time()-5:
            ch_counter=1
            for s1,s2 in socks:
                s1.send(("/msg #testchannel"+str(ch_counter)+" message "+str(counter)).encode("utf-8"))
                s1.recv(200)
                ch_counter+=1
            counter+=1
            last_time=time.time()
            print(time.time())
except KeyboardInterrupt:
    print("Client stopped")
    for s1,s2 in socks:
        s1.close()
        s2.close()

