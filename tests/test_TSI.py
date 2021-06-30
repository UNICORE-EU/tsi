import unittest
import io, os
from lib import Log, TSI, BecomeUser
import MockConnector


class TestTSI(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing")
        self.file_name = "tests/conf/tsi.properties"

    def test_read_config(self):
        cwd = os.getcwd()
        file = "tests/input/test_config.properties"
        c = TSI.read_config_file(file, self.LOG)
        
        # parse allowed DNs correctly?
        acl = c["tsi.allowed_dns"]
        from lib import SSL
        subject = ((('commonName', 'Some Guy'),),
                   (('countryName','EU',),))
        self.assertTrue(SSL.match(subject, acl), msg="should match %s" % str(subject))
        subject = ((('commonName', 'Some Guy'),),
                   (('countryName','DE',),))
        self.assertFalse(SSL.match(subject, acl), msg="wrong match %s" % str(subject))
        
        # accept white space in property lines?
        self.assertEqual("some_value", c["whitespace"])
        os.chdir(cwd)

    def test_version_check(self):
        version_ok = TSI.assert_version()
        self.assertTrue(version_ok)

    def test_PING(self):
        cwd = os.getcwd()
        version = TSI.MY_VERSION
        config = {'tsi.testing': True}
        msg = "#TSI_PING\nENDOFMESSAGE\n"
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        self.assertTrue(version in result)
        self.assertTrue("ENDOFMESSAGE" in result)
        control_source.close()
        os.chdir(cwd)

    def test_PING2(self):
        cwd = os.getcwd()
        version = TSI.MY_VERSION
        config = {'tsi.testing': True, 'tsi.enforce_os_gids': False}
        config['tsi.use_id_to_resolve_gids'] = False
        msg = """#TSI_PING_UID
#TSI_IDENTITY nobody NONE
ENDOFMESSAGE
"""
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        BecomeUser.initialize(config, self.LOG)
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        self.assertTrue(version in result)
        control_source.close()
        os.chdir(cwd)
                 
    def test_Exec(self):
        cwd = os.getcwd()
        config = {'tsi.testing': True, 'tsi.switch_uid': False}
        msg = """#TSI_EXECUTESCRIPT
echo "Hello World!"
ENDOFMESSAGE
"""
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        self.assertTrue("TSI_OK" in result)
        self.assertTrue("Hello World!\n" in result)
        control_source.close()
        os.chdir(cwd)
        
    def test_Exec_discard_output(self):
        cwd = os.getcwd()
        config = {'tsi.testing': True, 'tsi.switch_uid': False}
        msg = """#TSI_EXECUTESCRIPT
#TSI_DISCARD_OUTPUT true
echo "Hello World!"
ENDOFMESSAGE
"""
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        self.assertTrue("TSI_OK" in result)
        control_source.close()
        os.chdir(cwd)

    def test_Exec_error(self):
        cwd = os.getcwd()
        config = {'tsi.testing': True, 'tsi.switch_uid': False}
        msg = """#TSI_EXECUTESCRIPT
some_invalid_command
ENDOFMESSAGE
"""
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        self.assertTrue("TSI_FAILED" in result)
        self.assertTrue("127" in result)
        control_source.close()
        os.chdir(cwd)

if __name__ == '__main__':
    unittest.main()
