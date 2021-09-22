#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      allaud_e
#
# Created:     08/01/2015
# Copyright:   (c) allaud_e 2015
# Licence:     <your licence>
#-------------------------------------------------------------------------------

from random import choice
import random, pygame, sys
from pygame.locals import *
import socket

#this client will connect automatically as a "user" with nick: chat-test
#it will connect to all channels when they get created
#and display all users in all channels (depending on screen space

#["#ch1","#ch2",...]     [["#ch1",GREEN],["#ch2",WHITE],...]

def print_lines(l,x,y):
    """
    l is a list of pairs (text, color) to be printed
    used to print channels, color tells if you have joined it or not
    """
    y = y-20*len(l)
    for lines,color in l:
        label = myfont.render(lines, 1, color)
        DISPLAYSURF.blit(label, (x, y))
        y+=20

def draw_button(x,y,w,h,text,color):
    pygame.draw.rect(DISPLAYSURF,color,(x,y,w,h),1)
    label=myfont.render(text,1,color)
    DISPLAYSURF.blit(label,(x+2,y+2))

def channel_joined(channel):
    for chan,color in channels:
        if chan==channel:
            return color == GREEN
    return False

def send_cmd(cmd,err_msg="Error when sending command"):
    cmds.send(cmd.encode('utf-8'))
    if not cmds.recv(200).decode('utf-8').startswith("/OK"):
        print(err_msg)
        return False
    return True

# create the commands socket object
cmds = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# create the messages socket object
msgs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

msgs.settimeout(0.01)
# get local machine name
host = "127.0.0.1"

port = 50002

# connection procedure
cmds.connect((host, port))
msg = cmds.recv(200).decode('utf-8')
if not msg.startswith("/ID"):
    cmds.close()
    print("Unexpected response from the server when waiting for ID")
    quit()
#now connect to msgs port
msgs.connect((host, port+1))
ID = int (msg[3:].lstrip())
msgs.send(("/connect "+str(ID)).encode('utf-8'))
msg = msgs.recv(200).decode('utf-8')
if not msg.startswith("/OK"):
    print("No ACK from the server for the 2nd stage of the connection")
    cmds.close()
    msgs.close()
    quit()

#connect as "chat-test"
send_cmd("/nick chat-test","Unable to set nick!")


FPS = 30 # frames per second, the general speed of the program
WINDOWWIDTH = 1000 # size of window's width in pixels
WINDOWHEIGHT = 700 # size of windows' height in pixels

#            R    G    B
GRAY     = (100, 100, 100)
NAVYBLUE = ( 60,  60, 100)
WHITE    = (255, 255, 255)
RED      = (255,   0,   0)
GREEN    = (  0, 255,   0)
BLUE     = (  0,   0, 255)
YELLOW   = (255, 255,   0)
ORANGE   = (255, 128,   0)
PURPLE   = (255,   0, 255)
CYAN     = (  0, 255, 255)

BGCOLOR = NAVYBLUE
LIGHTBGCOLOR = GRAY
BOXCOLOR = WHITE
HIGHLIGHTCOLOR = BLUE

pygame.init()
myfont = pygame.font.SysFont("monospace", 20)


FPSCLOCK = pygame.time.Clock()
DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))

pygame.display.set_caption("Your title")
FPSCLOCK.tick(FPS)

# text holds the text typed by the user
text=""
# rec is the list of the last 22 messages received
rec=[]
#channels is the list of all channels
#there are 2 info by channel: its name and the color to print it
channels=[]
#
joining=[]
#nicks is the list of connected nicks (+color)
nicks=[]
#controls if we have to ask for list (=2) or names (=1) or nothing (=0)
do_check=2
#my_nick contains the nick of the user
my_nick=""
have_nick=False
#None if no channel is clicked on
chan_clicked = None
while True:
    for event in pygame.event.get(): # event handling loop
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type==KEYDOWN:
            if event.key==K_BACKSPACE:
                text=text[:-1]
            elif event.key==K_RETURN:
                send_cmd(text,"Error when sending user command!")
                text=""
            else:
                text+=event.unicode
        elif event.type==pygame.MOUSEBUTTONDOWN:
            x,y=pygame.mouse.get_pos()
            if pygame.rect.Rect(600,550-len(channels)*20,400,len(channels)*20).collidepoint((x,y)):
                #print(x,y,len(channels)-(550-y)//20,"button",event.button)
                chan_clicked = len(channels)-1-(550-y)//20
                do_check = 1
                
        elif event.type==pygame.MOUSEBUTTONUP:
            do_check = 1
            chan_clicked = None

    if do_check==2:
        print("asking channels")
        if send_cmd("/list","Error asking for channels"):
            do_check-=1
    elif do_check==1:
        if chan_clicked is not None:
            send_cmd("/names "+channels[chan_clicked][0],"Error asking for names")
        else:
            send_cmd("/names","Error asking for names")
        do_check = 0
    try:
        m = msgs.recv(200).decode("utf-8")
    except:
        m=""
    if m!="":
        msgs.send("/OK".encode("utf-8"))
        m_list = m.split()
        print(m_list)
        if m_list[0]=="/deletedchannel":
            to_delete = None
            for c in channels:
                if c[0]==m_list[1]:
                    to_delete = c
            if to_delete is None:
                print("Error deleting channel")
            else:
                channels.remove(to_delete)
        elif m_list[0]=="/received":
            color = WHITE
            m=m_list[1]+":"+" ".join(m_list[2:])
        elif m_list[0]=="/list":
            for new_ch in m_list[1:]:
                existed= False
                for ch in channels:
                    if ch[0]==new_ch:
                        existed=True
                        break
                if not existed:
                    channels.append([new_ch,WHITE])
        elif m_list[0]=="/names":
            nicks=[]
            for names in m_list[1:]:
                nicks.append([names,WHITE])
        elif len(m_list)>1:
            color = GREEN
            if m_list[0]=="/new":
                c=WHITE
                if m_list[1].startswith("#"):
                    channels.append([m_list[1],c])
                    send_cmd("/join "+m_list[1],"Error joing channel "+m_list[1])
                    
                else:
                    nicks.append([m_list[1],WHITE])
            elif m_list[0]=="/joined" and m_list[2]==my_nick:
                for c in channels:
                    if c[0]==m_list[1]:
                        c[1]= GREEN
                        break
            elif m_list[0]=="/parted" and m_list[2]==my_nick:
                for c in channels:
                    if c[0]==m_list[1]:
                        c[1]= WHITE
                        break
                        
        if m_list[0]!="/list" and m_list[0]!="/names":
            rec.append([m,color])

        if len(rec)>22:
            rec.pop(0)

    DISPLAYSURF.fill(BGCOLOR)

    label = myfont.render(text, 1, GREEN)
    DISPLAYSURF.blit(label, (150, 650))

    print_lines(rec,200,550)
    print_lines(channels,600,550)
    print_lines(nicks,0,550)
    FPSCLOCK.tick(FPS)
    pygame.display.update()
