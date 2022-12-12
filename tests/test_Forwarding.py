import unittest
import os
import signal
import socket
import threading
import time
import Connector, Log, Server, TSI


def fake_service(config, LOG):
    # launch a fake service that we will connect to
    host = config['tsi.my_addr']
    port = config['tsi.my_port'] + 1
    LOG.info("SERVICE: pid <%s> listening on %s:%s" % (os.getpid(), host,port))
    service_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    service_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    service_server.bind((host, port))
    service_server.listen(2)
    (fake_service, (_, _)) = service_server.accept()
    service_server.close()
    LOG.info("SERVICE: client connected.")
    # read a message from the command socket
    testmsg = fake_service.recv(1024)
    LOG.info("SERVICE: got test message: %s" % testmsg)
    time.sleep(5)
    fake_service.shutdown(socket.SHUT_RDWR)
    fake_service.close()

class TestServer(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)
        self.config = {'tsi.my_addr': 'localhost',
                       'tsi.my_port': 14433,
                       'tsi.unicorex_machine': 'localhost',
                       'tsi.local_portrange': (50000, 50000, 50010),
                       'tsi.switch_uid': False,
                       'tsi.port_forwarding.rate_limit': 1024*1024,
                       }
        TSI.setup_defaults(self.config)

    def test_Forwarding(self):
        print("*** test_Forwarding")
        # fork, creating the TSI shepherd and a fake U/X
        pid = os.fork()
        if pid == 0:
            threading.Thread(target=fake_service, args=(self.config, self.LOG), daemon=True).start()
            socket1, _, msg = Server.connect(self.config, self.LOG)
            forwarder = Connector.Forwarder(socket1, msg, self.config, self.LOG)
            TSI.handle_function(TSI.start_forwarding, None, msg, forwarder, self.config, self.LOG)
        else:
            # this is the fake U/X
            # wait a bit to allow for setup of server socket at TSI
            time.sleep(2)
            # connect to the server
            host = self.config['tsi.my_addr']
            port = self.config['tsi.my_port']
            tsi = socket.create_connection((host, port))
            self.LOG.info("CLIENT: pid <%s> Connected to %s:%s" % (os.getpid(), host, port))
            host = self.config['tsi.unicorex_machine']
            msg = "start-forwarding 24433 localhost:%s nobody:DEFAULT_GID" % (port+1)
            tsi.sendall(bytes(msg, "UTF-8"))
            ux_port = 24433
            self.LOG.info("CLIENT: waiting for callback on %s:%s" % (host, ux_port))
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((host, ux_port))
            server.listen(2)
            (proxy_socket, (_, _)) = server.accept()
            server.close()
            testmsg = b'this is a test\n'
            self.LOG.info("CLIENT: connected, sending test message: %s" % testmsg)
            proxy_socket.sendall(testmsg)
            time.sleep(5)
            self.LOG.info("CLIENT: shutdown")
            tsi.sendall(b'shutdown')
            proxy_socket.shutdown(socket.SHUT_RDWR)
            proxy_socket.close()
            tsi.close()
            self.LOG.info("CLIENT: exiting.")
            os.kill(pid, signal.SIGKILL)

if __name__ == '__main__':
    unittest.main()
