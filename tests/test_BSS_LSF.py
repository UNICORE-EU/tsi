import os
import time
import unittest
import lsf.BSS
import Log, TSI


class TestBSSLSF(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)
        self.bss = lsf.BSS.BSS()
        self.config = TSI.get_default_config()
        self.config['tsi.testing'] = True
        self.config['tsi.submit_cmd'] = 'echo 1234.server'
        self.bss.init(self.config, self.LOG)

    def test_init(self):
        self.assertTrue(self.config['tsi.submit_cmd'] is not None)

    def test_parse_qstat(self):
        with open("tests/input/qstat_lsf.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("1002 RUNNING large" in result)
        self.assertTrue("1003 QUEUED batch" in result)

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
        self.assertTrue(self.has_directive(submit_cmds, "#BSUB -q", "fast"))
        self.assertTrue(self.has_directive(submit_cmds, "#BSUB -W", "2"))
        self.assertTrue(self.has_directive(submit_cmds, "#BSUB -P", "myproject"))
        self.assertTrue(self.has_directive(submit_cmds, "#BSUB -n", "128"))
        self.assertTrue(self.has_directive(submit_cmds, "#BSUB -J", "\"test_job[10]%2\""))


if __name__ == '__main__':
    unittest.main()
