import unittest
import os
import signal
import time
import Log, Runner

class TestRunner(unittest.TestCase):
    def setUp(self):
        self.LOG = Log.Logger("tsi.testing", use_syslog = False)
        self.file_name = "tests/conf/tsi.properties"

    def test_Runner(self):
        child_read, pw = os.pipe()
        pr, child_write = os.pipe()
        config_file = "tests/conf/tsi.properties"
        pid = os.fork()
        if pid == 0:
            # child, this is the one-shot TSI runner process
            os.dup2(child_read, 0)
            os.dup2(child_write, 1)
            Runner.main(["TSI", config_file])
        else:
            # parent, this is the fake U/X
            try:
                time.sleep(2)
                test_msg = b'#TSI_PING\nENDOFMESSAGE\n'
                os.write(pw, test_msg)
                reply = ""
                with open(pr, "r") as f:
                    while True:
                        line = f.readline()
                        reply+=line+"\n"
                        if "ENDOFMESSAGE" in line:
                            break
                self.assertIn("__VERSION__", reply)
            finally:
                os.kill(pid, signal.SIGKILL)

if __name__ == '__main__':
    unittest.main()
