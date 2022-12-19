""" jmolsocket - G. Whitwell May 2020
    library to provide Jmol access via sockets
""" 

import sys
import json
import socket
from time import sleep, time
from string import Template
import subprocess as sp
from platform import system as osname
sndport =  8008
rcvport = 18008
OS = osname()

# stock json objects for Jmol socket communication
# see https://chemapps.stolaf.edu/jmol/docs/misc/appsync.txt
magic  = {"magic" : "JmolApp", "role" : "out"}
commnd = {"type" : "command", "command" : "command" }
banner = {"type" : "banner", "mode" : "ON" or "OFF" }
rotate = {"type" : "move", "style" : "rotate", "x" : 30, "y" : 30 }
trnslt = {"type" : "move", "style" : "translate", "x" : 1, "y" : 1 }
zoom   = {"type" : "move", "style" : "zoom", "scale" : 1.0 }

class Jmol():
    """ run Jmol in subprocess
        uses java_path and jmol_path for FQN, kiosk for kiosk option
        capture output and err work in Linux - Windows hangs after first
        send/receive until connection broken, thus stdin,stderr go to DEVNULL
    """
    def __init__(self, port=sndport, kiosk=False):
        self.kiosk = kiosk
        if OS == 'Windows':
            jmol_path = 'c:\\compchem\\jmol14\\'
            java_path ='"C:\\Program Files (x86)\\Java\\jre1.8.0_341\\bin\\'
        elif OS == 'Linux':
            jmol_path='//home//george//compchem//jmol14//'
            java_path='"//usr//bin//'
        java = java_path + 'java" -jar '
        # jmol = jmol_path + 'Jmol.jar -o -j "sync ' + str(port) + '"'
        jmol = jmol_path + 'Jmol.jar -o -j "sync -' + str(port) + '"'
        if kiosk:
            jmol = jmol_path + 'Jmol.jar -k -j "sync -' + str(port) + '"'
        jmol_cmd = java + jmol
        print(jmol_cmd)
        # The 'Windows' block ignores stdout and stderr in deference to Win10
        # hanging after one command received.  The Linux block works in Ubuntu.
        if OS == 'Windows':
            self.jmol = sp.Popen(jmol_cmd, shell=False,
                          stdin=sp.PIPE,
                          bufsize=0,
                          universal_newlines=True,
                          stdout=sp.DEVNULL,
                          stderr=sp.DEVNULL)
        elif OS == 'Linux':
            self.jmol = sp.Popen(jmol_cmd, shell=False,
                          stdin=sp.PIPE,
                          bufsize=0,
                          universal_newlines=True,
                          stdout=sp.PIPE,
                          stderr=sp.PIPE)
        sleep(2)
        print('init Jmol at', port)
        return
        
    def out_put(self):
        """ called to print output, if available
        """
        std_out, std_err = self.jmol.communicate()
        print('\nSTDOUT\n\n', std_out)
        print('STDERR\n', std_err)
        return

class socketeer:
    """ simple socket communication class for Jmol
    """
    def __init__(self, port=sndport):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cnct = False
        self.port = port
        self.ECHO = []
        return

    def accept(self, host, port):
        print('connecting to', host, 'from', port)
        self.sock.settimeout(10)
        self.sock.bind((host, port))
        self.sock.listen()
        fd, self.port = self.sock.accept()
        print(fd, self.port)
        return fd

    def connect(self, host, port):
        print('connecting to', host, 'on', port)
        self.sock.settimeout(4)
        self.sock.connect((host, port))
        # handshake
        self.sock.send('{"magic":"JmolApp","role":"out"}\n'.encode('utf-8'))
        try:
            self.receive("OK")
            self.cnct = True
        except:
            self.cnct = False
        print('connection', self.cnct)
        return

    def build(self, json_dict):
        """ take a Jmol command sequence as dict of key/value pairs
            and convert to json object as bytes for send
        """
        msg = '{'
        for key, val in json_dict.items():
            if (0 != val * 0):  # keep numerics as type
                tmp = Template('"$key":"$value",')
            else:
                tmp = Template('"$key":$value,')               
            msg += tmp.substitute(key=key, value=val)
        msg = msg[:-1] + '}\n'
        return msg.encode('utf-8')
  
    def send(self, cmd_list):
        """ encode and send message to Jmol
        """
        try:
            msg = self.build(cmd_list)
            print('\nsending', msg, len(msg), 'bytes')
            self.sock.sendall(msg)
            return msg
        except Exception as ex:
            print('send fail', ex)
        return

    def receive(self, finish="SCRIPT:Jmol script terminated"):
        """ receive and decode reply from Jmol
        """
        try:
            rct = []
            rcbytes = 0
            while True:
                recvd = self.sock.recv(4096).decode('UTF-8')
                rcbytes += len(recvd)
                try:
                    recvd_ = [json.loads(x) for x in recvd.split('\n') if x]
                except json.decoder.JSONDecodeError:
                    recvd_ = 'Missing'
                rct.extend(recvd_)
                if finish in rct[-1]['reply']:
                    for r in rct:
                        if r['reply'][:4] == 'ECHO':
                            echo = r['reply'][5:]
                            print('ECHO\n', echo)
                            self.ECHO.append(echo)
                    break

            print('socketeer received', len(rct), 'messages: total', rcbytes, 'bytes\n') #, rct)            
            return rct
            
        except Exception as ex:
            print("receive fail", ex)
        return "No reply"

    def close_Jmol(self):
        cmd = commnd.copy()
        cmd['command'] = "exitJmol"
        # print('\nsending', cmd, len(cmd), 'bytes')
        self.send(cmd)
        return

    def close_socket(self):
        self.sock.shutdown(2)
        self.sock.close()
        return

