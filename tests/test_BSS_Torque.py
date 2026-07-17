
import io, json
import os
import time
import unittest
import torque.BSS
import Log, TSI
import MockConnector

basedir = os.getcwd()

class TestBSSTorque(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog=False)
        self.config = TSI.get_default_config()
        self.config['tsi.testing']= True
        self.config['tsi.submit_cmd'] = 'echo 1234.server'
        self.bss = torque.BSS.BSS()
        self.bss.init(self.config, self.LOG)

    def test_init(self):
        self.assertTrue(self.config['tsi.submit_cmd'] is not None)

    def test_parse_qstat1(self):
        with open("tests/input/qstat_torque1.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("83 COMPLETED batch" in result)
        self.assertTrue("84 RUNNING fast" in result)
        self.assertTrue("85 QUEUED slow" in result)

    def test_parse_qstat2(self):
        with open("tests/input/qstat_torque2.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("11203 QUEUED large" in result)

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

    def test_report_details(self):
        os.chdir(basedir)
        self.config['tsi.details_cmd'] = "cat "
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)
        msg = "#TSI_BSSID tests/input/details_openpbs.txt\n"
        self.bss.get_job_details(msg, connector, self.config, self.LOG)
        _p = control_out.getvalue().replace("TSI_OK", "").strip()
        result = json.loads(_p)
        #print(json.dumps(result, indent=2))
        self.assertIn("PBS_O_HOME", result["Variable_List"])
        self.assertEqual("STDIN", result["Job_Name"])

if __name__ == '__main__':
    unittest.main()
