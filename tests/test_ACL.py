import unittest
import io
import os
import ACL, Log, TSI
import MockConnector


class TestACL(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing")
        self.config = {}
        self.config = {'tsi.testing': True}
        self.config['tsi.switch_uid'] = False
        self.config['tsi.acl'] = {}
        self.config['tsi.getfacl'] = "getfacl"
        self.config['tsi.setfacl'] = "setfacl"
        try:
            os.mkdir("/tmp/test_TSI_ACL")
        except:
            pass

    def setup_connector(self, msg):
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        data_out = io.BytesIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                data_out, self.LOG)
        return connector

    def test_check_support(self):
        acl = {'/tmp': 'POSIX', '/tmp/foo': 'NFS'}
        result = ACL.check_support("/tmp/", acl)
        self.assertEqual("POSIX", result)
        result = ACL.check_support("/tmp/foo", acl)
        self.assertEqual("NFS", result)
        result = ACL.check_support("/tmp/foo/bar", acl)
        self.assertEqual("NFS", result)
        result = ACL.check_support("/usr", acl)
        self.assertEqual("NONE", result)

    def test_unset_posix(self):
        ACL.unset_posix()

    def test_getsupport_via_connector(self):
        acl_support = self.config['tsi.acl']
        acl_support['/tmp'] = "POSIX"
        msg = """#TSI_FILE_ACL
#TSI_ACL_OPERATION CHECK_SUPPORT
#TSI_ACL_PATH /tmp
ENDOFMESSAGE
"""
        connector = self.setup_connector(msg)
        TSI.process(connector, self.config, self.LOG)
        result = connector.control_out.getvalue()
        self.assertTrue("TSI_OK" in result)
        self.assertTrue("true" in result)

    def test_getfacl_via_connector(self):
        acl_support = self.config['tsi.acl']
        acl_support['/tmp'] = "POSIX"
        msg = """#TSI_FILE_ACL
#TSI_ACL_OPERATION GETFACL
#TSI_ACL_PATH /tmp
ENDOFMESSAGE
"""
        connector = self.setup_connector(msg)
        TSI.process(connector, self.config, self.LOG)
        result = connector.control_out.getvalue()
        self.assertTrue("TSI_OK" in result)

        msg = """#TSI_FILE_ACL
#TSI_ACL_OPERATION GETFACL
#TSI_ACL_PATH /opt
ENDOFMESSAGE
"""
        connector = self.setup_connector(msg)
        TSI.process(connector, self.config, self.LOG)
        result = connector.control_out.getvalue()
        print(result)
        self.assertTrue("TSI_FAILED" in result)
        self.assertTrue("unsupported" in result)

    def test_setfacl_via_connector(self):
        acl_support = self.config['tsi.acl']
        acl_support['/tmp/test_TSI_ACL'] = "POSIX"
        self.config['tsi.setfacl'] = "setfacl"
        msg = """#TSI_FILE_ACL
#TSI_ACL_OPERATION SETFACL
#TSI_ACL_COMMAND MODIFY RECURSIVE
#TSI_ACL_COMMAND_SPEC U %s rwx
#TSI_ACL_PATH /tmp/test_TSI_ACL
ENDOFMESSAGE
""" % os.environ['USER']
        connector = self.setup_connector(msg)
        TSI.process(connector, self.config, self.LOG)
        result = connector.control_out.getvalue()
        self.assertTrue("TSI_OK" in result)

        msg = """#TSI_FILE_ACL
#TSI_ACL_OPERATION GETFACL
#TSI_ACL_PATH /tmp/test_TSI_ACL
ENDOFMESSAGE
"""
        connector = self.setup_connector(msg)
        TSI.process(connector, self.config, self.LOG)
        result = connector.control_out.getvalue()
        self.assertTrue("TSI_OK" in result)
        print(result)


if __name__ == '__main__':
    unittest.main()