class sndrcv:
    """ python socket 2-way communication
        run in separate shells with t and f args
        
    """
    def __init__(self, role):
        """ role is boolean: server (T) or client (F)
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = "localhost"
        self.port = 18008
        self.sock.settimeout(1)
        self.end = time() + 2
        if role==True:
            print('I am server at ', self.port)
            self.server()
        else:
            print('I am client at ', self.port)
            self.client()

        return

    def server(self):
        """ start server first, then start client within 1 s
        """
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        clnt, addr = self.sock.accept()  
        print('Got connection from', addr)
        while True:
            if time() > self.end:
                break
            r = ''
            try:
                r = clnt.recv(1024).decode()
            except:
                pass
            if len(r) > 0:
                print(r)
            message = b">>"
            clnt.sendall(message)
        clnt.close()
        
        return

    def client(self):
        self.sock.connect((self.host, self.port))
        while True:
            if time() > self.end:
                break
            try:
                print(self.sock.recv(1024).decode())
            except:
                pass
            message = b"<<"
            self.sock.send(message)

        return

def main():
    """ start Jmol, build a message list and send
        wait, then close Jmol
    """
    jmol = Jmol(kiosk=False)
    sender = socketeer(sndport)
    sender.connect('localhost', sender.port)
    msg_1 = commnd.copy()
    msg_1['command'] = "load $C1COCCC1"
    msg_2 = commnd.copy()
    msg_2['command'] = "spacefill"
    msg_3 = commnd.copy()
    msg_3['command'] = "rotate"
    msg_list = [msg_1, msg_2, msg_3]
    for cmd in msg_list:
        sent = sender.send(cmd)
        rcvd = sender.receive()
    sleep(20)
    sender.close_Jmol()
    return

def demo():
    """ 2-way communication with Jmol using ECHO hack
        note: sync command (4th in round 1) is not received by socketeer
    """
    jmol = Jmol(kiosk=False)
    sender = socketeer(sndport)
    sender.connect('localhost', sender.port)
    rcv = []
    msg = commnd.copy()
    # round 1: load SMILES, get coords, send back to socketeer
    for m in ["load $C1COCCC1","x =  write('COORDS')","print x","sync " + str(sender.port) + " x","delete *"]:
        msg['command'] = m
        sent = sender.send(msg)
        rcvd = sender.receive()
        rcv.append([sent, rcvd])
        try:
            for r in rcvd:
                if r['reply'][:4] == 'ECHO':
                    xyz = "".join(r['reply'][5:]).replace("\n",",")
        except Exception as ex:
            print("Except: ", ex)
    # round 2: send struct back to Jmol and load
    for m in ["x = '" + xyz + "'","y = x.replace(',','\\n')","load '@y'"]:
        msg['command'] = m
        sent = sender.send(msg)
        rcvd = sender.receive()
        rcv.append([sent, rcvd])

    sender.close_Jmol() 

    return 

if __name__ == '__main__':
    # main()
    demo()

    # sndrcv(sys.argv[1][0].upper()=='T')
