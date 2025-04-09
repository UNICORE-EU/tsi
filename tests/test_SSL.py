import unittest
import socket
import Log, Utils


class TestSSL(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)
        self.config = {}
        self.config['tsi.my_addr'] = 'localhost'
        self.config['tsi.my_port'] = 14433
        self.config['tsi.unicorex_machine'] = 'localhost'
        self.config['tsi.unicorex_port'] = 24433
        self.config['tsi.certificate'] = 'tests/certs/tsi-cert.pem'
        self.config['tsi.truststore'] = 'tests/certs/tsi-truststore.pem'
        self.config['tsi.allowed_dn.1'] = 'CN=Foo,C=DE'
        self.config['tsi.allowed_dn.2'] = 'CN=Bar,C=EU'

    def test_ParseACL(self):
        dn = 'CN=Foo,C=DE'
        print(Utils.convert_dn(dn))

    def test_setup_ssl(self):
        try:
            import SSL
        except ImportError:
            print("SSL is not available, skipping test.")
            return
        self.config['tsi.keystore'] = 'tests/certs/tsi-key-encrypted.pem'
        self.config['tsi.keypass'] = 'the!tsi'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            ssl_server = SSL.setup_ssl(self.config, server, self.LOG, True)
            ssl_server.close()

    def test_setup_ssl_unencrypted_key(self):
        try:
            import SSL
        except ImportError:
            print("SSL is not available, skipping test.")
            return
        self.config['tsi.keystore'] = 'tests/certs/tsi-key-plain.pem'
        self.config['tsi.keypass'] = 'dummy-unused'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            ssl_server = SSL.setup_ssl(self.config, server, self.LOG, True)
            ssl_server.close()

if __name__ == '__main__':
    unittest.main()
