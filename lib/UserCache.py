#
# Retrieves and caches various info about a user
# (groups, home dir, ...)
#
# The cache time is configurable
#
import time
import pwd
import grp
import Utils

class UserCache(object):

    def __init__(self, cache_ttl, LOG, use_id_to_resolve_groups = True):
        self.cache_ttl = cache_ttl
        self.LOG = LOG
        self.all_groups = {}
        self.uids = {}
        self.gids = {}
        self.homes = {}
        self.groups = {}
        self.users_timestamps = {}
        self.groups_timestamps = {}
        self.use_id_to_resolve_groups = use_id_to_resolve_groups
            
    def prepare_users(self, user):
        timestamp = self.users_timestamps.get(user)
        if self.expired(timestamp):
            self.update_user_info(user)
            if self.users_timestamps.get(user) is None:
                self.LOG.debug("Unknown user name requested: %s" % user)

    def prepare_groups(self, group):
        timestamp = self.groups_timestamps.get(group)
        if self.expired(timestamp):
            self.update_group_info(group)
        if self.groups_timestamps.get(group) is None:
            self.LOG.debug("Unknown group name requested: %s" % group)

    # checks if cache TTL is expired
    def expired(self, timestamp):
        return (timestamp is None) or (timestamp + self.cache_ttl < time.time())

    # retrieves all gids the username is member of
    def get_gids_4user(self, user):
        self.prepare_users(user)
        gids = self.all_groups.get(user)
        if gids is None:
            return []
        else:
            return gids

    # resolves the group name
    def get_gid_4group(self, group):
        self.prepare_groups(group)
        gid = self.groups.get(group)
        if gid is None:
            return -1
        else:
            return gid

    # returns primary gid for a username
    def get_gid_4user(self, user):
        self.prepare_users(user)
        gid = self.gids.get(user)
        if gid is None:
            return -1
        else:
            return gid

    # returns uid for a username
    def get_uid_4user(self, user):
        self.prepare_users(user)
        uid = self.uids.get(user)
        if uid is None:
            return -1
        else:
            return uid

    # returns home for a username
    def get_home_4user(self, user):
        self.prepare_users(user)
        return self.homes.get(user)

    # Establish the list of all (including supplementary) groups the user
    # is member of.
    # Arguments: user name and primary group id.
    def get_gids_4user_nc(self, user, gid, old_info = None):
        if self.use_id_to_resolve_groups:
            all_groups = self.get_gids_4user_via_id(user, gid)
        else:
            all_groups = self.get_gids_4user_via_getgrall(user, gid)
        if str(all_groups)!=str(old_info):
            self.LOG.debug("Updated groups list for the user %s : %s" % (
                user, str(all_groups)))
        return all_groups
    
    # implementation using grp.getgrall()
    def get_gids_4user_via_getgrall(self, user, gid):
        all_groups = [g.gr_gid for g in
                      filter(lambda g: user in g.gr_mem, grp.getgrall())]
        all_groups.append(gid)
        return all_groups

    # alternative implementation using 'id -G <user>'
    def get_gids_4user_via_id(self, user, gid):
        success, out = Utils.run_command("id -G %s" % user, login_shell=False)
        if not success:
            return []
        all_groups = [int(g) for g in out.split(" ")]
        if gid not in all_groups:
            all_groups.append(gid)
        return all_groups

    # Fills up all per group caches with a freshly obtained information
    # Argument: group name
    def update_group_info(self, group):
        self.groups[group] = None
        self.groups_timestamps[group] = None
        try:
            g = grp.getgrnam(group)
        except KeyError:
            return
        self.groups[group] = g.gr_gid
        self.groups_timestamps[group] = time.time()

    # Fills up all per user caches with freshly obtained information
    # Argument: user name
    def update_user_info(self, user):
        self.uids[user] = None
        self.gids[user] = None
        self.homes[user] = None
        old_group_info = self.all_groups.get(user, None)
        self.all_groups[user] = None
        self.users_timestamps[user] = None
        try:
            (_, _, uid, gid, _, home, _) = pwd.getpwnam(user)
        except KeyError:
            self.LOG.debug("No such user: %s" % user)
            return
        self.uids[user] = uid
        self.gids[user] = gid
        self.homes[user] = home
        self.all_groups[user] = self.get_gids_4user_nc(user, gid, old_group_info)
        self.users_timestamps[user] = time.time()