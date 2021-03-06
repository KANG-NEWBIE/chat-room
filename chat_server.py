import socket
import os
import sys
import threading
import select
import random
from getpass import getpass
from cryptography.fernet import Fernet
from tinydb import TinyDB, Query

ADMIN_PASSWORD = ""
HOST = socket.gethostbyname(socket.gethostname())
#HOST = socket.gethostbyname('testingg.pagekite.me')
PORT = 9999
MAX_CLIENTS = 99
BUFFER_SIZE = 4096
sockets_list = []
clients = {}
rooms = ["Public", "Public2"]
privroom=[("Private1","password"), ("Private2","noobie")]

if not os.path.isdir("log"):
    os.mkdir("log")

file = open('log/users.json', 'w')
file.close()
db = TinyDB('log/users.json')
db.purge()

key = Fernet.generate_key()
cipher_suite = Fernet(key)
file = open('log/key.key', 'wb')
file.write(key)
file.close()


class Logger(object):
    def __init__(self, filename="Default.log"):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass


sys.stdout = Logger("log/server.txt")


class User(object):
    def __init__(self, username):
        self.username = username
        self.password = ""
        self.rooms = []
        self.default_room = ""
        self.warn = 0


def run_server():
    while True:
        if clients:
            db.purge()
            for client in clients:
                query = Query()
                if not db.search(query.username == clients[client].username):
                    data = {
                        "username": clients[client].username,
                        "password": clients[client].password,
                        "rooms": clients[client].rooms,
                        "default_room": clients[client].default_room,
                    }
                    db.insert(data)
        read_sockets, write_sockets, exception_sockets = select.select(sockets_list, [], [])
        for notified_socket in read_sockets:
            if notified_socket == server_socket:
                client_socket, client_address = server_socket.accept()
                print(f"New incoming connection from {client_address[0]}")
#                sockets_list.append(client_socket)
                data = (client_socket.recv(BUFFER_SIZE)).decode()
                username = data.partition(" ")[0]
                if clients and (username in [str(clients[u].username) for u in sockets_list if u != server_socket]):
                    client_socket.send("[we changed your username because another user has logged in with the same username]".encode())
                    username = username + f"({random.randrange(99999)})"
                sockets_list.append(client_socket)
                confirm = data.partition(" ")[2]
                relogin_flag = False
                if confirm == "EXISTS":
                    success_message = "Successfully logged in!"
                    client_socket.send(success_message.encode())
                    relogin_flag = True
                else:
                    success_message = "Username set successfully!"
                    client_socket.send(success_message.encode())
                clients[client_socket] = User(username)
#                clients[client_socket].rooms.append("Public")
                if relogin_flag:
                    print(f"{clients[client_socket].username} logged back in")
                else:
                    print(f"{client_address[0]} set username to {clients[client_socket].username}")
                broadcast("\r[SERVER] " + str(clients[client_socket].username) +
                          " has joined the " + str(clients[client_socket].default_room) + " room.\n",
                          client_socket, server_socket, clients[client_socket].default_room)
                send_to_client("\rType /help to display the list of available commands.\n\n[SERVER] Welcome " + str(clients[client_socket].username) +
                               "! Kindly set a password using /p command, if not set.\n",
                               client_socket, server_socket)
                list_rooms(client_socket, server_socket)
                print(f"{clients[client_socket].username} joined {clients[client_socket].default_room} room")
            else:
                try:
                    stream = notified_socket.recv(BUFFER_SIZE).decode()
                    if stream:
                        if stream[0] == "/":
                            if stream.partition(" ")[2] != "":
                                command = stream.partition(" ")[0]
                            else:
                                command = stream.strip()
                            if command == "/u":
                                new_username = stream.partition("/u ")[2].strip()
                                change_username(new_username, notified_socket, server_socket)
                            elif command == "/p":
                                new_password = client_password(notified_socket, server_socket).strip()
                                if new_password:
                                    change_password(new_password, notified_socket, server_socket)
                                else:
                                    send_to_client("\rInvalid password\n", notified_socket, server_socket)
                            elif command == "/c":
                                if check_admin_password(notified_socket, server_socket):
                                    new_room = stream.partition("/c ")[2].strip()
                                    create_room(new_room, notified_socket, server_socket)
                                else:
                                    send_to_client("\rWrong Admin password!\n", notified_socket, server_socket)
                            elif command == "/j":
                                new_room = stream.partition("/j ")[2].strip()
                                join_room(new_room, notified_socket, server_socket)
                            elif command == "/l":
                                selected_room = stream.partition("/l ")[2].strip()
                                leave_room(selected_room, notified_socket, server_socket)
                            elif command == "/jp":
                                new_room=stream.split()[1].strip()
                                if new_room in [x[0] for x in privroom]:
                                    join_privroom(new_room, notified_socket, server_socket)
                                    break
                                else:
                                    send_to_client(f"\r[SERVER] Room '{new_room}' does not exist or maybe its not private room!\n", notified_socket, server_socket)
                                    break
                            elif command == "/cd":
                                selected_room = stream.partition("/cd ")[2].strip()
                                change_default_room(selected_room, notified_socket, server_socket)
                            elif command == "/cp":
                                if check_admin_password(notified_socket, server_socket):
                                     new_priv_room = stream.split()[1]
                                     paswd_room = stream.split()[2]
                                     create_priv_room((new_priv_room,paswd_room),notified_socket,server_socket)
                                else:
                                    send_to_client("/rWrong Admin password!",notified_socket, server_socket)
                            elif command == "/list":
