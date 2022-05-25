import os
import time
import unittest
import loadleveler.BSS
import Log, TSI


class TestBSSLoadLeveler(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing")
        self.bss = loadleveler.BSS.BSS()
        self.config = {'tsi.testing': True}
        TSI.setup_defaults(self.config)
        self.bss.init(self.config, self.LOG)
        
    def test_init(self):
        self.assertTrue(self.config['tsi.submit_cmd'] is not None)

    def test_parse_qstat(self):
        with open("tests/input/qstat_ll.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("266540 RUNNING m001\n" in result)
        self.assertTrue("266560 RUNNING m002\n" in result)
        self.assertTrue("266530 COMPLETED m001\n" in result)

    def test_extract_job_id(self):
        submit_result = 'llsubmit: The job "login3.cluster.com.12345" has been submitted.'
        self.assertTrue("12345"==self.bss.extract_job_id(submit_result))

    def has_directive(self, cmds, name, value=None):
        result = False
        for line in cmds:
            if line.startswith(name):
                if value:
                    result=value in line
                else:
                    result=True
                if result:
                    break
        return result

    def test_submit(self):
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % int(100 * time.time())
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_STDOUT stdout
#TSI_STDERR stderr
#TSI_SCRIPT
#TSI_QUEUE fast
#TSI_PROJECT myproject
#TSI_TIME 120
#TSI_MEMORY 32
#TSI_NODES 2
#TSI_PROCESSORS_PER_NODE 64
#TSI_ARRAY 10
#TSI_ARRAY_LIMIT 2
#TSI_JOBNAME test_job
#TSI_SCRIPT
echo "Hello World!"
sleep 3
""" % (uspace, uspace)
        submit_cmds = self.bss.create_submit_script(msg, self.config, self.LOG)
        print(submit_cmds)
        self.assertTrue(self.has_directive(submit_cmds, "# @ account_no = ", "myproject"))
        self.assertTrue(self.has_directive(submit_cmds, "# @ class = ", "fast"))
        self.assertTrue(self.has_directive(submit_cmds, "# @ bg_size = ", "2"))
        self.assertTrue(self.has_directive(submit_cmds, "# @ cpu_limit = ", "120"))


if __name__ == '__main__':
    unittest.main()
