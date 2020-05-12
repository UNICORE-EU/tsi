"""
Main TSI module, containing the main processing loop and several utility
methods.

It handles the TSI_PING and TSI_EXECUTESCRIPT commands
"""

import logging
import logging.config
import os
import re
import socket
import sys
import ACL, BecomeUser, BSS, Connector, Local, Reservation, Server, SSL, IO, Utils

#
# the TSI version
#
MY_VERSION = "__VERSION__"

# supported Python versions
REQUIRED_VERSION = (2, 7, 5)
REQUIRED_VERSION_3 = (3, 4, 0)


def assert_version():
    """
    Checks that the Python version is correct.
    Returns True if version is 2.7.6 or later
    """
    ver = sys.version_info
    if Utils.have_p3:
        return ver >= REQUIRED_VERSION_3
    else:
        return ver >= REQUIRED_VERSION


def get_startup_logger():
    """ Logger used during the startup phase - will log to stdout """
    LOG = logging.getLogger("tsi.startup")
    LOG.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    LOG.handlers = [ch]
    return LOG


def get_worker_logger(config):
    """
    Logger used by a TSI worker
    """
    number = config.get('tsi.worker.id', 1)
    return logging.getLogger("tsi.worker." + str(number))


def read_logging_config(config, LOG):
    """ Read logging subsystem config from file """
    log_config = config.get('tsi.logging_configuration', None)
    if log_config is None:
        LOG.info("No logging configuration set, continuing to log to console.")
    else:
        LOG.info("Reading logging configuration from %s " % log_config)
        from ast import literal_eval
        with open(log_config, 'r') as infile:
            configuration = literal_eval(infile.read())
            if type(configuration) is dict:
                logging.config.dictConfig(configuration)
            else:
                logging.config.fileConfig(log_config)


def setup_defaults(config):
    """
    Sets some default values in the configuration
    """
    config['tsi.default_job_name'] = 'UnicoreJob'
    config['tsi.nodes_filter'] = ''
    config['tsi.logfacility'] = 'LOG_USER'
    config['tsi.loghost'] = ''
    config['tsi.userCacheTtl'] = 600
    config['tsi.enforce_os_gids'] = True
    config['tsi.fail_on_invalid_gids'] = False
    config['tsi.use_id_to_resolve_gids'] = False
    config['tsi.debug'] = 0
    config['tsi.worker.id'] = 1
    config['tsi.njs_machine'] = 'localhost'
    config['tsi.safe_dir'] = '/tmp'

def process_config_value(key, value, config, LOG):
    """
    Handles configuration values, checking for correctness
    and storing the appropriate settings in the config dictionary
    """
    boolean_keys = ['tsi.enforce_os_gids',
            'tsi.fail_on_invalid_gids',
            'tsi.use_id_to_resolve_gids'
    ]
    for bool_key in boolean_keys:
        if bool_key == key:
            if 'true' == value:
                config[key] = True
            elif 'false' == value:
                config[key] = False
            else:
                raise KeyError("Invalid value '%s' for parameter '%s', "
                               "must be 'true' or 'false'" % (value, key))

    if key.startswith('tsi.acl'):
        if 'NONE' == value or 'POSIX' == value or 'NFS' == value:
            path = key[8:]
            acl = config.get('tsi.acl', {})
            acl[path] = value
            config['tsi.acl'] = acl
        else:
            raise KeyError("Invalid value '%s' for parameter '%s', "
                           "must be 'NONE', 'POSIX' or 'NFS'" % (value, key))
    elif key.startswith('tsi.allowed_dn.'):
        allowed_dns = config.get('tsi.allowed_dns', [])
        dn = SSL.convert_dn(value)
        LOG.info("Allowing SSL connections for %s" % value)
        allowed_dns.append(dn)
        config['tsi.allowed_dns'] = allowed_dns
    else:
        config[key] = value


def setup_acl(config, LOG):
    """
    Configures the ACL settings
    """
    if config.get('tsi.getfacl_cmd') is not None and config.get(
            'tsi.setfacl_cmd') is not None:
        config['tsi.posixacl_enabled'] = True
    else:
        config['tsi.posixacl_enabled'] = False
        LOG.info("POSIX ACL support disabled (commands not configured)")

    if config.get('tsi.nfs_getfacl_cmd') is not None and config.get(
            'tsi.nfs_setfacl_cmd') is not None:
        config['tsi.nfsacl_enabled'] = True
    else:
        config['tsi.nfsacl_enabled'] = False
        LOG.info("NFS ACL support disabled (commands not configured)")


def setup_allowed_ips(config, LOG):
    """
    Configures IP addresses of UNICORE/X servers allowed to connect
    """
    machines = config.get('tsi.njs_machine', 'localhost').split(",")
    ips = []
    LOG.info("Allowed UNICORE/X machines: %s" % machines)
    for machine in machines:
        try:
            ip = socket.gethostbyname(machine)
            ips.append(ip)
            LOG.info("Access allowed from %s (%s)" % (machine, ip))
        except:
            LOG.error("Could not resolve: '%s'" % machine)
    config['tsi.allowed_ips'] = ips


