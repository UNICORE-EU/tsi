"""
Batch system specific functions.

This is the "LoadLeveler" version, setup for BlueGene

Check the manual for advice on how to create a custom version.
"""

import re
from BSSCommon import BSSBase
from Utils import extract_parameter, extract_number

class BSS(BSSBase):

    def get_variant(self):
        return "LoadLeveler"

    defaults = {
        'tsi.submit_cmd': 'llsubmit',
        'tsi.qstat_cmd': 'llq -r %id %st %c',
        'tsi.details_cmd': 'llq -x -j',
        'tsi.abort_cmd': 'llcancel %s',
        'tsi.hold_cmd': 'llhold',
        'tsi.resume_cmd': 'llhold -r',
    }

    def create_submit_script(self, message, config, LOG):
        """ parse the #TSI_" BSS parameters from the message
        and convert them to the proper BSS instructions.
        Returns the script to submit to the BSS (as a list of lines)
        """
        submit_cmds = []

        email = extract_parameter(message, "EMAIL", "NONE")
        jobname = extract_parameter(message, "JOBNAME",
                                    config['tsi.default_job_name'])
        outcome_dir = extract_parameter(message, "OUTCOME_DIR")
        project = extract_parameter(message, "PROJECT", "NONE")
        stderr = extract_parameter(message, "STDERR", "stderr")
        stdout = extract_parameter(message, "STDOUT", "stdout")
        umask = extract_parameter(message, "UMASK")
        memory = extract_number(message, "MEMORY")
        nodes = extract_number(message, "NODES")
        queue = extract_parameter(message, "QUEUE", "NONE")
        reservation_id = extract_parameter(message,
                                           "RESERVATION_REFERENCE",
                                           "NONE")
        req_time = extract_number(message, "TIME")
        # BlueGene topology
        topology = extract_parameter(message, "SSR_TOPOLOGY", "Either")

        # first line is shell
        submit_cmds.append("#/bin/sh")

        # Jobname:
        # check that it fits the rules
        match = re.search(r"([a-zA-Z]\S{0,14})", jobname)
        if match is not None:
            jobname = match.group(1)
        else:
            jobname = "UNICORE_job"
        submit_cmds.append("# @ job_name = %s" % jobname)

        if queue != "NONE":
            submit_cmds.append("# @ class = %s" % queue)

        if project != "NONE":
            submit_cmds.append("# @ account_no = %s" % project)

        # Blue Gene stuff
        submit_cmds.append("# @ job_type = bluegene")
        submit_cmds.append("# @ bg_connectivity = %s" % topology)
        if memory >0:
            submit_cmds.append("# @ bg_requirements = (Memory>= %s)" % memory)
        if nodes >0:
            submit_cmds.append("# @ bg_size = %s" % nodes)

        # Job time requirement. Wallclock time in seconds.
        submit_cmds.append("# @ cpu_limit = %s" % req_time)

        if email != "NONE":
            submit_cmds.append("# @ notification = always")
            submit_cmds.append("# @ notify_user = %s" % email)

        if reservation_id != "NONE":
            submit_cmds.append("# @ ll_res_id = %s" % reservation_id)

        submit_cmds.append("# @ output = %s/%s" % (outcome_dir, stdout))
        submit_cmds.append("# @ error = %s/%s" % (outcome_dir, stderr))

        if umask is not None:
            submit_cmds.append("umask %s" % umask)

        submit_cmds.append("# @ comment = UNICORE")

        return submit_cmds

    def extract_job_id(self, submit_result):
        """ extracts the job ID after submission to the BSS """
        # expect 'llsubmit: The job "cluster.host.162588" has been submitted.",
        # extract the 'NNN'
        job_id = None
        m = re.search(r"\D*\.(\d+)\D*", submit_result)
        if m is not None:
            job_id = m.group(1)
        return job_id

    def extract_info(self, qstat_line):
        """ extracts the bssid, queue status and queue name """
        
        # Example output we expect:
        # (as defined by the default llq syntax above)
        #
        # node1c1.host.eu.267412.10!R!m001
        # node2c1.host.eu.123456.0!R!m002
        #
        # we only use the numerical part of the job ID,
        # minus the job step (last part '.NN')
        #
        # we want to extract the full job ID w/o the job step, the
        # state and the queue name
        
        match = re.search(r"\S+\.(\d+)\.\d+\!(\S+)!(\S+)", qstat_line)
        if match is None:
            return (None,None,None)
        bssid = match.group(1)
        state = match.group(2)
        queue_name = match.group(3)
        return (bssid, state, queue_name)

    def convert_status(self, bss_state):
        """ converts BSS status to UNICORE status """
        ustate = "UNKNOWN"
        if bss_state in ["I", "D", "P", "XP", "NQ"]:
            ustate = "QUEUED"
        elif bss_state in ["R", "E", "EP", "T", "V", "VP", "MP", "ST", "SX",
                       "CP", "CK"]:
            ustate = "RUNNING"
        elif bss_state in ["S", "H", "HS"]:
            ustate = "SUSPENDED"
        elif bss_state in ["C", "RM", "CA", "X", "TX", "NR"]:
            ustate = "COMPLETED"
        return ustate
    
