""" jmolsocket - G. Whitwell May 2020
    library to provide Jmol access via sockets
""" 

import sys
import json
import socket
from time import sleep
from string import Template
import subprocess as sp
from platform import system as osname
defport = 18008

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
    def __init__(self, port=defport, kiosk = False):
        self.kiosk = kiosk
        if osname() == 'Windows':
            jmol_path = 'c:\\compchem\\jmol14\\'
            java_path ='"C:\\Program Files (x86)\\Java\\jre1.8.0_341\\bin\\'
        elif osname() == 'Linux':
            jmol_path='//home//george//compchem//jmol14//'
            java_path='"//usr//bin//'
        java = java_path + 'java" -jar '
        jmol = jmol_path + 'Jmol.jar -o -j "sync -' + str(port) + '"'
        if kiosk:
            jmol = jmol_path + 'Jmol.jar -k -j "sync -' + str(port) + '"'
        jmol_cmd = java + jmol
        print(jmol_cmd)
        # The True block ignores stdout and stderr in deference to Win10
        # hanging after one command received.  The else block works in Ubuntu.
        if True:
            self.jmol = sp.Popen(jmol_cmd, shell=False,
                          stdin=sp.PIPE,
                          bufsize=0,
                          universal_newlines=True,
                          stdout=sp.DEVNULL,
                          stderr=sp.DEVNULL)
        else:
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
    def __init__(self, port=defport):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cnct = False
        self.port = port
        return

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
            print('sending', msg, len(msg), 'bytes')
            sent = self.sock.sendall(msg)
            # sleep(1)
            return sent
        except Exception as ex:
            print('send', ex)
        return

    def receive(self, finish="SCRIPT:Jmol script terminated"):
        """ receive and decode reply from Jmol
        """
        try:
            print('waiting to receive')
            rct = []
            while True:
                recvd = self.sock.recv(4096).decode('UTF-8')
                try:
                    recvd_ = [json.loads(x) for x in recvd.split('\n') if x]
                except json.decoder.JSONDecodeError:
                    recvd_ = 'Missing'
                rct.extend(recvd_)
                if finish in rct[-1]['reply']:
                        break
            print('socketeer received ', len(recvd), 'bytes\n', recvd)
            return rct
        except Exception as ex:
            print("receive", ex)
        return

    def close_Jmol(self):
        cmd = commnd.copy()
        cmd['command'] = "exitJmol"
        self.send(cmd)
        return

    def close_socket(self):
        self.sock.shutdown(2)
        self.sock.close()
        return
    
def main(cmds = [{"type" : "command", "command" : "command" }]):
    jmol = Jmol(kiosk=False)
    sender = socketeer()
    sender.connect('localhost', sender.port)
    for cmd in cmds:
        sent = sender.send(cmd)
        # sleep(3)
        rcvd = sender.receive()
    sleep(30)
    sender.close_Jmol()
    # print(rcvd)
    # jmol.out_put()
    return

def test():
    jmol = Jmol(kiosk=False)
    sender = socketeer()
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
    # sent = sender.send(msg_list)
    # rcvd = sender.receive()
    sleep(20)
    sender.close_Jmol()
    return 

if __name__ == '__main__':
    # jmol = Jmol(kiosk=False)
    msg_1 = commnd.copy()
    msg_1['command'] = "load $C1CCCC1"
    msg_2 = commnd.copy()
    msg_2['command'] = "spacefill"
    msg_3 = commnd.copy()
    msg_3['command'] = "rotate"
    msg_list = [msg_1, msg_2, msg_3]
    # main(msg_list)
    test()
