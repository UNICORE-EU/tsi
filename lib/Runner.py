"""
Runs one processing event, reading from stdin and writing to stdout.
Binary data is encoded and transferred via the text streams.
"""

from TSI import assert_version, finish_setup, MY_VERSION, REQUIRED_VERSION, process, read_config_file
from Log import Logger
import BecomeUser, BSS, Connector
import sys

def main(argv=None):
    """
    Runs one-shot processing. Reads config, reads message and
    and launches the processing.
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
    LOG = Logger("UNICORE-TSI-run", verbose, use_syslog)
    LOG.info("Debug logging: %s" % verbose)
    config['tsi.switch_uid'] = False
    config['tsi.open_user_sessions'] = False
    finish_setup(config, LOG)
    bss = BSS.BSS()
    LOG.info("Starting TSI %s for %s" % (MY_VERSION, bss.get_variant()))
    BecomeUser.initialize(config, LOG)
    bss.init(config, LOG)
    config['tsi.bss'] = bss
    connector = Connector.StreamConnector(sys.stdin, sys.stdout, LOG)
    process(connector, config, LOG, one_shot=True)
    return 0


# application entry point
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)