"""
Main TSI module, containing the main processing loop
"""

import os
import re
import socket
import sys
import ACL, BecomeUser, BSS, Connector, Log, PAM, Reservation, Server, SSL, IO, UFTP, Utils

#
# the TSI version
#
MY_VERSION = "__VERSION__"

# supported Python versions
REQUIRED_VERSION = (3, 6, 0)


def assert_version():
    """
    Checks that the Python version is correct
    """
    return sys.version_info >= REQUIRED_VERSION


def setup_defaults(config):
    """
    Sets some default values in the configuration
    """
    config['tsi.default_job_name'] = 'UnicoreJob'
    config['tsi.nodes_filter'] = ''
    config['tsi.userCacheTtl'] = 600
    config['tsi.enforce_os_gids'] = True
    config['tsi.fail_on_invalid_gids'] = False
    config['tsi.use_id_to_resolve_gids'] = True
    config['tsi.open_user_sessions'] = False
    config['tsi.debug'] = 0
    config['tsi.use_syslog'] = False
    config['tsi.worker.id'] = 1
    config['tsi.unicorex_machine'] = 'localhost'
    config['tsi.safe_dir'] = '/tmp'
    config['tsi.keyfiles'] = ['.ssh/authorized_keys']


def process_config_value(key, value, config):
    """
    Handles configuration values, checking for correctness
    and storing the appropriate settings in the config dictionary
    """
    boolean_keys = ['tsi.open_user_sessions',
            'tsi.switch_uid',
            'tsi.enforce_os_gids',
            'tsi.fail_on_invalid_gids',
            'tsi.use_id_to_resolve_gids',
            'tsi.use_syslog',
            'tsi.debug'
    ]
    for bool_key in boolean_keys:
        if bool_key == key:
            config[key] = value.lower() in ["1", "true"]
            return
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
        allowed_dns.append(dn)
        config['tsi.allowed_dns'] = allowed_dns
    elif key == "tsi.keyfiles":
        config["tsi.keyfiles"] = value.split(":")  
    elif key== "tsi.njs_machine":
        key="tsi_unicorex_machine"
    elif key== "tsi_njs_port":
        key="tsi_unicorex_port"
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
    machines = config.get('tsi.unicorex_machine', 'localhost').split(",")
    ips = []
    LOG.info("Allowed UNICORE/X machines: %s" % machines)
    for machine in machines:
        machine = machine.strip()
        try:
            ip = socket.gethostbyname(machine)
            ips.append(ip)
            LOG.info("Access allowed from %s (%s)" % (machine, ip))
        except:
            LOG.error("Could not resolve: '%s'" % machine)
    config['tsi.allowed_ips'] = ips

def setup_portrange(config, LOG):
    """
    Configures the (optional) range of local ports the TSI should use
    """
    rangespec = config.get("tsi.local_portrange", None)
    first = 0
    lower = -1
    upper = -1
    if rangespec is not None:
        try:
            lower,upper = rangespec.strip().split(":")
            lower = int(lower)
            upper = int(upper)
            if upper<=lower:
                raise Exception()
            first = lower
            LOG.info("Local port range used by TSI: %s - %s" % (lower, upper))
        except:
            raise Exception("Invalid 'tsi.local_portrange' specified, must be 'lower:upper'")
    config["tsi.local_portrange"] = (first, lower, upper)
      

def read_config_file(file_name):
    """
    Read config properties file, check values, and return
    a dictionary with the configuration.
    Parameters: file_name, LOG logger object
    Returns: a dictionary with config values
    """
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
            process_config_value(key, value, config)
    return config


def finish_setup(config, LOG):
    setup_acl(config, LOG)
    setup_allowed_ips(config, LOG)
    setup_portrange(config, LOG)


def ping(message, connector, config, LOG):
    """ Returns TSI version."""
    connector.write_message(MY_VERSION)


def ping_uid(message, connector, config, LOG):
    """ Returns TSI version and process' UID. Used for unit testing."""
    connector.write_message(MY_VERSION)
    connector.write_message(" running as UID [%s]" % config.get('tsi.effective_uid', "n/a"))


def get_user_info(message, connector, config, LOG):
    id_info = re.search(r".*#TSI_IDENTITY (\S+) (\S+)\n.*", message, re.M)
    if id_info is None:
        connector.failed("No user/group info given")
        return
    user = id_info.group(1)
    user_cache = config['tsi.user_cache']
    home = user_cache.get_home_4user(user)
    if home is None:
        connector.failed("No home directory found for user %s", user)
        return
    status = ""
    response = "home: %s\n" % home
    i = 0
    for keyfile in config['tsi.keyfiles']:
        _file = os.path.join(home, keyfile)
        try:
            with open(_file, "r") as f:
                status += " keyfile %s : OK" % _file
                for line in f.readlines():
                    if line.startswith("#"):
                        continue
                    response+="Accepted key %d: %s\n" % (i, line.strip())
                    i+=1
        except Exception as e:
            status += " keyfile %s : %s" % (_file, str(e))
    response += "status: %s\n" % status
    connector.write_message(response)


def execute_script(message, connector, config, LOG):
    """ Executes a script. If the script contains a line
    #TSI_DISCARD_OUTPUT true
    the output is discarded, otherwise it is returned to UNICORE/X.
    """
    discard = "#TSI_DISCARD_OUTPUT true\n" in message
    children = config.get('tsi.NOBATCH.children', None)
    (success, output) = Utils.run_command(message, discard, children)
    if success:
        connector.ok(output)
    else:
        connector.failed(output)

