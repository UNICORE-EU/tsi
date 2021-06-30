"""

Batch system specific functions,
this is the "NOBATCH" version.

Check the manual for advice on how to create a custom version.
"""

from time import time
import re
import os
import subprocess
from BSSCommon import BSSBase
import Utils


class BSS(BSSBase):
    def get_variant(self):
        return "NOBATCH"

    def submit(self, message, connector, config, LOG):
        """Submit a script, which for NOBATCH means fork a child process to
        execute the script.
        The message must be unicode.
        The message is scanned for the following values
        TSI_SCRIPT   - the script to run
        TSI_OUTCOME_DIR
        TSI_USPACE_DIR
        TSI_STDOUT
        TSI_STDERR
        TSI_JOBNAME
        TSI_TIME
        TSI_MEMORY
        """
        self.cleanup(config)

        children = config.get('tsi.NOBATCH.children')

        LOG.debug("Submitting a script.")
        message = Utils.expand_variables(message)

        outcome_dir = Utils.extract_parameter(message, "OUTCOME_DIR")
        uspace_dir = Utils.extract_parameter(message, "USPACE_DIR")
        stdout = Utils.extract_parameter(message, "STDOUT")
        stderr = Utils.extract_parameter(message, "STDERR")
        req_time = Utils.extract_number(message, "TIME")
        memory = Utils.extract_number(message, "MEMORY")

        # setup time and memory limits (if given)
        ulimits = ""
        timeoutcmd = ""
        if req_time >0:
            # limit wall time
            grace = 0.01 * req_time
            timeoutcmd = "timeout -k %d %s" % (grace, req_time)
            # CPU time can be limited in addition. However, this may lead
            # to job abortion before reaching the wall time limit,
            # e.g. when multiple threads are used on multiple cores.
            #
            # ulimits = ulimits + "ulimit -t %req_time; " % req_time

        if memory >0:
            # limit virtual memory
            real_mem = 1024 * memory  # MB -> KB
            ulimits = "ulimit -v %d;" % real_mem

        # add the following amount to the child process' niceness
        nice = 100

        # on systems that support it, "ionice" can be useful to
        # reduce the I/O load on the TSI frontend
        # see "man ionice"
        ionice = "ionice -c 3"

        os.chdir(uspace_dir)

        if not os.path.exists(outcome_dir):
            os.mkdir(outcome_dir)

        Utils.addperms(outcome_dir, 0o700)

        # create a unique Job ID which will be visible
        # using the 'ps' later, see get_status_listing()
        job_id = str(os.getpid()) + str(int(time() * 1000))[5:]
        cmds_file_name = "UNICORE_Job_%s" % job_id

        # Write the commands to a file
        with open(cmds_file_name, "w") as cmds:
            cmds.write(message)
        Utils.addperms(cmds_file_name, 0o700)
        cmd = "%s %s nice -n %s %s ./%s > %s/%s 2> %s/%s" % (
            ulimits, ionice, nice, timeoutcmd, cmds_file_name, outcome_dir,
            stdout, outcome_dir, stderr)
        LOG.debug("Running: %s" % cmd)
        # fork a child to run the command
        child = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        # remember child to be able to clean up processes later
        children.append(child)
        connector.write_message(job_id)

    def extract_info(self, qstat_line):
        """ extracts the bssid, queue status and queue name """
        match = re.search(r"(\w) .*UNICORE_Job_(\d+).*", qstat_line)
        if match is None:
            return (None,None,None)
        bssid = match.group(2)
        state = match.group(1)
        queue_name = "NOBATCH"
        return (bssid, state, queue_name)

    def convert_status(self, bss_state):
        """ converts BSS status to UNICORE status """
        if bss_state == "T":
            ustate = "SUSPENDED"
        else:
            ustate = "RUNNING"
        return ustate

    def get_job_details(self, message, connector, config, LOG):
        # for nobatch, there is nothing to report
        bssid = Utils.extract_parameter(message, "BSSID")
        output = "No info available for job %s \n" % bssid
        connector.ok(output)

    def hold_job(self, message, connector, config, LOG):
        # for nobatch, there is nothing to do
        connector.ok("\n")

    def resume_job(self, message, connector, config, LOG):
        # for nobatch, there is nothing to do
        connector.ok("\n")