def read_config_file(file_name, LOG):
    """
    Read config properties file, check values, and return
    a dictionary with the configuration.
    Parameters: file_name, LOG logger object
    Returns: a dictionary with config values
    """
    LOG.info("Reading config from %s" % file_name)
    with open(file_name, "r") as f:
        lines = f.readlines()

    config = {}
    setup_defaults(config)

    for line in lines:
        # only process lines of the form key=value
        match = re.match(r"\s*([a-zA-Z0-9.\-_/]+)\s*=\s*(.+)$", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            process_config_value(key, value, config, LOG)

    setup_acl(config, LOG)
    setup_allowed_ips(config, LOG)
    return config


# invoked for TSI_PING
def ping(message, connector, config, LOG):
    """ Returns TSI version."""
    connector.write_message(MY_VERSION)


# invoked for TSI_PING_UID (useful mainly for unit testing)
def ping_uid(message, connector, config, LOG):
    """ Returns TSI version and process' UID. Used for unit testing."""
    connector.write_message(MY_VERSION)
    connector.write_message(
        " running as UID [%s]" % config.get('tsi.effective_uid', "n/a"))


# invoked for TSI_EXECUTESCRIPT
def execute_script(message, connector, config, LOG):
    """ Executes a script. If the script contains a line
    #TSI_DISCARD_OUTPUT true
    the output is discarded, otherwise it is returned to the XNJS.
    """
    discard = "#TSI_DISCARD_OUTPUT true\n" in message
    children = config.get('tsi.NOBATCH.children', None)
    (success, output) = Utils.run_command(message, discard, children)
    if success:
        connector.ok(output)
    else:
        connector.failed(output)


# setup the table of supported TSI commands.
# The commands must have a specific signature, see e.g. execute_script()
def init_functions(bss):
    """
    Creates the function lookup table used to map XNJS commands '#TSI_...' to
    the appropriate TSI function.
    """
    return {
        "TSI_PING": ping,
        "TSI_PING_UID": ping_uid,
        "TSI_EXECUTESCRIPT": execute_script,
        "TSI_GETFILECHUNK": IO.get_file_chunk,
        "TSI_PUTFILECHUNK": IO.put_file_chunk,
        "TSI_LS": IO.ls,
        "TSI_DF": IO.df,
        "TSI_SUBMIT": bss.submit,
        "TSI_GETSTATUSLISTING": bss.get_status_listing,
        "TSI_GETJOBDETAILS": bss.get_job_details,
        "TSI_ABORTJOB": bss.abort_job,
        "TSI_HOLDJOB": bss.hold_job,
        "TSI_RESUMEJOB": bss.resume_job,
        "TSI_GET_COMPUTE_BUDGET": bss.get_budget,
        "TSI_MAKE_RESERVATION": Reservation.make_reservation,
        "TSI_QUERY_RESERVATION": Reservation.query_reservation,
        "TSI_CANCEL_RESERVATION": Reservation.cancel_reservation,
        "TSI_FILE_ACL": ACL.process_acl,
    }


def process(connector, config, LOG):
    """
    Main processing loop. Reads commands from control_in and invokes the
    appropriate command.

        Arguments:
          connector: connection to the UNICORE/X
          config: TSI configuration (dictionary)
          LOG: logger object
    """

    setting_uids = config.get('tsi.switch_uid', True)
    my_umask = os.umask(0o22)
    os.umask(my_umask)
    bss = config.get('tsi.bss', BSS.BSS())
    functions = init_functions(bss)

    # read message from control
    first = True
    while True:
        if config.get('tsi.testing', False) and not first:
            LOG.info("Testing mode, exiting main loop")
            break
        first = False
        try:
            message = Utils.encode(connector.read_message())
        except IOError:
            LOG.info("Peer shutdown, exiting")
            connector.close()
            return

        os.chdir(config.get('tsi.safe_dir','/tmp'))
        do_set_uid = setting_uids
        # check for command and invoke appropriate function
        legal_cmd = False
        session_info = None
        for cmd in functions:
            have_cmd = re.search(r".*#%s\n" % cmd, message, re.M)
            if have_cmd:
                function = functions.get(cmd)
                legal_cmd = True
                if "TSI_PING" == cmd:
                    do_set_uid = False
                try:
                    if do_set_uid:
                        id_info = re.search(r".*#TSI_IDENTITY (\S+) (\S+)\n.*",
                                            message, re.M)
                        if id_info is None:
                            raise RuntimeError("No user/group info given")
                        user = id_info.group(1)
                        groups = id_info.group(2).split(":")
                        session_info = Local.pre_become_user(user, config, LOG)
                        user_switch_status = BecomeUser.become_user(user, groups, config, LOG)
                        if user_switch_status is not True:
                            raise RuntimeError(user_switch_status)
                        Local.post_become_user(session_info, config, LOG)
                    function(Utils.encode(message), connector, config, LOG)
                except:
                    connector.failed(str(sys.exc_info()[1]))
                    # log exception info and stacktrace
                    LOG.exception("Error executing %s" % cmd)
                break

        if not legal_cmd:
            LOG.info("Unknown command!")
            connector.failed("Unknown command")

        # finally reset user ID
        if do_set_uid:
            Local.cleanup(session_info, config, LOG)
            BecomeUser.restore_id(config, LOG)

        # and terminate the current "transaction" with the XNJS
        connector.write_message("ENDOFMESSAGE")
    

def main(argv=None):
    """
    Start the TSI. Read config, init XNJS connection
    and start processing
    """
    if not assert_version():
        raise RuntimeError("Unsupported version of Python! "
                           "Must be %s or later." % str(REQUIRED_VERSION))
    LOG = get_startup_logger()
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        raise RuntimeError("Please specify the config file!")
    config_file = argv[1]
    config = read_config_file(config_file, LOG)
    bss = BSS.BSS()
    LOG.info("Starting TSI for " + bss.get_variant())
    read_logging_config(config, LOG)
    LOG = logging.getLogger("tsi.main")
    BecomeUser.initialize(config, LOG)
    os.chdir(config.get('tsi.safe_dir','/tmp'))
    bss.init(config, LOG)
    config['tsi.bss'] = bss
    (command, data) = Server.connect(config, LOG)
    LOG = get_worker_logger(config)
    LOG.info("Worker started.")
    connector = Connector.Connector(command, data, LOG)
    process(connector, config, LOG)
    return 0


# application entry point
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