def start_forwarding(message, forwarder, config, LOG):
    """ starts forwarding threads """
    forwarder.start_forwarding()


def init_functions(bss):
    """
    Creates the function lookup table used to map UNICORE/X commands
    ('#TSI_...') to the appropriate TSI function.
    """
    return {
        "TSI_PING": ping,
        "TSI_PING_UID": ping_uid,
        "TSI_GET_USER_INFO": get_user_info,
        "TSI_EXECUTESCRIPT": execute_script,
        "TSI_GETFILECHUNK": IO.get_file_chunk,
        "TSI_PUTFILECHUNK": IO.put_file_chunk,
        "TSI_LS": IO.ls,
        "TSI_DF": IO.df,
        "TSI_UFTP": UFTP.uftp,
        "TSI_SUBMIT": bss.submit,
        "TSI_GETSTATUSLISTING": bss.get_status_listing,
        "TSI_GETPROCESSLISTING": bss.get_process_listing,
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


def handle_function(function, command, message, connector, config, LOG):
    switch_uid = config.get('tsi.switch_uid', True)
    pam_enabled = config.get('tsi.open_user_sessions', False)
    cmd_spawns = command in [ "TSI_EXECUTESCRIPT", "TSI_SUBMIT", "TSI_UFTP" ]
    open_user_session = pam_enabled and cmd_spawns and switch_uid
    if open_user_session and command!="_START_FORWARDING":
        # fork to avoid TSI process getting put into user slice
        pid = os.fork()
        if pid != 0:
            os.waitpid(pid, 0)
            return
    try:
        if switch_uid:
            id_info = re.search(r".*#TSI_IDENTITY (\S+) (\S+)\n.*", message, re.M)
            if id_info is None:
                raise RuntimeError("No user/group info given")
            user = id_info.group(1)
            groups = id_info.group(2).split(":")
            if open_user_session:
                pam_module = config.get('tsi.pam_module', "unicore-tsi")
                pam_session = PAM.PAM(LOG, module_name=pam_module)
                pam_session.open_session(user)
            user_switch_status = BecomeUser.become_user(user, groups, config, LOG)
            if user_switch_status is not True:
                raise RuntimeError(user_switch_status)
        function(message, connector, config, LOG)
    except:
        connector.failed(str(sys.exc_info()[1]))
        LOG.error("Error executing %s" % command)
    if switch_uid and command!="_START_FORWARDING":
        BecomeUser.restore_id(config, LOG)
        if open_user_session:
            pam_session.close_session()
    if open_user_session:
        os._exit(0)


def process(connector, config, LOG):
    """
    Main processing loop. Reads commands from control_in and invokes the
    appropriate command.

        Arguments:
          connector: connection to the UNICORE/X
          config: TSI configuration (dictionary)
          LOG: logger object
    """

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
        # check for command and invoke appropriate function
        command = None
        function = None
        for cmd in functions:
            have_cmd = re.search(r".*#%s\n" % cmd, message, re.M)
            if have_cmd:
                command = cmd
                function = functions.get(cmd)
                break
        
        if function is None:
            connector.failed("Unknown command %s" % command)
        elif "TSI_PING" == command:
            connector.write_message(MY_VERSION)
        else:
            handle_function(function, command, message, connector, config, LOG)
        # terminate the current "transaction" with UNICORE/X
        connector.write_message("ENDOFMESSAGE")


def main(argv=None):
    """
    Start the TSI. Read config, init UNICORE/X connection
    and start processing
    """
    if not assert_version():
        raise RuntimeError("Unsupported version of Python! "
                           "Must be %s or later." % str(REQUIRED_VERSION))
    if argv is None:
        argv = sys.argv
    if len(argv) < 2:
        raise RuntimeError("Please specify the config file!")
    config_file = argv[1]
    config = read_config_file(config_file)
    verbose = config['tsi.debug']
    use_syslog = config['tsi.use_syslog']
    LOG = Log.Logger("TSI-main", verbose, use_syslog)
    LOG.info("Debug logging: %s" % verbose)
    LOG.info("Opening PAM sessions for user tasks: %s" % config['tsi.open_user_sessions'])
    finish_setup(config, LOG)
    bss = BSS.BSS()
    LOG.info("Starting TSI %s for %s" % (MY_VERSION, bss.get_variant()))
    BecomeUser.initialize(config, LOG)
    os.chdir(config.get('tsi.safe_dir','/tmp'))
    bss.init(config, LOG)
    config['tsi.bss'] = bss
    (socket1, socket2, msg) = Server.connect(config, LOG)
    number = config.get('tsi.worker.id', 1)
    if msg==None:
        LOG.reinit("TSI-worker", verbose, use_syslog)
        LOG.info("Worker %s started." % str(number))
        connector = Connector.Connector(socket1, socket2, LOG)
        process(connector, config, LOG)
    else:
        LOG.reinit("TSI-port-forwarding", verbose, use_syslog)
        LOG.info("Port forwarder worker %s started." % str(number))
        forwarder = Connector.Forwarder(socket1, msg, config, LOG)
        handle_function(start_forwarding, "_START_FORWARDING", msg, forwarder, config, LOG)
    return 0


# application entry point
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
