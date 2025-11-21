import socket
from _thread import *
import threading
import pickle

server = "0.0.0.0"
port = 5555

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    s.bind((server, port))
except socket.error as e:
    str(e)

s.listen(2)
print("Waiting for a connection, Server Started")

# State
players = {}
mob_states = {} # id -> {x, y, action, hp, max_hp, ...}
host_addr = None
state_lock = threading.Lock()

def threaded_client(conn, addr):
    global host_addr
    
    with state_lock:
        # First connection becomes host
        if host_addr is None:
            host_addr = addr
            print(f"Host assigned to {addr}")
        
        # Send initial state including if they are host
        initial_data = {
            'players': players,
            'is_host': (addr == host_addr),
            'mobs': mob_states
        }
    conn.send(pickle.dumps(initial_data))
    
    while True:
        try:
            data = pickle.loads(conn.recv(2048*8)) # Increased buffer for larger data
            
            if not data:
                print("Disconnected")
                break
            
            with state_lock:
                # Update player state
                if 'player_data' in data:
                    players[addr] = data['player_data']
                    
                # Handle Mob Updates (Only from Host)
                if addr == host_addr and 'mob_updates' in data:
                    for mid, mdata in data['mob_updates'].items():
                        mob_states[mid] = mdata
                        
                # Handle Mob Hits (From Clients)
                if 'mob_hits' in data:
                    pass 
                
                # Prepare reply
                reply = {
                    'players': players,
                    'mobs': mob_states,
                    'is_host': (addr == host_addr)
                }
            
            conn.sendall(pickle.dumps(reply))
        except Exception as e:
            print(f"Error: {e}")
            break

    print("Lost connection")
    with state_lock:
        if addr in players:
            del players[addr]
            
        if addr == host_addr:
            print("Host disconnected, resetting host")
            host_addr = None
            # Ideally pick a new host, but for now just reset
            # If there are other players, one should become host.
            if players:
                host_addr = list(players.keys())[0]
                print(f"New host assigned: {host_addr}")
            
    conn.close()

while True:
    conn, addr = s.accept()
    print("Connected to:", addr)

    start_new_thread(threaded_client, (conn, addr))
