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
    (fake_service, _) = service_server.accept()
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
        self.config = TSI.get_default_config()
        self.config['tsi.my_addr'] = '127.0.0.1'
        self.config['tsi.my_port'] = 14433
        self.config['tsi.unicorex_machine'] = '127.0.0.1'
        self.config['tsi.local_portrange']= (50000, 50000, 50010)
        self.config['tsi.switch_uid'] = False
        self.config['tsi.port_forwarding.rate_limit'] = 1024*1024

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
            ux_port = 24433
            host = self.config['tsi.unicorex_machine']
            msg = "start-forwarding %s %s:%s nobody:DEFAULT_GID" % (ux_port, host, port+1)
            if Server._check_ipv6_support(host, port, self.config):
                server = socket.create_server((host, ux_port), family=socket.AF_INET6, dualstack_ipv6=True, reuse_port=True)
            else:
                server = socket.create_server((host, ux_port), reuse_port=True)
            tsi.sendall(bytes(msg, "UTF-8"))
            self.LOG.info("CLIENT: waiting for callback on %s:%s" % (host, ux_port))
            server.listen(2)
            (proxy_socket, _) = server.accept()
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
