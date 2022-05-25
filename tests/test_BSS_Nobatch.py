import unittest
import time
import os
import io
import BSS, Log, TSI
import MockConnector


class TestBSSNobatch(unittest.TestCase):
    def setUp(self):
        # setup logger
        self.LOG = Log.Logger("tsi.testing")
        self.config = {'tsi.testing': True, 'tsi.switch_uid': False}
        TSI.setup_defaults(self.config)
        self.bss = BSS.BSS()
        self.bss.init(self.config, self.LOG)
        
    def test_parse_status_listing(self):
        with open("tests/input/qstat_nobatch.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)

    
    def test_submit(self):
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % int(time.time())
        os.mkdir(uspace)
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
        TSI.process(connector, self.config, self.LOG)
        result = control_out.getvalue()
        if "TSI_FAILED" in result:
            print(result)
        else:
            result = result.splitlines()[0]
            print("Submitted with ID %s" % result)
        control_source.close()
        children = self.config.get('tsi.NOBATCH.children')
        print("Children: " + str(children))
        self.assertEqual(1, len(children))
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                None, self.LOG)
        self.bss.get_status_listing(None, connector, self.config, self.LOG)
        qstat = control_out.getvalue()
        print (qstat+"\n")
        self.assertTrue(result in qstat)
        # test cleanup
        time.sleep(2)
        self.bss.cleanup(self.config)
        print("Children after cleanup: " + str(children))
        self.assertEqual(0, len(children))


if __name__ == '__main__':
    unittest.main()
