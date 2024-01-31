"""

Batch system specific functions,
this is the "LSF" version.

Check the manual for advice on how to create a custom version.
"""

import re
from BSSCommon import BSSBase
from Utils import extract_parameter, extract_number


class BSS(BSSBase):
    def get_variant(self):
        return "LSF"

    defaults = {
        'tsi.submit_cmd': 'bsub <',
        'tsi.qstat_cmd': 'bjobs -w -u all',
        'tsi.details_cmd': 'bjobs -l',
        'tsi.abort_cmd': 'bkill %s',
        'tsi.hold_cmd': 'bstop',
        'tsi.resume_cmd': 'bresume',
        'tsi.lsf.memory_conversion_factor': '1',
    }

    def init(self, config, LOG):
        BSSBase.init(self, config, LOG)
        submit_cmd = config.get('tsi.submit_cmd')
        if not submit_cmd.strip().endswith("<"):
            submit_cmd += " <"
            config['tsi.submit_cmd'] = submit_cmd

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
        umask = extract_parameter(message, "UMASK", "NONE")
        memory = extract_number(message, "MEMORY")
        nodes = extract_number(message, "NODES")
        processors_per_node = extract_number(message,
                                                "PROCESSORS_PER_NODE")
        total_processors = extract_number(message, "TOTAL_PROCESSORS")
        gpus = extract_parameter(message, "GPUS_PER_NODE", "NONE")    
        array_spec = extract_number(message, "ARRAY")
        array_limit = extract_number(message, "ARRAY_LIMIT")

        queue = extract_parameter(message, "QUEUE", "NONE")
        reservation_id = extract_parameter(message,
                                           "RESERVATION_REFERENCE",
                                           "NONE")
        req_time = extract_number(message, "TIME")

        lsf_memory_conversion_factor = config.get(
            'tsi.lsf.memory_conversion_factor')

        if email != "NONE":
            submit_cmds.append("#BSUB -B -N -u %s" % email)

        if queue != "NONE":
            submit_cmds.append("#BSUB -q %s" % queue)

        if project != "NONE":
            submit_cmds.append("#BSUB -P %s" % project)

        # LSF slots:
        # use total_processors or nodes*processors per node
        slots = 0
        if total_processors >0:
            slots = total_processors
        elif nodes >0 and processors_per_node >0:
            slots = nodes * processors_per_node
            submit_cmds.append("#BSUB -R \"span[ptile=%s]\"" % processors_per_node)

        if slots > 0:
            submit_cmds.append("#BSUB -n %s" % slots)

        # GPUs
        gpu_count = 0
        try:
            gpu_count = int(gpus)
        except:
            pass
        
        if gpu_count>0:
            submit_cmds.append("#BSUB -gpu \"num=%s:j_exclusive=yes\"" % gpu_count)

        # Wallclock time: LSF requires minutes
        if req_time != "NONE":
            time_in_minutes = int( int(req_time) / 60 )
            submit_cmds.append("#BSUB -W %s" % time_in_minutes)

        # Memory: LSF specifies a limit per process
        if memory != "NONE":
            if processors_per_node != "NONE":
                ppn = int(processors_per_node)
                memory = int(int(memory) / ppn)
                memory *= int(lsf_memory_conversion_factor)
                # submit_cmds.append("#BSUB -M %s" % memory)

        if reservation_id != "NONE":
            submit_cmds.append("#BSUB -U %s" % reservation_id)

        # Jobname: check that it fits the rules
        match = re.search(r"([a-zA-Z]\S{0,14})", jobname)
        if match is not None:
            jobname = match.group(1)
        else:
            jobname = "UNICORE_job"
                
        if array_spec >0:
            if array_limit >0:
                array_spec = "[" + str(array_spec) + "]" + "%" + str(array_limit)
            else:
                array_spec = "[" + str(array_spec) + "]"
            submit_cmds.append("#BSUB -J \"%s%s\"" % (jobname,array_spec));
            submit_cmds.append("UC_ARRAY_TASK_ID = \"$LSB_JOB_INDEX\"; export UC_ARRAY_TASK_ID");
            stdout = stdout + "%I"
            stderr = stderr + "%I"
        else:   
            submit_cmds.append("#BSUB -J %s" % jobname)

        submit_cmds.append("#BSUB -o %s/%s" % (outcome_dir, stdout))
        submit_cmds.append("#BSUB -e %s/%s" % (outcome_dir, stderr))

        if umask is not None:
            submit_cmds.append("umask %s" % umask)

        return submit_cmds


    def extract_info(self, qstat_line):
        """ extracts the bssid, queue status and queue name """
        # Example output we expect:
        # The output format of the interesting lines is:
        # xxxxxx user Status Queue ....
        #
        # Where xxxxx is the Job id, the number of junk fields is variable
        # Example:
        # JOBID USER STAT QUEUE FROM_HOST EXEC_HOST JOB_NAME SUBMIT_TIME
        # 1652  bob  DONE normal gridnode1  gridnode3   date Jun 19 12:45
        #
        # There may be also some uninteresting lines (not starting with a
        # numerical batch system id)
        match = re.search(r"^\s*(\d+)\s+\S+\s+(\w+)\s+(\w+)\.*", qstat_line)        
        if match is None:
            return (None,None,None)
        bssid = match.group(1)
        state = match.group(2)
        queue_name = match.group(3)
        return (bssid, state, queue_name)

    
    def convert_status(self, bss_state):
        """ converts BSS status to UNICORE status """
        ustate = "UNKNOWN"
        if bss_state in ["PEND", "WAIT", "ZOMBI"]:
            ustate = "QUEUED"
        elif bss_state in ["RUN", "POST_DONE", "POST_ERR"]:
            ustate = "RUNNING"
        elif bss_state in ["PSUSP", "USUSP", "SSUSP"]:
            ustate = "SUSPENDED"
        elif bss_state in ["DONE", "EXIT"]:
            ustate = "COMPLETED"
        return ustate
