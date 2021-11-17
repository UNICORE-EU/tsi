import io
import os
import unittest
import uuid
import slurm.BSS
import MockConnector
from lib import Log, TSI
from time import sleep

basedir = os.getcwd()

class TestBSSSlurm(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing")
        self.bss = slurm.BSS.BSS()
        self.config = {'tsi.testing': True,
                # mock submit/alloc cmds
                'tsi.submit_cmd': "echo 'Submitted batch job 1234'",
                'tsi.alloc_cmd':  "echo 'salloc: Granted job allocation 115463'"
        }
        TSI.setup_defaults(self.config)
        self.bss.init(self.config, self.LOG)

    def test_init(self):
        self.assertTrue(self.config['tsi.submit_cmd'] is not None)
        self.assertTrue(self.config['tsi.get_processes_cmd'] is not None)

    def test_parse_qstat(self):
        os.chdir(basedir)
        with open("tests/input/qstat_slurm.txt", "r") as sample:
            qstat_output = sample.read()
        result = self.bss.parse_status_listing(qstat_output)
        self.assertTrue("QSTAT\n" in result)
        self.assertTrue("182867 RUNNING large\n" in result)
        self.assertTrue("182917 RUNNING batch\n" in result)
        self.assertTrue("182588 QUEUED batch\n" in result)
        self.assertTrue("182732 RUNNING large\n" in result)
        self.assertTrue("182744 QUEUED large\n" in result)
        self.assertTrue("182745 RUNNING small\n" in result)
        self.assertTrue("182800 COMPLETED small\n" in result)

    def test_extract_job_id(self):
        os.chdir(basedir)
        reply = "Submitted job 123"
        result = self.bss.extract_job_id(reply)
        self.assertTrue("123" in result)
        reply = "Error 123"
        result = self.bss.extract_job_id(reply)
        self.assertTrue(result is None)

    def has_directive(self, cmds, name, value=None):
        result = False
        for line in cmds:
            if line.startswith(name):
                if value:
                    result=value in line
                else:
                    result=True
                break
        return result

    def test_create_submit_script(self):
        os.chdir(basedir)
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
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
#TSI_BSS_NODES_FILTER NONE
#TSI_JOBNAME test_job
#TSI_SCRIPT
echo "Hello World!"
sleep 3
""" % (uspace, uspace)
        submit_cmds = self.bss.create_submit_script(msg, self.config, self.LOG)
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --partition", "fast"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --nodes", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --ntasks-per-node", "64"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --mem", "32"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --time", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --array", "10%2"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --account", "myproject"))
        self.assertFalse(self.has_directive(submit_cmds, "#SBATCH --constraint"))
        self.assertFalse(self.has_directive(submit_cmds, "#SBATCH --exclusive"))

    def test_submit_exclusive(self):
        os.chdir(basedir)
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_MEMORY 0
#TSI_SSR_EXCLUSIVE true
#TSI_SCRIPT
echo "Hello World!"
sleep 3
""" % (uspace, uspace)
        submit_cmds = self.bss.create_submit_script(msg, self.config, self.LOG)
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --mem", "0"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --exclusive"))


    def test_submit_nodes_filter(self):
        os.chdir(basedir)
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_STDOUT stdout
#TSI_STDERR stderr
#TSI_QUEUE fast
#TSI_PROJECT myproject
#TSI_TIME 60
#TSI_MEMORY 32
#TSI_NODES 1
#TSI_PROCESSORS_PER_NODE 64
#TSI_ARRAY 10
#TSI_ARRAY_LIMIT 2
#TSI_BSS_NODES_FILTER gpu
#TSI_SCRIPT
echo "Hello World!"
sleep 3
""" % (uspace, uspace)
        submit_cmds = self.bss.create_submit_script(msg, self.config, self.LOG)
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --partition", "fast"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --nodes", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --ntasks-per-node", "64"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --mem", "32"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --time", "1"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --array", "10%2"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --account", "myproject"))
        self.assertTrue(self.has_directive(submit_cmds, "#SBATCH --constraint", "gpu"))


    def test_submit_raw(self):
        os.chdir(basedir)
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        with open(uspace+"/foo.sh", "w") as f:
            f.write("""#!/bin/bash
