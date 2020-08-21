"""Batch system specific functions:
   - submit jobs
   - get status listing
   - control jobs (abort, hold, resume, get details, ...)

This is the "Slurm" version.

Check the manual for advice on how to create a custom version.
"""

import re
from BSSCommon import BSSBase
from Utils import extract_parameter, extract_number


class BSS(BSSBase):
    def get_variant(self):
        return "Slurm"

    defaults = {
        'tsi.submit_cmd': 'sbatch',
        'tsi.qstat_cmd': 'squeue -h -o \"%i %T %P\"',
        'tsi.details_cmd': 'scontrol show jobid',
        'tsi.abort_cmd': 'scancel %s',
        'tsi.hold_cmd': 'scontrol hold',
        'tsi.resume_cmd': 'scontrol release',
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

        memory = extract_number(message, "MEMORY")
        nodes = extract_number(message, "NODES")
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

        nodes_filter = config.get("tsi.nodes_filter", "")
        user_nodes_filter = extract_parameter(message,
                                              "BSS_NODES_FILTER", "NONE")
        
        qos = extract_parameter(message, "QOS", "NONE")

        # first line has to be the shell
        submit_cmds.append("#!/bin/bash")

        # jobname: check for illegal characters
        m = re.search(r"[^0-9a-zA-Z\.:.=~/]", jobname)
        if m is not None:
            jobname = "UNICORE_job"
        submit_cmds.append("#SBATCH --job-name=%s" % jobname)

        if queue != "NONE":
            submit_cmds.append("#SBATCH --partition=%s" % queue)

        if project != "NONE":
            submit_cmds.append("#SBATCH --account=%s" % project)

        # nodes count
        if nodes >0:
            # Multiple node and/or processors
            submit_cmds.append("#SBATCH --nodes=%s" % nodes)
            if processors_per_node >0:
                submit_cmds.append(
                    "#SBATCH --ntasks-per-node=%s" % processors_per_node)
        else:
            # request tasks and let Slurm figure out the nodes
            if total_processors > 0:
                submit_cmds.append("#SBATCH --ntasks=%s" % total_processors)
            
        # nodes filter, can be both global and user defined
        if user_nodes_filter != "NONE":
            if nodes_filter != "":
                nodes_filter = nodes_filter + "&" + user_nodes_filter
            else:
                nodes_filter =  user_nodes_filter
        if nodes_filter != "":
            submit_cmds.append("#SBATCH --constraint=%s" % nodes_filter)

        if qos != "NONE":
            submit_cmds.append("#SBATCH --qos=%s" % qos)
        
        if memory >= 0:
            # memory per node, '0' means that the job requests all of the memory on each node
            submit_cmds.append("#SBATCH --mem=%s" % memory)

        if req_time > 0:
            # wall time. Convert to minutes, as accepted by SLURM
            time_in_minutes = req_time / 60
            submit_cmds.append("#SBATCH --time=%d" % time_in_minutes)

        if email != "NONE":
            submit_cmds.append("#SBATCH --mail-user=%s" % email)
            submit_cmds.append("#SBATCH --mail-type=ALL")

        if reservation_id != "NONE":
            submit_cmds.append("#SBATCH --reservation=%s" % reservation_id)

        if array_spec > 0:
            if array_limit > 0:
                array_spec = str(array_spec) + "%" + str(array_limit)
            submit_cmds.append("#SBATCH --array=%s" % array_spec);
            submit_cmds.append("UC_ARRAY_TASK_ID = \"$SLURM_ARRAY_TASK_ID\"; export UC_ARRAY_TASK_ID");
            stdout = stdout + "%a"
            stderr = stderr + "%a"

        submit_cmds.append("#SBATCH --output=%s/%s" % (outcome_dir, stdout))
        submit_cmds.append("#SBATCH --error=%s/%s" % (outcome_dir, stderr))

        submit_cmds.append("#SBATCH --chdir=%s" % uspace_dir)

        if umask is not None:
            submit_cmds.append("umask %s" % umask)

        return submit_cmds

    def get_extract_id_expr(self):
        """ regular expression for extracting the job ID after batch submit """
        return r"Submitted\D*(\d+)\D*"

    def extract_info(self, qstat_line):
        """ extracts the bssid, queue status and queue name
        Using the default command 'squeue -h -o "%i %T %P", we expect the
        output to be: <jobID> <state> <partition>", e.g
        
        182027 PENDING large
        182197 PENDING normal
        182580 RUNNING large
        177070_0 RUNNING large
        177070_1 RUNNING large
        177071_[0-99] PENDING small
        """
        match = re.match(r"(\d+)_?\S*\s+(\w+)\s+(\w+)", qstat_line)
        if match is None:
            return (None,None,None)
        bssid = match.group(1)
        state = match.group(2)
        queue_name = match.group(3)
        return (bssid, state, queue_name)
    
    # Map Slurm job states to UNICORE states
    decoder = {
        'CANCELLED': 'COMPLETED',
        'COMPLETED': 'COMPLETED',
        'CONFIGURING': 'QUEUED',
        'COMPLETING': 'RUNNING',
        'FAILED': 'COMPLETED',
        'NODE_FAIL': 'UNKNOWN',
        'PENDING': 'QUEUED',
        'PREEMPTED': 'SUSPENDED',
        'RUNNING': 'RUNNING',
        'SUSPENDED': 'SUSPENDED',
        'TIMEOUT': 'UNKNOWN',
    }

    def convert_status(self, bss_state):
        """ converts BSS status to UNICORE status """
        return self.decoder.get(bss_state, "UNKNOWN")
