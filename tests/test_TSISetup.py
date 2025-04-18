import unittest
import os
import socket
import signal
import time
import Log, Server, TSI


class TestTSISetup(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog = False)
        self.file_name = "tests/conf/tsi.properties"

    def test_configure(self):
        config = TSI.read_config_file(self.file_name)
        TSI.finish_setup(config, self.LOG)
        self.assertEqual('600', config['tsi.usersCacheTtl'])
        acl = config['tsi.acl']
        self.assertEqual('NONE', acl['/'])

    def test_RunMain(self):
        config_file = "tests/conf/tsi.properties"
        pid = os.fork()
        if pid == 0:
            # child, this is the TSI shepherd process
            TSI.main(["TSI", config_file])
        else:
            # parent, this is the fake U/X
            LOG = Log.Logger("fake-unicorex", use_syslog=False)
            time.sleep(2)
            config = TSI.read_config_file(config_file)
            TSI.finish_setup(config, self.LOG)
            # connect to the server
            host = config['tsi.my_addr']
            port = int(config['tsi.my_port'])
            tsi = socket.create_connection((host, port))
            LOG.info("CLIENT: Connected to %s:%s" % (host, port))
            host = config['tsi.unicorex_machine']
            port = int(config['tsi.unicorex_port'])
            LOG.info("CLIENT: waiting for callback on %s:%s" % (host, port))
            server = Server.create_server(host, port, config)
            tsi.sendall(b'newtsiprocess 24433')
            server.listen(2)
            (command, _) = server.accept()
            (data, _) = server.accept()
            test_msg = b'#TSI_PING\nENDOFMESSAGE\n'
            LOG.info("CLIENT: connected, sending test message: %s" % test_msg)
            command.sendall(test_msg)
            reply = command.recv(1024)
            print(reply)
            # send shutdown and cleanup
            LOG.info("CLIENT: shutdown")
            tsi.sendall(b'shutdown')
            command.close()
            data.close()
            tsi.close()
            server.close()
            os.kill(pid, signal.SIGKILL)


if __name__ == '__main__':
    unittest.main()
