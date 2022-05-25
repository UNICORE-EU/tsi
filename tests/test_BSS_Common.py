import io
import os
import time
import unittest
import MockBSS
import MockConnector
import Log, TSI


class TestBSSCommon(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing")
        self.config = { 'tsi.testing': True,
           # mock submit cmd
           'tsi.submit_cmd': "echo 1234.server" }
        TSI.setup_defaults(self.config)
        self.bss = MockBSS.BSS()
        self.bss.init(self.config, self.LOG)
        
    def test_submit(self):
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % int(100 * time.time())
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_SCRIPT
echo "Hello World!"
""" % (uspace, uspace)
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        self.bss.submit(msg, connector, self.config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            print("Submitted with ID %s" % result)
        control_source.close()
        os.chdir(cwd)
        
    def test_submit_raw(self):
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % int(105 * time.time())
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_JOB_MODE raw
#TSI_JOB_FILE %s/tests/input/raw-job-file.sh

#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
""" % (cwd, uspace, uspace)
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        self.bss.submit(msg, connector, self.config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            print("Submitted with ID %s" % result)
            print (uspace)
        control_source.close()

    def test_get_process_listing(self):
        cwd = os.getcwd()
        msg = "#TSI_GET_PROCESS_LISTING\n"
        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        self.bss.get_process_listing(msg, connector, self.config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            print("Process listing\n%s" % result)
        control_source.close()
        os.chdir(cwd)

if __name__ == '__main__':
    unittest.main()
