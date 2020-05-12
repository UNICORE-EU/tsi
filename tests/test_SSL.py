import unittest
import logging
from lib import SSL


class TestSSL(unittest.TestCase):
    def setUp(self):
        # setup logger
        self.LOG = logging.getLogger("tsi.testing")
        self.LOG.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.LOG.handlers = [ch]
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
