import io
import os
import unittest
import Utils


class TestTSI(unittest.TestCase):
    def setUp(self):
        pass

    def test_Helper_functions(self):
        
        msg = Utils.expand_variables(
            "home: $HOME user: $USER logname: $LOGNAME")
        self.assertTrue(os.environ['HOME'] in msg)
        self.assertTrue(os.environ['USER'] in msg)
        msg = 'blah\n#TSI_foo ham spam \nblah blah'
        param = Utils.extract_parameter(msg, "foo")
        self.assertEqual("ham spam ", param)
        msg = 'blah\n#TSI_xfoo ham spam \nblah blah'
        param = Utils.extract_parameter(msg, "foo")
        self.assertTrue(param is None)
        msg = 'blah\n#TSI_foo \nblah blah'
        param = Utils.extract_parameter(msg, "foo")
        self.assertTrue(param is None)
        msg = 'blah\n#TSI_nope \nblah blah'
        param = Utils.extract_parameter(msg, "foo", "spam")
        self.assertEqual("spam", param)

    def test_Helper_functions_2(self):
        msg = 'blah\n#TSI_foo NONE\nblah blah'
        param = Utils.extract_number(msg, "foo")
        self.assertEqual(-1, param)

        msg = 'blah\n#TSI_foo 123\nblah blah'
        param = Utils.extract_number(msg, "foo")
        self.assertEqual(123, param)

        msg = 'blah\nblah blah\n'
        param = Utils.extract_number(msg, "foo")
        self.assertEqual(-1, param)

        msg = 'blah\n#TSI_foo NONE\nblah blah\n'
        param = Utils.extract_number(msg, "foo")
        self.assertEqual(-1, param)

    def test_addperms(self):
        cwd = os.getcwd()
        try:
            os.mkdir(cwd+"/build")
        except:
            pass
        path = cwd + "/build/permstest"
        with io.open(path, "w") as f:
            f.write(u"abc")
            f.close()
        os.chmod(path, 0o700)
        self.assertEqual(0, os.stat(path)[0] & 0o7)
        Utils.addperms(path, 0o7)
        self.assertEqual(7, os.stat(path)[0] & 0o7)


if __name__ == '__main__':
    unittest.main()