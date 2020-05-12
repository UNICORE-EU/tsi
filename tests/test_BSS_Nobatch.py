import unittest
import logging
import time
import os
import io
from lib import BSS, TSI
import MockConnector


class TestBSSNobatch(unittest.TestCase):
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

    def test_parse_status_listing(self):
        bss = BSS.BSS()
        config = {'tsi.testing': True, 'tsi.switch_uid': False}
        bss.init(config, self.LOG)
        with open("tests/input/qstat_nobatch.txt", "r") as sample:
            qstat_output = sample.read()
        result = bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)

    
    def test_submit(self):
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % int(time.time())
        os.mkdir(uspace)
        config = {'tsi.testing': True, 'tsi.switch_uid': False}
        bss = BSS.BSS()
        bss.init(config, self.LOG)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_STDOUT stdout
#TSI_STDERR stderr
#TSI_SCRIPT
#TSI_TIME 60
#TSI_MEMORY 32
#TSI_JOBNAME test_job
#TSI_SCRIPT

echo "Hello World!"
sleep 1
ENDOFMESSAGE
""" % (uspace, uspace)

        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            result = result.splitlines()[0]
            print("Submitted with ID %s" % result)
        control_source.close()
        children = config.get('tsi.NOBATCH.children')
        print("Children: " + str(children))
        self.assertEqual(1, len(children))
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        bss.get_status_listing(None, connector, config, self.LOG)
        qstat = control_out.getvalue()
        print (qstat+"\n")
        self.assertTrue(result in qstat)
        # test cleanup
        time.sleep(2)
        bss.cleanup(config)
        print("Children after cleanup: " + str(children))
        self.assertEqual(0, len(children))


if __name__ == '__main__':
    unittest.main()
