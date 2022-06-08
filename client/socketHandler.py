import os.path
import socket
import sys
import threading
import logging
import pickle
import time
import math
from tkinter import END

from message.message import Message, MessageType

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SocketHandler:
    HEADER_LENGTH = 1024

    def __init__(self, port: int, address: str, output):
        self.port = int(port)
        self.address = address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.isConnectionActive = False
        self.output = output

        self.connectionThread = threading.Thread(target=self.connect)
        self.connectionThread.start()
        self.receiveThread = threading.Thread(target=self.receive)
        self.receiveThread.start()

    def connect(self):
        while True:
            if not self.isConnectionActive:
                log.info('Connecting to socket')
                try:
                    self.socket.connect((self.address, self.port))
                except:
                    log.info('Not connected to socket')
                    continue
                log.info('Connected to socket')
                self.isConnectionActive = True
            time.sleep(5)

    def receive(self):
        while True:
            if self.isConnectionActive:
                try:
                    self.handleMessage(self.getNextMessage())
                except Exception as e:
                    log.info(f'Error receiving message {e}')

    def getNextMessage(self):
        log.info('Received message')
        msg = self.socket.recv(1024)
        msgLength = int(msg.decode('utf-8'))
        msg = self.socket.recv(msgLength)
        return pickle.loads(msg)

    def handleMessage(self, message):
        if message.type == MessageType.TEXT:
            log.info(f"Received text")
            self.output.insert(END, f"\n [{message.sender[0]}:{message.sender[1]}] {message.content}")
        if message.type == MessageType.FILE:
            log.info(f"Received file")
            self.saveToFile(message)

    def saveToFile(self, message):
        messages = [message.content]
        while len(messages) != message.parts:
            msg = self.getNextMessage()
            log.info(f"Received {1 + msg.part} of {msg.parts}")
            messages.append(msg.content)
        with open(f'downloaded{message.fileExtension}', "w+b") as file:
            file.write(b''.join(messages))
        log.info(f"Wrote {len(messages)} parts")

    def sendTextMessage(self, content):
        log.info('TypedEnter')
        if self.isConnectionActive:
            log.info('Sending text message')
            try:
                msg = Message(self.socket.getsockname(), MessageType.TEXT, content)
                self.sendMessage(msg)
            except ConnectionResetError as e:
                self.isConnectionActive = False

    def sendFile(self, filename):
        max = 1024 * 50
        log.info('FileChosen')
        if self.isConnectionActive:
            log.info('Sending file')
            fExtension = os.path.splitext(filename)[1]
            parts = math.ceil(os.path.getsize(filename) / max)
            with open(filename, 'r+b') as source:
                part = 0
                while True:
                    msg = Message(self.socket.getsockname(), MessageType.FILE, None, None, part, parts, fExtension)
                    data = source.read(max)
                    msg.content = data
                    self.sendMessage(msg)
                    log.info(f'Sent part {1 + part} of {parts}')
                    part += 1
                    if part == parts:
                        break

    def nextMessageSize(self, msg):
        bytes = str(len(msg)).encode("utf-8")
        bytes = bytes + b' ' * (self.HEADER_LENGTH - len(bytes))
        return bytes

    def sendMessage(self, message):
        dumped = pickle.dumps(message)
        log.info(f'sending message: {len(dumped)} bytes')
        self.socket.sendall(self.nextMessageSize(dumped))
        self.socket.sendall(dumped)