#                                if check_admin_password(notified_socket, server_socket):
                                list_rooms(notified_socket, server_socket)
#                                else:
#                                    send_to_client("Wrong Admin password!", notified_socket, server_socket)
#                                    print(f"Failed admin attempt: {clients[notified_socket].username}")
                            elif command == "/users":
#                                if check_admin_password(notified_socket, server_socket):
                                list_users(notified_socket, server_socket)
#                                else:
#                                    send_to_client("Wrong Admin password!", notified_socket, server_socket)
#                                    print(f"Failed admin attempt: {clients[notified_socket].username}")
                            elif command == "/public":
                                sub_string = stream.partition("<")[2]
                                destination_room = sub_string.partition(">")[0]
                                message = sub_string.partition("> ")[2].strip()
                                send_different_room(destination_room, message, notified_socket, server_socket)
                            elif command == "/private":
#                                sub_string = stream.partition("<")[2]
#                                destination_username = sub_string.partition(">")[0]
#                                message = sub_string.partition("> ")[2].strip()
                                destination_username = stream.split()[1].replace('@','')
                                message = stream.split()[2:]
                                send_private_message(destination_username, ' '.join(message), notified_socket, server_socket)
                            elif command == "/logout":
                                broadcast("\r[SERVER] " + clients[notified_socket].username + " has left the server!\n",
                                          notified_socket, server_socket, clients[notified_socket].default_room)
                                remove_socket(notified_socket)
                                print(f"{clients[notified_socket].username} has disconnected")
#                            else:
#                                send_to_client("\r[SERVER] Invalid command!\n", client_socket, server_socket)
                        else:
                            if clients[notified_socket].default_room in clients[notified_socket].rooms:
                                broadcast(str(clients[notified_socket].username) + " : " + stream,
                                          notified_socket, server_socket, clients[notified_socket].default_room)
                                print(f"{clients[client_socket].username} sent a message in "
                                      f"{clients[notified_socket].default_room}, broadcasting now")
                            else:
                                send_to_client("\r[SERVER] Please join or set the default room!\n",
                                               notified_socket, server_socket)
                    else:
                        broadcast("\r[SERVER] " + clients[notified_socket].username + " has left the server!\n",
                                  notified_socket, server_socket, clients[notified_socket].default_room)
                        remove_socket(notified_socket)
                        print(f"{clients[notified_socket].username} has disconnected")
                except ConnectionResetError:
                    print(f"Connection reset by {clients[client].username}")
                    continue


def check_admin_password(client_socket, server_socket):
    for client in sockets_list[1:]:
        if client == client_socket and client != server_socket:
            client_socket.send("GETADMINPASS".encode())
            rcv_pass = client_socket.recv(BUFFER_SIZE).decode()
            if rcv_pass == cipher_suite.decrypt(ADMIN_PASSWORD).decode():
                return True
            else:
                return False


def client_password(client_socket, server_socket):
    for client in sockets_list[1:]:
        if client == client_socket and client != server_socket:
            client_socket.send("GETUSERPASS".encode())
            rcv_pass = client_socket.recv(BUFFER_SIZE).decode()
            if rcv_pass:
                return rcv_pass
            else:
                return False

