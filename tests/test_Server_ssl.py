import unittest
import os
import signal
import socket
import time
import Log, Server, TSI, Utils

class TestServerSSL(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)
        self.config = TSI.get_default_config()
        self.config['tsi.my_addr'] = 'localhost'
        self.config['tsi.my_port'] = 14433
        self.config['tsi.unicorex_machine'] = 'localhost'
        self.config['tsi.unicorex_port'] = 24433
        self.config['tsi.local_portrange'] = (0, -1, -1)
        self.config['tsi.keystore'] = 'tests/certs/tsi-key-plain.pem'
        self.config['tsi.certificate'] = 'tests/certs/tsi-cert.pem'
        self.config['tsi.truststore'] = 'tests/certs/tsi-truststore.pem'
        self.config['tsi.allowed_dns'] = [
            Utils.convert_dn('CN=TSI,O=UNICORE,C=EU')]

    def test_Connect(self):
        try:
            import SSL
        except ImportError:
            print("SSL is not available, skipping test.")
            return
        # fork, creating the TSI shepherd and a fake U/X
        pid = os.fork()
        if pid == 0:
            # child, this is the TSI shepherd process
            command, data, _ = Server.connect(self.config, self.LOG)
            # read a message from the command socket
            test_msg = command.recv(1024)
            self.LOG.info("TESTING: got test message: %s" % test_msg)
            command.close()
            data.close()
        else:
            # parent, this is the fake U/X
            # wait a bit to allow for setup of server socket at TSI
            time.sleep(2)
            # connect to the server
            host = self.config['tsi.my_addr']
            port = self.config['tsi.my_port']
            tsi = socket.create_connection((host, port))
            self.LOG.info("CLIENT: Connected to %s:%s" % (host, port))
            tsi = SSL.setup_ssl(self.config, tsi, self.LOG, server_mode=False)
            host = self.config['tsi.unicorex_machine']
            port = self.config['tsi.unicorex_port']
            tsi.sendall(b'newtsiprocess 24433')
            self.LOG.info(
                "CLIENT: waiting for callback on %s:%s" % (host, port))
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if Server._check_ipv6_support(host, port, self.config):
                server = socket.create_server((host, port), family=socket.AF_INET6, dualstack_ipv6=True, reuse_port=True)
            else:
                server = socket.create_server((host, port), reuse_port=True)
            server = SSL.setup_ssl(self.config, server, self.LOG, server_mode=True)
            server.listen(2)
            (command, _) = server.accept()
            (data, _) = server.accept()
            test_msg = b'#TSI_PING\nENDOFMESSAGE'
            self.LOG.info(
                "CLIENT: connected, sending test message: %s" % test_msg)
            command.sendall(test_msg)
            # send shutdown and cleanup
            self.LOG.info("CLIENT: shutdown")
            tsi.sendall(b'shutdown')
            command.close()
            data.close()
            tsi.close()
            server.close()
            os.kill(pid, signal.SIGKILL)


if __name__ == '__main__':
    unittest.main()
