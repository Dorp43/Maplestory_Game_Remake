import socket
from _thread import *
import pickle

server = "0.0.0.0"  # Listen on all available interfaces
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.bind((server, port))
except socket.error as e:
    str(e)

s.listen(2)
print("Waiting for a connection, Server Started")

players = {}

def threaded_client(conn, addr):
    conn.send(pickle.dumps(players))
    
    while True:
        try:
            data = pickle.loads(conn.recv(2048*4))
            players[addr] = data

            if not data:
                print("Disconnected")
                break
            else:
                reply = players
                # print("Received: ", data)
                # print("Sending : ", reply)

            conn.sendall(pickle.dumps(reply))
        except:
            break

    print("Lost connection")
    del players[addr]
    conn.close()

while True:
    conn, addr = s.accept()
    print("Connected to:", addr)

    start_new_thread(threaded_client, (conn, addr))
