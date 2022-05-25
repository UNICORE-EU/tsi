import unittest
import Log, SSL

class TestSSL(unittest.TestCase):
    def setUp(self):
        # setup logger
        self.LOG = Log.Logger("tsi.testing")
        self.config = {}
        self.config['tsi.my_addr'] = 'localhost'
        self.config['tsi.my_port'] = 14433
        self.config['tsi.njs_machine'] = 'localhost'
        self.config['tsi.njs_port'] = 24433
        self.config['tsi.keystore'] = 'tests/certs/tsi-key-plain.pem'
        self.config['tsi.keypass'] = 'the!tsi'
        self.config['tsi.certificate'] = 'tests/certs/tsi-cert.pem'
        self.config['tsi.truststore'] = 'tests/certs/tsi-truststore.pem'
        self.config['tsi.allowed_dn.1'] = 'CN=Foo,C=DE'
        self.config['tsi.allowed_dn.2'] = 'CN=Bar,C=EU'

    def test_ParseACL(self):
        dn = 'CN=Foo,C=DE'
        print(SSL.convert_dn(dn))


if __name__ == '__main__':
    unittest.main()
