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

#["#ch1","#ch2",...]     [["#ch1",GREEN],["#ch2",WHITE],...]

def print_lines(msgs_list,x,y):
    """
    msgs_list is a list of pairs (text, color) to be printed
    used to print channels, color tells if you have joined it or not
    """
    y = y-20*len(msgs_list)
    for line,color in msgs_list:
        label = myfont.render(line, 1, color)
        DISPLAYSURF.blit(label, (x, y))
        y+=20

def draw_button(x,y,w,h,text,color):
    """
    Draw a button
    """
    pygame.draw.rect(DISPLAYSURF,color,(x,y,w,h),1)
    label=myfont.render(text,1,color)
    DISPLAYSURF.blit(label,(x+2,y+2))

def channel_joined(channel):
    """
    Check the user has joined channel (by checking the associated color
    """
    for chan,color in channels:
        if chan==channel:
            return color == GREEN
    return False

# create the commands socket object
cmds = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# create the messages socket object
msgs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

msgs.settimeout(0.01)
# get local machine name
host = "192.168.0.22"

port = 50000

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

#nicks is the list of connected nicks (+color)
nicks=[]

#my_nick contains the nick of the user
my_nick=""

#None if no channel is clicked on
chan_clicked = None

#Init the channels list
cmds.send("/list".encode('utf-8'))
msg = cmds.recv(200).decode('utf-8')


#Init the channels list
cmds.send("/names".encode('utf-8'))
msg = cmds.recv(200).decode('utf-8')

check_names = True

while True:
    for event in pygame.event.get(): # event handling loop
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        if event.type==KEYDOWN:
            #process keys
            if event.key==K_BACKSPACE:
                text=text[:-1]
            elif event.key==K_RETURN:
                cmds.send(text.encode("utf-8"))
                print("seding:",text)
                if not cmds.recv(200).decode('utf-8').startswith("/OK"):
                    print("Error when sending command ",text)
                #text=""
            else:
                text+=event.unicode
        elif event.type==pygame.MOUSEBUTTONDOWN:
            #process mouse clicks
            x,y=pygame.mouse.get_pos()
            if pygame.rect.Rect(0,670,60,25).collidepoint((x,y)):
                #click on join button
                cmds.send(("/join "+text).encode('utf-8'))
                if not cmds.recv(200).decode('utf-8').startswith("/OK"):
                    print("Error when joining channel",text)
                text=""
            elif pygame.rect.Rect(0,650,60,25).collidepoint((x,y)):
                #click on NICK button
                cmds.send(("/nick "+text).encode('utf-8'))
                if not cmds.recv(200).decode('utf-8').startswith("/OK"):
                    print("Error when setting/changing nickname to",text)
                else:
                    my_nick = text
                text=""
            elif pygame.rect.Rect(600,550-len(channels)*20,400,len(channels)*20).collidepoint((x,y)):
                #Click on the channel list
                chan_clicked = len(channels)-1-(550-y)//20
                modifiers = pygame.key.get_mods()  #check key modifiers state
                if event.button == 1 and modifiers & pygame.KMOD_CTRL==0:
                    #click without pressing CTRL => send msg
                    cmds.send(("/msg "+channels[chan_clicked][0]+" "+text).encode("utf-8"))
                    if not cmds.recv(200).decode('utf-8').startswith("/OK"):
                        print("Error when sending msg to channel",text)
                if event.button == 1 and modifiers & pygame.KMOD_CTRL:
                    #click while pressing CTRL => join/part channel
                    #check color of channel, if WHITE we are not in so join it
                    if channels[chan_clicked][1]==WHITE:
                        cmds.send(("/join "+channels[chan_clicked][0]).encode("utf-8"))
                        if not cmds.recv(200).decode('utf-8').startswith("/OK"):
                            print("Error when joining channel",text)
                    else:
                        #otherwise part from it
                        cmds.send(("/part "+channels[chan_clicked][0]).encode("utf-8"))
                        if not cmds.recv(200).decode('utf-8').startswith("/OK"):
                            print("Error when parting from channel",text)
                elif event.button==3:
                    #right click on channels => Show users in this channel
                    check_names = True

        elif event.type==pygame.MOUSEBUTTONUP and event.button==3:
            #Unpress of right click => show the list of all users
            check_names = True
            chan_clicked = None

    if check_names:
        #reload names of users
        print("asking names")
        if chan_clicked is not None:
            #get only users from the channel that was cliked on
            cmds.send(("/names "+channels[chan_clicked][0]).encode("utf-8"))
        else:
            #all users
            cmds.send("/names".encode("utf-8"))
            
        if not cmds.recv(200).decode('utf-8').startswith("/OK"):
            print("Error asking for names")
        else:
            check_names = False
    #check if new messages arrived from the server
    try:
        m = msgs.recv(200).decode("utf-8")
    except:
        m=""
    if m!="":
        #send ACK
        msgs.send("/OK".encode("utf-8"))
        #split for better handling
        m_list = m.split()
        print(m_list)
        if m_list[0]=="/deletedchannel":
            to_delete = None
            for c in channels:
                if c[0]==m_list[1]:
                    to_delete = c
                    break
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
                if m_list[1].startswith("#"):
                    channels.append([m_list[1],WHITE])
                else:
                    nicks.append([m_list[1],WHITE])
                    print("adding nick",m_list[1],"mynick=",my_nick)
                    if my_nick == m_list[1]:
                        #we have a nick so we should ask for nicks and channels
                        have_nick = True
            elif m_list[0]=="/disconnected":
                print("deleting nick",m_list[1])
                for i in range(len(nicks)):
                    if nicks[i][0]==m_list[1]:
                        nicks.pop(i)
                        break
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
    draw_button(10, 670,60,25,"JOIN",RED)
    draw_button(10, 650,60,25,"NICK",RED)

    print_lines(rec,200,550)
    print_lines(channels,600,550)
    print_lines(nicks,0,550)
    FPSCLOCK.tick(FPS)
    pygame.display.update()
pygame.quit()
