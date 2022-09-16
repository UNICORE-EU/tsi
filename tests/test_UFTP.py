import io
import os
import time
import unittest
import MockConnector
import Log, TSI, UFTP


class TestUFTP(unittest.TestCase):

    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)

    def test_submit(self):
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "echo 1234.server"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % int(100 * time.time())
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_UFTP
#TSI_USPACE_DIR %s
#TSI_OUTCOME_DIR %s
#TSI_UFTP_HOST localhost
#TSI_UFTP_PORT 54434
#TSI_UFTP_SECRET test123
#TSI_UFTP_MODE GET
#TSI_UFTP_REMOTE_FILE foo
#TSI_UFTP_LOCAL_FILE bar

""" % (uspace, uspace)
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        UFTP.uftp(msg, connector, config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            print("OK!")
        control_source.close()
        os.chdir(cwd)

if __name__ == '__main__':
    unittest.main()
