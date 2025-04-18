import unittest
import os
import signal
import socket
import sys
import time
import Connector, Log, Server, TSI

class TestServer(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)
        self.config = TSI.get_default_config()
        self.config['tsi.my_addr'] = 'localhost'
        self.config['tsi.my_port'] = 14433
        self.config['tsi.unicorex_machine'] = 'localhost'
        self.config['tsi.local_portrange'] = (50000, 50000, 50010)

    def test_Extract_Port(self):
        print("*** test_Extract_Port")
        self.config['tsi.unicorex_port'] = '12345'
        msg = "newtsi 5678"
        params = msg.split(" ", 1)[1]
        # use port from config
        port = Server.get_unicorex_port(self.config, params)
        self.assertEqual("12345", port)
        # read port from message
        self.config['tsi.unicorex_port'] = None
        port = Server.get_unicorex_port(self.config, params)
        self.assertEqual("5678", port)
  
    def test_Connect(self):
        print("*** test_Connect")
        # fork a fake U/X
        pid = os.fork()
        if pid == 0:
            # this is the TSI
            command, data, _ = Server.connect(self.config, self.LOG)
            testmsg = command.recv(1024)
            self.LOG.info("TESTING: got test message: %s" % testmsg)
            time.sleep(5)
            command.close()
            data.close()
        else:
            # this is the fake U/X
            # wait a bit to allow for setup of server socket at TSI
            time.sleep(2)
            # connect to the server
            host = self.config['tsi.my_addr']
            port = self.config['tsi.my_port']
            tsi = socket.create_connection((host, port))
            self.LOG.info("CLIENT: Connected to %s:%s" % (host, port))
            host = self.config['tsi.unicorex_machine']
            port = 24433
            tsi.sendall(b'newtsiprocess 24433')
            self.LOG.info("CLIENT: waiting for callback on %s:%s" % (host, port))
            if Server._check_ipv6_support(host, port, self.config):
                server = socket.create_server((host, port), family=socket.AF_INET6, dualstack_ipv6=True, reuse_port=True)
            else:
                server = socket.create_server((host, port), reuse_port=True)
            server.listen(2)
            (command, _) = server.accept()
            (data, _) = server.accept()
            testmsg = b'#TSI_PING\nENDOFMESSAGE'
            self.LOG.info("CLIENT: connected, sending test message: %s" % testmsg)
            command.sendall(testmsg)
            # send shutdown and cleanup
            self.LOG.info("CLIENT: shutdown")
            tsi.sendall(b'shutdown')
            command.close()
            data.close()
            tsi.close()
            server.close()
            self.LOG.info("CLIENT: exiting.")
            os.kill(pid, signal.SIGKILL)

    def test_UNICOREXShutDown(self):
        """ Test behaviour when the U/X side goes away """
        print("*** test_UNICOREXShutDown")
        # fork, creating the TSI shepherd and a fake U/X
        pid = os.fork()
        if pid == 0:
            # child, this is the TSI shepherd process
            command, data, _ = Server.connect(self.config, self.LOG)
            connector = Connector.Connector(command, data, self.LOG)
            # read a message
            try:
                self.LOG.info("SERVER: Reading from command socket")
                testmsg = connector.read_message()
                self.LOG.info("SERVER: got test message: %s" % testmsg)
                testmsg = connector.read_message()
                self.LOG.info("SERVER: got test message: %s" % testmsg)
                connector.close()
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
            host = self.config['tsi.unicorex_machine']
            port = 24433
            server = Server.create_server(host, port, self.config)
            self.LOG.info("CLIENT: waiting for callback on %s:%s" % (host, port))
            tsi.sendall(b'newtsiprocess 24433')
            server.listen(2)
            (command, _) = server.accept()
            (data, _) = server.accept()
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
