""" Wrapper class around common I/O operations """

from os import _exit
from socket import socket
from time import sleep, time
import Server
import threading
import Utils
from Log import Logger

class Connector():
    def __init__(self, command: socket, data: socket, LOG: Logger):
        self.data = data
        self.command = command
        self.control_in = command.makefile("r")
        self.control_out = command.makefile("w")
        self.data_in = data.makefile("rb")
        self.data_out = data.makefile("wb")
        self.LOG = LOG
        self.buf_size = 32768

    def failed(self, message: str):
        """ Write single line of TSI_FAILED and error message to control
        channel
        """
        msg = "TSI_FAILED: "
        if message is not None:
            msg += message.replace("\n", ":")
        self.write_message(msg)

    def ok(self, message: str=None):
        """ Write TSI_OK line and any message to control channel """
        msg = "TSI_OK"
        if message is not None:
            msg += "\n"
            msg += message
        self.write_message(msg)

    def read_message(self):
        """Read message terminated by ENDOFMESSAGE from control channel
           Returns unicode
        """
        message = ''
        while True:
            line = self.control_in.readline()
            if len(line) == 0:
                raise IOError("Socket closed")
            if line == 'ENDOFMESSAGE\n':
                break
            message += line
        return Utils.encode(message)

    def write_message(self, message):
        """ Write message to control channel and add newline """
        if message is not None:
            self.control_out.write(Utils.encode(message))
            self.control_out.write(u"\n")
            self.control_out.flush()

    def read_data(self, maxlen):
        limit = min(maxlen, self.buf_size)
        return self.data_in.read(limit)

    def write_data(self, data):
        written = self.data_out.write(data)
        self.data_out.flush()
        if written is None:
            written = len(data)
        return written

    def close(self):
        for s in self.command, self.data:
            try:
                s.close()
            except:
                pass


class Forwarder():
    def __init__(self, client_socket: socket, message: str, config: dict, LOG: Logger):
        self.client_socket = client_socket
        self.service_socket = None
        self.message = message
        self.config = config
        self.LOG = LOG
        self.rate_limit = int(config.get("tsi.port_forwarding.rate_limit", 0))

    def failed(self, message: str):
        self.LOG.error(message)
        self.close(1)

    def start_forwarding(self):
        service = Utils.extract_parameter(self.message, "FORWARDING_CONNECT_TO", None)
        if(service==None):
            self.LOG.error("No service host:port to connect to")
            self.close(1)
        service_host, service_port = service.split(":")
        self.LOG.info("Connecting to %s:%s" % (service_host, service_port))
        self.service_socket = Server.open_connection((service_host, service_port), 10, self.config)
        Server.configure_socket(self.service_socket)
        if self.rate_limit>0:
            lim = "(max. %d kB/sec)" % int(float(self.rate_limit)/1024)
        else:
            lim = ""
        self.LOG.info("Starting TCP forwarding %s %s <--> %s" % (lim, self.client_socket.getpeername() , self.service_socket.getpeername()))
        threading.Thread(target=self.transfer, args=(self.client_socket, self.service_socket)).start()
        threading.Thread(target=self.transfer, args=(self.service_socket, self.client_socket)).start()

    def close(self, status=0):
        for s in self.client_socket, self.service_socket:
            try:
                s.close()
            except:
                pass
        _exit(status)

    def transfer(self, source: socket, destination: socket):
        desc = "%s --> %s" % (source.getpeername(), destination.getpeername())
        limit_rate = self.rate_limit > 0
        start_time = int(time()*1000)
        total = 0
        sleep_time = 0
        while True:
            try:
                buffer = source.recv(4096)
                if len(buffer) > 0:
                    destination.send(buffer)
                    total+=len(buffer)
                elif len(buffer)<=0:
                    break
            except:
                break
            if limit_rate:
                interval = int(time()*1000 - start_time) + 1
                current_rate = 1000 * total / interval
                if current_rate < self.rate_limit:
                    sleep_time = int(0.5 * sleep_time)
                else:
                    sleep_time = sleep_time + 5
                    sleep(0.001*sleep_time)
        self.LOG.info("Stopping TCP forwarding %s" % desc)
        self.close()