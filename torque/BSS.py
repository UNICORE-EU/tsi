"""

batch system specific functions.

This is the "Torque" version.

Check the manual for advice on how to create a custom version.
"""

import re
from BSSCommon import BSSBase
from Utils import extract_parameter, extract_number


class BSS(BSSBase):
    def get_variant(self):
        return "Torque"

    defaults = {
        'tsi.submit_cmd': 'qsub',
        'tsi.qstat_cmd': 'qstat -a',
        'tsi.details_cmd': 'qstat -f',
        'tsi.abort_cmd': 'qdel %s',
        'tsi.hold_cmd': 'qhold',
        'tsi.resume_cmd': 'qrls',
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
        uspace_dir = extract_parameter(message, "USPACE_DIR")
        nodes = extract_number(message, "NODES")
 
        nodes_filter = config.get("tsi.nodes_filter", "")
        if nodes_filter != "":
            nodes_filter = ":" + nodes_filter
            user_nodes_filter = extract_parameter(message,
                                                  "BSS_NODES_FILTER", "NONE")
            if user_nodes_filter != "NONE":
                nodes_filter = nodes_filter + ":" + user_nodes_filter

        processors = extract_number(message, "PROCESSORS")
        processors_per_node = extract_number(message,
                                                "PROCESSORS_PER_NODE")
        total_processors = extract_number(message, "TOTAL_PROCESSORS")
        array_spec = extract_number(message, "ARRAY")
        array_limit = extract_number(message, "ARRAY_LIMIT")

        queue = extract_parameter(message, "QUEUE", "NONE")
        reservation_id = extract_parameter(message,
                                           "RESERVATION_REFERENCE",
                                           "NONE")
        req_time = extract_number(message, "TIME")

        # Jobname:
        # check that it fits the rules
        match = re.search(r"([a-zA-Z]\S{0,14})", jobname)
        if match is not None:
            jobname = match.group(1)
        else:
            jobname = "UNICORE_job"
        submit_cmds.append("#PBS -N %s" % jobname)

        if queue != "NONE":
            submit_cmds.append("#PBS -q %s" % queue)

        if project != "NONE":
            submit_cmds.append("#PBS -A %s" % project)

        # Nodes / CPUs
        if nodes > 0:
            submit_cmds.append("#PBS -l nodes=%s:ppn=%s%s" % (
                nodes, processors_per_node, nodes_filter))
        
        if req_time > 0:
            # Job time requirement. Wallclock time in seconds.
            submit_cmds.append("#PBS -l walltime=%s" % req_time)

        if email == "NONE":
            email = "n"
        else:
            email = "abe -M %s" % email
        submit_cmds.append("#PBS -m %s" % email)

        if reservation_id != "NONE":
            submit_cmds.append("#PBS -W x=FLAGS:ADVRES:%s" % reservation_id)

        if array_spec >0:
            if array_limit>0:
                array_spec = str(array_spec) + "%" + str(array_limit)
            submit_cmds.append("#PBS -t %s" % array_spec);
            submit_cmds.append("UC_ARRAY_TASK_ID = \"$PBS_ARRAYID\"; export UC_ARRAY_TASK_ID");
            stdout = stdout + "$PBS_ARRAYID"
            stderr = stderr + "$PBS_ARRAYID"

        submit_cmds.append("#PBS -o %s/%s" % (outcome_dir, stdout))
        submit_cmds.append("#PBS -e %s/%s" % (outcome_dir, stderr))

        submit_cmds.append("#PBS -d %s" % uspace_dir)

        if umask is not None:
            submit_cmds.append("#PBS -W umask=%s" % umask)

        return submit_cmds

    def extract_info(self, qstat_line):
        """ extracts the bssid, queue status and queue name """

        # Example output we expect:
        #
        # host.juelich.de:
        #                                                                    Req'd  Req'd   Elap
        # Job ID               Username Queue    Jobname    SessID NDS   TSK Memory Time  S Time
        # -------------------- -------- -------- ---------- ------ ----- --- ------ ----- - -----
        # host.juelich.de jdoe    batch    New_Script  16522     1  -- 1000mb 00:00 C 00:00
                    
        match = re.search(
            r"\s*(\d+)\.\S+\s+\S+\s+"
            r"(\S+)\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+([CEHQRTWS]+)"
            r"\s+\S+", qstat_line)        
        if match is None:
            return (None,None,None)
        bssid = match.group(1)
        state = match.group(3)
        queue_name = match.group(2)
        return (bssid, state, queue_name)

    def convert_status(self, bss_state):
        """ converts BSS status to UNICORE status """
        ustate = "UNKNOWN"

        # Torque returns on of these states:
        #
        #   C -  Job is completed after having run
        #   E -  Job is exiting after having run.
        #   H -  Job is held.
        #   Q -  job is queued, eligible to run or routed.
        #   R -  job is running.
        #   T -  job is being moved to new location.
        #   W -  job is waiting for its execution time
        #        (-a option) to be reached.

        if bss_state in ["Q", "T", "W"]:
            ustate = "QUEUED"
        elif bss_state in ["E", "R"]:
            ustate = "RUNNING"
        elif bss_state in ["S", "H"]:
            ustate = "SUSPENDED"
        elif bss_state == "C":
            ustate = "COMPLETED"

        return ustate
