import unittest
import os
import signal
import socket
import sys
import time
import Connector, Log, Server

class TestServer(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing")
        self.config = {'tsi.my_addr': 'localhost',
                       'tsi.my_port': 14433,
                       'tsi.njs_machine': 'localhost',
                       'tsi.njs_port': None}

    def test_Extract_Port(self):
        p = self.config['tsi.njs_port']
        self.config['tsi.njs_port'] = '12345'
        msg = "newtsi 5678"
        params = msg.split(" ", 1)[1]
        # use port from config
        port = Server.get_unicorex_port(self.config, params, self.LOG)
        self.assertEqual("12345", port)
        # read port from message
        self.config['tsi.njs_port'] = None
        port = Server.get_unicorex_port(self.config, params, self.LOG)
        self.assertEqual("5678", port)
        self.config['tsi.njs_port'] = p

    def test_Connect(self):
        # fork, creating the TSI shepherd and a fake U/X
        pid = os.fork()
        if pid == 0:
            # child, this is the TSI shepherd process
            command, data = Server.connect(self.config, self.LOG)
            # read a message from the command socket
            testmsg = command.recv(1024)
            self.LOG.info("TESTING: got test message: %s" % testmsg)
        else:
            # parent, this is the fake U/X
            # wait a bit to allow for setup of server socket at TSI
            time.sleep(2)
            # connect to the server
            host = self.config['tsi.my_addr']
            port = self.config['tsi.my_port']
            tsi = socket.create_connection((host, port))
            self.LOG.info("CLIENT: Connected to %s:%s" % (host, port))
            host = self.config['tsi.njs_machine']
            port = 24433
            tsi.sendall(b'newtsiprocess 24433')
            self.LOG.info(
                "CLIENT: waiting for callback on %s:%s" % (host, port))
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(2)
            (command, (_, _)) = server.accept()
            (data, (_, _)) = server.accept()
            testmsg = b'#TSI_PING\nENDOFMESSAGE'
            self.LOG.info(
                "CLIENT: connected, sending test message: %s" % testmsg)
            command.sendall(testmsg)
            # send shutdown and cleanup
            self.LOG.info("CLIENT: shutdown")
            tsi.sendall(b'shutdown')
            command.close()
            data.close()
            tsi.close()
            server.close()
            os.kill(pid, signal.SIGKILL)

    def test_UNICOREXShutDown(self):
        """ Test behaviour when the U/X side goes away """
        # fork, creating the TSI shepherd and a fake U/X
        pid = os.fork()
        if pid == 0:
            # child, this is the TSI shepherd process
            command, data = Server.connect(self.config, self.LOG)
            connector = Connector.Connector(command, data, self.LOG)
            # read a message
            try:
                self.LOG.info("SERVER: Reading from command socket")
                testmsg = connector.read_message()
                self.LOG.info("SERVER: got test message: %s" % testmsg)
                testmsg = connector.read_message()
                self.LOG.info("SERVER: got test message: %s" % testmsg)
                command.close()
            except IOError:
                print("Got: " + str(sys.exc_info()[1]))
                connector.close()
        else:
            # parent, this is the fake U/X
            # wait a bit to allow for setup of server socket at TSI
            time.sleep(2)
            # connect to the server
            host = self.config['tsi.my_addr']
            port = self.config['tsi.my_port']
            tsi = socket.create_connection((host, port))
            self.LOG.info("CLIENT: Connected to %s:%s" % (host, port))
            host = self.config['tsi.njs_machine']
            port = 24433
            tsi.sendall(b'newtsiprocess 24433')
            self.LOG.info(
                "CLIENT: waiting for callback on %s:%s" % (host, port))
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, port))
            server.listen(2)
            (command, (_, _)) = server.accept()
            (data, (_, _)) = server.accept()
            time.sleep(2)
            self.LOG.info("CLIENT: connected, now closing sockets.")
            command.close()
            data.close()
            time.sleep(5)
            self.LOG.info("CLIENT: shutting down.")
            tsi.close()
            server.close()
            os.kill(pid, signal.SIGKILL)


if __name__ == '__main__':
    unittest.main()
