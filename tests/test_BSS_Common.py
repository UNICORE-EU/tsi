import io
import logging
import os
import time
import unittest
import MockBSS
import MockConnector
from lib import TSI


class TestBSSCommon(unittest.TestCase):
    def setUp(self):
        # setup logger
        self.LOG = logging.getLogger("tsi.testing")
        self.LOG.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.LOG.handlers = [ch]
        self.bss = MockBSS.BSS()

    def test_submit(self):
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "echo 1234.server"
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
        self.bss.submit(msg, connector, config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            print("Submitted with ID %s" % result)
        control_source.close()
        os.chdir(cwd)
        
    def test_submit_raw(self):
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "echo 1234.server"
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
        self.bss.submit(msg, connector, config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            print("Submitted with ID %s" % result)
            print (uspace)
        control_source.close()
        

if __name__ == '__main__':
    unittest.main()