#SLURM --myopts
            """)

        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_JOB_MODE raw
#TSI_JOB_FILE foo.sh
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
""" % (uspace, uspace)

        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)

        self.bss.submit(msg, connector, self.config, self.LOG)
        result = control_out.getvalue()
        assert "1234" in result
        os.chdir(cwd)


    def test_submit_normal(self):
        os.chdir(basedir)
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)

        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_JOB_MODE normal
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
#TSI_SCRIPT
echo "Hello World!"
""" % (uspace, uspace)

        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)
        self.bss.submit(msg,connector, self.config, self.LOG)

        result = control_out.getvalue()
        assert "1234" in result
        os.chdir(cwd)

    def test_create_alloc_cmd(self):
        os.chdir(basedir)
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)
        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_JOB_MODE allocate
#TSI_USPACE_DIR %s
#TSI_QUEUE fast
#TSI_PROJECT myproject
#TSI_TIME 600
#TSI_MEMORY 32
#TSI_NODES 4
#TSI_PROCESSORS_PER_NODE 64
#TSI_BSS_NODES_FILTER NONE
#TSI_JOBNAME test_job
#TSI_SCRIPT
""" % (uspace)
        submit_cmds = self.bss.create_alloc_script(msg, self.config, self.LOG)
        cmd = ""
        for line in submit_cmds:
            cmd += line + u"\n"
        self.assertTrue("salloc" in cmd)
        self.assertTrue("--partition=fast" in cmd)
        self.assertTrue("--account=myproject" in cmd)
        self.assertTrue("--nodes=4" in cmd)
        self.assertTrue("--mem=32" in cmd)
        self.assertTrue("--time=10" in cmd)
        self.assertTrue("--ntasks-per-node=64" in cmd)
        self.assertFalse("--constraint" in cmd)
        print(cmd)

    def test_run_alloc_cmd(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.alloc_cmd'] = "echo 'salloc: Granted job allocation 115463'"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)

        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_JOB_MODE allocate
#TSI_USPACE_DIR %s
#TSI_QUEUE fast
#TSI_PROJECT myproject
#TSI_NODES 4
""" % (uspace)

        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)

        self.bss.submit(msg,connector, config, self.LOG)
        result = control_out.getvalue()
        sleep(10)
        with open("%s/ALLOCATION_ID" % uspace) as f:
            line = f.readlines()[0]
            print("Allocation ID : %s" % line)
            self.assertTrue("115463" in line)
        os.chdir(cwd)

    def test_submit_fail(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        # mock submit cmd
        config['tsi.submit_cmd'] = "/bin/false"
        cwd = os.getcwd()
        uspace = cwd + "/build/uspace-%s" % uuid.uuid4()
        os.mkdir(uspace)

        msg = """#!/bin/bash
#TSI_SUBMIT
#TSI_OUTCOME_DIR %s
#TSI_USPACE_DIR %s
""" % (uspace, uspace)

        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)

        self.bss.submit(msg,connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        assert "TSI_FAILED" in result
        os.chdir(cwd)

    def test_parse_details(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        TSI.setup_defaults(config)
        with open("tests/input/details_slurm.txt", "r") as f:
            raw = f.read()
        parsed = self.bss.parse_job_details(raw)
        print(parsed)

    def test_report_details(self):
        os.chdir(basedir)
        config = {'tsi.testing': True}
        config['tsi.details_cmd'] = "cat "
        TSI.setup_defaults(config)
        control_out = io.StringIO()
        connector = MockConnector.MockConnector(None, control_out, None,
                                                None, self.LOG)
        msg = "#TSI_BSSID tests/input/details_slurm.txt\n"
        self.bss.get_job_details(msg, connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)


if __name__ == '__main__':
    unittest.main()
