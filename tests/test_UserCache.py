import unittest
import logging
import os
import pwd
import time
from lib import UserCache


class TestUserCache(unittest.TestCase):
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

    def getlogin(self):
        return pwd.getpwuid(os.getuid())[0]

    def test_user_cache(self):
        uc = UserCache.UserCache(2, self.LOG)
        user = self.getlogin()
        print("Getting info for the current user: %s" % user)
        gids = uc.get_gids_4user(user)
        uid = uc.get_uid_4user(user)
        home = uc.get_home_4user(user)
        print(" - uid %s" % uid)
        print(" - gids %s" % gids)
        print(" - home %s" % home)

        # check expiry
        time.sleep(2)
        self.assertTrue(uc.expired(uc.users_timestamps[user]))
        self.assertEqual(None, uc.groups_timestamps.get('root'))
        home = uc.get_home_4user(user)
        print(" - home %s" % home)
        self.assertFalse(uc.expired(uc.users_timestamps[user]))

        print("All members of the 'root' group: %s" % uc.get_members_4group(
            'root'))
        self.assertFalse(uc.expired(uc.groups_timestamps['root']))

        # how to deal with non-existing group
        print("All members of the non-existing 'foobarspam' group: %s" %
              uc.get_members_4group('foobarspam'))

        # how to deal with non-existing user
        print("Home for non-existing 'foobarspam' user: %s" %
              uc.get_home_4user('foobarspam'))


if __name__ == '__main__':
    unittest.main()