def join_privroom(room, client_socket, server_socket):
    for client in sockets_list[1:]:
        if client == client_socket and client != server_socket:
            client_socket.send("GETPRIVROOM".encode())
            rcv_pass = client_socket.recv(BUFFER_SIZE).decode()
            for rom in privroom:
                if room == rom[0]:
                    if rcv_pass == rom[1]:
                        join_private_room(room, client_socket, server_socket)
                        break
                    else:
                        client_socket.send("Wrong room password!\n".encode())


def check_username(username, server_socket):
    for user in sockets_list:
        if user != server_socket:
            if clients[user].username == username:
                return False
    return True


def change_username(username, client_socket, server_socket):
    if username:
        if check_username(username, server_socket):
            print(f"{clients[client_socket].username} changed username to {username}")
            send_to_client("\r[SERVER] Username changed to " + username + "\n",
                           client_socket, server_socket)
            broadcast(clients[client_socket].username + " changed username to " + username + "!\n",
                      client_socket, server_socket, "Public")
            clients[client_socket].username = username
        else:
            send_to_client("\r[SERVER] Username " + username + " is already taken." + "\n",
                           client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Correct usage: /u [username]\n", client_socket, server_socket)


def change_password(new_pass, client_socket, server_socket):
    clients[client_socket].password = cipher_suite.encrypt(new_pass.encode()).decode()
    send_to_client("\r[SERVER] Password changed!\n", client_socket, server_socket)


def create_room(room, client_socket, server_socket):
    if room:
        if room not in rooms:
            send_to_client("\r[SERVER] New room created: " + room + "\n", client_socket, server_socket)
            rooms.append(room)
            print(f"{clients[client_socket].username} created a new room: {room} using Admin cerdential")
        else:
            send_to_client("\r[SERVER] " + room + " room already exists!\n", client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Correct usage: /c [room_name]\n", client_socket, server_socket)

def create_priv_room(room, client_socket, server_socket):
    if room and len(room) == 2:
        if room[0] not in [x[0] for x in privroom]:
            privroom.append(room)
            send_to_client(f"\r[SERVER] New private room created: {room[0]}\n", client_socket, server_socket)
            print(f"{clients[client_socket].username} created a private room: {room} using admin credential")
        else:
            send_to_client(f"\r[SERVER] private room: {room[0]} already exists\n", client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Wrong usage type /help for more information\n", client_socket, server_socket)

def join_room(room, client_socket, server_socket):
    if room:
        if room in rooms:
            if room in clients[client_socket].rooms:
                send_to_client("\r[SERVER] You are already in the room!\n", client_socket, server_socket)
            else:
                clients[client_socket].rooms.append(room)
                send_to_client("\r[SERVER] You have been added to " + room + "!\n", client_socket, server_socket)
                broadcast("\r[SERVER] " + str(clients[client_socket].username) + " has joined the " +
                          str(room) + " room\n", client_socket, server_socket, room)
                change_default_room(room, client_socket, server_socket)
                print(f"{clients[client_socket].username} joined {room} room")
        else:
            send_to_client(f"\r[SERVER] Room '{room}' does not exist or maybe its private room!\n", client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Usage: /j [room_name]", client_socket, server_socket)

def join_private_room(room, client_socket, server_socket):
        if room:
            if room in clients[client_socket].rooms:
               send_to_client("\r[SERVER] You have already in the room!", client_socket, server_socket)
            else:
               for r in privroom:
                   if r[0] == room:
                       clients[client_socket].rooms.append(room)
                       send_to_client(f"\r[SERVER] You have been added to {room}!\n", client_socket, server_socket)
                       broadcast(f"\r[SERVER] {clients[client_socket].username} has joined the {room} room\n", client_socket, server_socket, room)
                       change_default_room(room, client_socket, server_socket)
                       print(f"{clients[client_socket].username} joined {room} room")
                       break
        else:
            send_to_client("\r[SERVER] Usage: /jp [room_name]\n", client_socket, server_socket)


def leave_room(room, client_socket, server_socket):
    if room:
        if room in clients[client_socket].rooms:
            broadcast("\r[SERVER] " + str(clients[client_socket].username) + " has left the room!\n",
                      client_socket, server_socket, room)
            send_to_client("\r[SERVER] You have left the " + room + " room!\n", client_socket, server_socket)
            clients[client_socket].rooms.remove(room)
            print(f"{clients[client_socket].username} left {room} room")
        else:
            send_to_client("\r[SERVER] You cannot leave a room you are not a part of!\n",
                           client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Correct usage: /l [room_name]\n", client_socket, server_socket)


def list_rooms(client_socket, server_socket):
    room_list = ""
    for room in rooms:
        room_list += str(room) + "\n"
    for room in privroom:
        room_list += f"{room[0]} (private) \n"
    send_to_client("\r[SERVER] List of rooms on server:\n" + room_list, client_socket, server_socket)
    print(f"{clients[client_socket].username} listed rooms")


def list_users(client_socket, server_socket):
    users = ""
    for u in sockets_list:
        if u != server_socket:
            users += str(clients[u].username) + "\n"
    send_to_client("\r[SERVER] Online Users:\n" + users,
                   client_socket, server_socket)
    print(f"{clients[client_socket].username} listed users")


def change_default_room(room, client_socket, server_socket):
    if room:
        if room in clients[client_socket].rooms:
            send_to_client("\r[SERVER] Default room changed from " + clients[client_socket].default_room +
                           " to " + room + "\n", client_socket, server_socket)
            clients[client_socket].default_room = room
            print(f"{clients[client_socket].username} changed default room to {room}")
        else:
            send_to_client("\r[SERVER] Cannot change default room to a room you are not part of "
                           "or if it does not exist!\n", client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Correct usage: /public <[room]> [message]\n", client_socket, server_socket)


def send_different_room(room, message, client_socket, server_socket):
    if room and message:
        if room in clients[client_socket].rooms:
            if room in [x[0] for x in privroom]:
                send_to_client("\r[SERVER] You cannot send across messages to a private room\n", client_socket, server_socket)
                return False
            broadcast(str(clients[client_socket].username) + ": " + message + "\n",
                      client_socket, server_socket, room)
            print(f"Public message sent from {clients[client_socket].username} to {room} room")
        else:
            send_to_client("\r[SERVER] Cannot send message to room you are not part of!\n",
                           client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Correct usage: /public <[room]> [message]", client_socket, server_socket)


def send_private_message(username, message, client_socket, server_socket):
    if username and message:
        for client in sockets_list:
            if len(sockets_list) > 2:
                if client != client_socket and client != server_socket:
                    if clients[client].username.strip() == username.strip():
                        message_string = str("\r[E2E][Private message by " + clients[client_socket].username + \
                                             "] : " + message).encode()
                        encrypted_message = cipher_suite.encrypt(message_string)
                        client.send(encrypted_message)
                        send_to_client("\r[SERVER] Private message sent!\n", client_socket,
                                       server_socket)
                        print(f"Private message sent from {clients[client_socket].username} to {username}")
                    elif clients[client_socket].username == username:
                        send_to_client("\r[SERVER] Private message cannot be sent to self!\n",
                                       client_socket, server_socket)
            else:
                send_to_client("\r[SERVER] Server needs to have more than 1 user!\n", client_socket, server_socket)
    else:
        send_to_client("\r[SERVER] Correct usage: /private <[username]> [message]\n", client_socket, server_socket)


def broadcast(message, client_socket, server_socket, room):
    for client in clients:
        if room in clients[client].rooms:
#            client.send(clients[client].rooms.encode())
            file_name = str("log/" + clients[client].username + ".txt")
            with open(file_name, 'a+') as f:
                f.write(message)
                f.close()
    for client in sockets_list[1:]:
        if client != client_socket and client != server_socket and room in clients[client].rooms:
            try:
                client.send(message.encode())
            except:
                remove_socket(client)


def send_to_client(message, client_socket, server_socket):
    file_name = str("log/" + clients[client_socket].username + ".txt")
    with open(file_name, 'a+') as f:
        f.write(message)
        f.close()
    for client in sockets_list[1:]:
        if client == client_socket and client != server_socket:
            try:
                client_socket.send(message.encode())
            except:
                remove_socket(client)


def remove_socket(client_socket):
    if client_socket in sockets_list:
        sockets_list.remove(client_socket)
        client_socket.close()


if __name__ == "__main__":
    try:
        print(end="\rRunning server script..\nSpecify port number for the server (default = 9999): ")
        try:
            PORT = int(input(""))
        except ValueError:
            print("\nStarting server on default port 9999!")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(MAX_CLIENTS)
        sockets_list.append(server_socket)
        print(f"Server started on {HOST} : {PORT}")
        tmp_admin_password = getpass("Admin Password: ")
        ADMIN_PASSWORD = cipher_suite.encrypt(tmp_admin_password.encode())
        tmp_admin_password = ""
        print("Password set and encrypted successfully!")
        print("Waiting for incoming connections..\n")
        threading.Thread(target=run_server())
    except KeyboardInterrupt:
        server_socket.close()
        print("\nServer stopped!")
