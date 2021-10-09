# client.py
import socket

# create a socket object
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s2.settimeout(0.1)


# get local machine name
host = "192.168.8.200"
port = int(input("port?"))

# connection to hostname on the port.
s.connect((host, port))
m = s.recv(200).decode('utf-8')
print("received:",m)
ID = int(m[len("/ID "):])
s2.connect((host,port+1))
s2.send(("/connect "+str(ID)).encode('utf-8'))
print(s2.recv(200).decode('utf-8'))
while True:
    msg = input("?")
    if msg == "STOP":
        break
    elif msg!="":
        s.send(msg.encode('utf-8'))
        print("command socket:",s.recv(200).decode('utf-8'))
    try:
        m = s2.recv(200).decode('utf-8')
    except:
        m=""
    print("messages socket:",m)
    if m!="":
        s2.send("/OK".encode('utf-8'))
s.close()
