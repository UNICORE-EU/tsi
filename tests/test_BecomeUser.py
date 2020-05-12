import unittest
import logging
import os
import pwd
import grp
from lib import BecomeUser, TSI


class TestBecomeUser(unittest.TestCase):
    def setUp(self):
        # setup logger
        self.LOG = logging.getLogger("tsi.testing")
        self.LOG.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.LOG.handlers = [ch]
        self.config = {'tsi.testing': True}
        TSI.setup_defaults(self.config)
        BecomeUser.initialize(self.config, self.LOG)

    def getlogin(self):
        return pwd.getpwuid(os.getuid())[0]

    def test_check_membership(self):
        uc = self.config['tsi.user_cache']
        user = self.getlogin()
        gid = uc.get_gid_4user(user)
        (group, _, _, _) = grp.getgrgid(gid)
        result = BecomeUser.check_membership(group, gid, user, self.config)
        self.assertTrue(result)
        self.config['tsi.enforce_os_gids'] = False
        other_gid = 1
        result = BecomeUser.check_membership(group, other_gid, user,
                                             self.config)
        self.assertTrue(result)

    def test_get_groups(self):
        uc = self.config['tsi.user_cache']
        user = self.getlogin()
        gid = uc.get_gid_4user(user)
        (group, _, _, _) = grp.getgrgid(gid)
        new_gid = BecomeUser.get_primary_group(group, user, uc, True,
                                               self.config, self.LOG)
        self.assertEqual(gid, new_gid)
        groups = [group]
        sup_gids = BecomeUser.get_supplementary_groups(groups, new_gid, user,
                                                       self.config, self.LOG)
        print("Got groups: %s" % sup_gids)
        groups = ["DEFAULT_GID"]
        sup_gids = BecomeUser.get_supplementary_groups(groups, new_gid, user,
                                                       self.config, self.LOG)
        print(sup_gids)
        print("Got groups: %s" % sup_gids)

    def test_become_user(self):
        user = self.getlogin()
        result = BecomeUser.become_user(user, ["DEFAULT_GID"], self.config,
                                        self.LOG)
        self.assertTrue(result)
        BecomeUser.restore_id(self.config, self.LOG)


if __name__ == '__main__':
    unittest.main()
