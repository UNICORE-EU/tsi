import unittest
import logging
import io
import os
from lib import TSI
import MockConnector


class TestIO(unittest.TestCase):
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

    def readlines(self, path):
        f = io.open(path, "r")
        lines = f.readlines()
        f.close()
        return lines

    def test_get_file_chunk(self):
        cwd = os.getcwd()
        path = cwd + "/tests/input/testfile.txt"
        length = os.stat(path).st_size
        config = {'tsi.testing': True, 'tsi.switch_uid': False}
        msg = """#TSI_GETFILECHUNK
#TSI_FILE %s
#TSI_START 0
#TSI_LENGTH %d
ENDOFMESSAGE
""" % (path, length)

        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        data_out = io.BytesIO()
        connector = MockConnector.MockConnector(control_in, control_out, None,
                                                data_out, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        data = str(data_out.getvalue())
        print(result)
        self.assertTrue("TSI_OK" in result)
        self.assertTrue("this is a test file" in data)
        control_source.close()
        data_out.close()
        os.chdir(cwd)
        
    def test_put_file_chunk(self):
        cwd = os.getcwd()
        path = cwd + "/build/testfile.txt"
        config = {'tsi.testing': True, 'tsi.switch_uid': False}
        data = b"this is some testdata used for testing the TSI I/O \n"
        msg = """#TSI_PUTFILECHUNK
#TSI_FILE %s 600
#TSI_FILESACTION 1
#TSI_START 0
#TSI_LENGTH %d
ENDOFMESSAGE
""" % (path, len(data))

        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        data_in = io.BytesIO(data)
        connector = MockConnector.MockConnector(control_in, control_out,
                                                data_in, None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        self.assertTrue("TSI_OK" in result)
        control_source.close()

        lines = self.readlines(path)
        self.assertEqual(1, len(lines))
        self.assertTrue(data.decode() in lines[0])

        # test append
        msg = """#TSI_PUTFILECHUNK
#TSI_FILE %s 600
#TSI_FILESACTION 3
#TSI_START 0
#TSI_LENGTH %d
ENDOFMESSAGE
""" % (path, len(data))

        control_source = io.BufferedReader(io.BytesIO(msg.encode("UTF-8")))
        control_in = io.TextIOWrapper(control_source)
        control_out = io.StringIO()
        data_in = io.BytesIO(data)
        connector = MockConnector.MockConnector(control_in, control_out,
                                                data_in, None, self.LOG)
        TSI.process(connector, config, self.LOG)
        result = control_out.getvalue()
        print(result)
        self.assertTrue("TSI_OK" in result)
        lines = self.readlines(path)
        self.assertEqual(2, len(lines))
        self.assertTrue(data.decode() in lines[0])
        os.chdir(cwd)

if __name__ == '__main__':
    unittest.main()
