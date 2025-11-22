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
pending_damage_for_players = {} # pid -> [damage]
pending_mob_hits = [] # [(mob_id, damage)]
state_lock = threading.Lock()

def threaded_client(conn, addr):
    global host_addr, pending_damage_for_players, pending_mob_hits
    
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
                # We need to store these and send them to the Host
                if 'mob_hits' in data and data['mob_hits']:
                    pending_mob_hits.extend(data['mob_hits'])
                
                # Prepare reply
                reply = {
                    'players': players,
                    'mobs': mob_states,
                    'is_host': (addr == host_addr)
                }
                
                # If this is the Host, send them the pending hits and clear the list
                if addr == host_addr:
                    if pending_mob_hits:
                        reply['remote_hits'] = list(pending_mob_hits) # Copy
                        pending_mob_hits.clear() # Clear after sending
            
            # If Host, process player hits and store them for the target clients
            if addr == host_addr and 'player_hits' in data:
                for pid, dmg in data['player_hits']:
                    if pid not in pending_damage_for_players:
                        pending_damage_for_players[pid] = []
                    pending_damage_for_players[pid].append(dmg)
            
            # Check if there are pending hits for THIS client
            # We need to know the client's PID. It's in players[addr]['id']
            if addr in players:
                current_pid = players[addr].get('id')
                if current_pid and current_pid in pending_damage_for_players:
                    hits = pending_damage_for_players[current_pid]
                    if hits:
                        # Send as list of (pid, dmg) to match client expectation
                        reply['player_hits'] = [(current_pid, dmg) for dmg in hits]
                        # Clear delivered hits
                        del pending_damage_for_players[current_pid]
            
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
