import unittest
import logging
import io
import os
from lib import IO
import MockConnector


class TestLS(unittest.TestCase):
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

    def test_stat_file(self):
        path = "/tmp/"
        info = IO.get_info(path)
        self.assertTrue("DRWX" in info)
        self.assertTrue("/tmp" in info)

    def test_list(self):
        path = os.getcwd()
        conn = MockConnector.MockConnector(None, None, None, None, self.LOG)
        IO.list_directory(conn, path, False)
        out = conn.control_out.getvalue()
        print(out)

    def test_ls(self):
        path = os.getcwd()
        msg = """#TSI_LS
#TSI_FILE %s
#TSI_LS_MODE N
ENDOFMESSAGE
""" % path
        control_in = io.TextIOWrapper(
            io.BufferedReader(io.BytesIO(msg.encode("UTF-8"))))
        conn = MockConnector.MockConnector(control_in, None, None, None,
                                           self.LOG)
        IO.ls(msg, conn, {}, self.LOG)
        out = conn.control_out.getvalue()
        self.assertFalse("TSI_FAILED" in out)
        self.assertTrue("START_LISTING" in out)
        self.assertTrue("END_LISTING" in out)

    def test_df(self):
        path = os.getcwd()
        msg = """#TSI_DF
#TSI_FILE %s
ENDOFMESSAGE
""" % path
        control_in = io.TextIOWrapper(
            io.BufferedReader(io.BytesIO(msg.encode("UTF-8"))))
        conn = MockConnector.MockConnector(control_in, None, None, None,
                                           self.LOG)
        IO.df(msg, conn, {}, self.LOG)
        out = conn.control_out.getvalue()
        self.assertFalse("TSI_FAILED" in out)
        print(out)

    def test_df_nosuchpath(self):
        path = "/x_y_z"
        msg = """#TSI_DF
#TSI_FILE %s
ENDOFMESSAGE
""" % path
        control_in = io.TextIOWrapper(
            io.BufferedReader(io.BytesIO(msg.encode("UTF-8"))))
        conn = MockConnector.MockConnector(control_in, None, None, None,
                                           self.LOG)
        IO.df(msg, conn, {}, self.LOG)
        out = conn.control_out.getvalue()
        self.assertTrue("TSI_FAILED" in out)
        print(out)


if __name__ == '__main__':
    unittest.main()
