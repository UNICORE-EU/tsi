import os
import time
import unittest
import torque.BSS
import Log, TSI


class TestBSSTorque(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)
        self.config = {'tsi.testing': True,
            # mock submit cmd
            'tsi.submit_cmd': "echo 1234.server" }
        TSI.setup_defaults(self.config)
        self.bss = torque.BSS.BSS()
        self.bss.init(self.config, self.LOG)

    def test_init(self):
        self.assertTrue(self.config['tsi.submit_cmd'] is not None)

    def test_parse_qstat1(self):
        with open("tests/input/qstat_torque1.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("83 COMPLETED batch\n" in result)
        self.assertTrue("84 RUNNING fast\n" in result)
        self.assertTrue("85 QUEUED slow\n" in result)

    def test_parse_qstat2(self):
        with open("tests/input/qstat_torque2.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("11203 QUEUED large\n" in result)

    def test_extract_job_id(self):
        submit_result = '12345.torqueserver.cluster.com'
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
#TSI_TIME 60
#TSI_MEMORY 32
#TSI_NODES 1
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
        self.assertTrue(self.has_directive(submit_cmds, "#PBS -q", "fast"))
        self.assertTrue(self.has_directive(submit_cmds, "#PBS -l", "nodes=1:ppn=64"))
        self.assertTrue(self.has_directive(submit_cmds, "#PBS -l", "walltime=60"))
        self.assertTrue(self.has_directive(submit_cmds, "#PBS -A", "myproject"))
        self.assertTrue(self.has_directive(submit_cmds, "#PBS -t", "10%2"))


if __name__ == '__main__':
    unittest.main()
