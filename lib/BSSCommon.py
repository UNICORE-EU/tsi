from time import time
import re
import os
import Quota
import Utils
from abc import ABCMeta


class BSSBase(object):
    """Base class for batch system specific functions:
        - submit jobs
        - get status listing
        - parse the status listing
        - job control (abort, hold, resume, get details, ...)
        - get a process list (via 'ps -e')

    Check the manual for advice on how to create a custom version.
    """

    __metaclass__ = ABCMeta

    def get_variant(self):
        return "<base>"

    def cleanup(self, config):
        """ cleanup child processes """
        children = config.get('tsi.NOBATCH.children')
        for child in children:
            return_code = child.poll()
            if return_code is not None:
                children.remove(child)

    defaults = {
        'tsi.qstat_cmd': 'ps -e -os,args',
        'tsi.abort_cmd': 'SID=$(ps -e -osid,args | grep "nice .* ./UNICORE_Job_%s" | grep -v "grep " | egrep -o "^\s*([0-9]+)" ); pkill -SIGTERM -s $SID',
        'tsi.get_processes_cmd': 'ps -e'
    }

    def init(self, config, LOG):
        """ setup default commands if necessary """
        defs = BSSBase.defaults
        defs.update(self.defaults)
        for key in defs:
            if config.get(key) is None:
                value = defs[key]
                config[key] = value
                LOG.info("Using default: '%s' = '%s'" % (key, value))
        # check if BSS commands are accessible
        if config.get('tsi.testing') is not True:
            (success, output) = Utils.run_command(config['tsi.qstat_cmd'])
            if not success:
                msg = "Could not run command to check job statuses! " \
                      "Please check that the correct TSI is installed, and " \
                      "check the configuration of 'tsi.qstat_cmd' : %s" % output
                LOG.error(msg)
                raise RuntimeError(msg)
        # for storing child process PIDs
        children = config.get('tsi.NOBATCH.children')
        if children is None:
            config['tsi.NOBATCH.children'] = []

    def create_submit_script(self, message, config, LOG):
        """ For batch systems, this method is responsible for 
            creating the script that is sent to the batch system.
            See the slurm/BSS.py for an example.
        """
        return []

    def create_alloc_script(self, message, config, LOG):
        """ For batch systems, this method is responsible for
            creating a script that will allocate resources,
            but not launch any tasks.
            See the slurm/BSS.py for an example.
        """
        return []

    def submit(self, message, connector, config, LOG):
        """ Submit a script to the batch system.
           Depending on the TSI_JOB_MODE parameter, the the batch system 
           parameters will be generated in different ways.

           "normal"  : parameters will be generated from the resource settings sent 
                       by the UNICORE/X server

           "raw"     : the file given by the TSI_JOB_FILE parameter will be submitted 
                       without further intervention by UNICORE.

           "allocate": the TSI will only create an allocation without launching 
                       anything. This will run the allocation command (e.g. "salloc" on Slurm)
                       in the background, and UNICORE/X can get the allocation ID from a file
                       once this task has finished.
        """
        message = Utils.expand_variables(message)

        uspace_dir = Utils.extract_parameter(message, "USPACE_DIR")
        os.chdir(uspace_dir)

        job_mode = Utils.extract_parameter(message, "JOB_MODE", "normal")
        is_alloc = job_mode.startswith("alloc")

        LOG.debug("Submitting a batch job, mode=%s" % job_mode)

        if "normal" == job_mode:
            submit_cmds = self.create_submit_script(message, config, LOG)
        elif "raw" == job_mode:
            raw_cmds_file_name = Utils.extract_parameter(message, "JOB_FILE")
            if raw_cmds_file_name is None:
                connector.failed("Job mode 'raw' requires TSI_JOB_FILE")
                return
            with open(raw_cmds_file_name, "r") as f:
                submit_cmds = [f.read()]
        elif is_alloc:
            try:
                submit_cmds = self.create_alloc_script(message, config, LOG)
            except:
                connector.failed("Allocation mode not (yet) supported!")
                return
        else:
            connector.failed("Illegal job mode: %s " % job_mode)
            return
        
        # create unique name for the files used in this job submission
        submit_id = str(int(time() * 1000))
        userjob_file_name = "UNICORE_Job_%s" % submit_id

        if job_mode.startswith("alloc"):
            # run allocation command in the background
            cmd = message + u"\n"
            cmd += u"{ "
            for line in submit_cmds:
                cmd += line + u" ; "
            pid_file_name = Utils.extract_parameter(message, "PID_FILE", "UNICORE_SCRIPT_PID")
            cmd += u"} & echo $! > %s \n" % pid_file_name
            with open(userjob_file_name, "w") as job:
                job.write(u"" + cmd)
            children = config.get('tsi.NOBATCH.children', None)
            (success, reply) = Utils.run_command(cmd, True, children)
        else:
            with open(userjob_file_name, "w") as job:
                job.write(u"" + message)
            Utils.addperms(userjob_file_name, 0o770)
            submit_cmds.append(uspace_dir + "/" + userjob_file_name)
            submit_file_name = "bss_submit_%s" % submit_id
            with open(submit_file_name, "w") as submit:
                for line in submit_cmds:
                    submit.write(line + u"\n")
            Utils.addperms(submit_file_name, 0o770)
            # run job submission command
            cmd = config['tsi.submit_cmd'] + " ./" + submit_file_name
            (success, reply) = Utils.run_command(cmd)
        
        if not success:
            connector.failed(reply)
        elif is_alloc:
            connector.ok()
        else:
            LOG.info("Job submission result: %s" % reply)
            job_id = self.extract_job_id(reply)
            if job_id is not None:
                connector.write_message(job_id)
            else:
                connector.failed("Submit failed? Submission result:" + reply)

    def get_extract_id_expr(self):
        """ regular expression for extracting the job ID after batch submit """
        return r"\D*(\d+)\D*"

    def extract_job_id(self, submit_result):
        """ extracts the job ID after submission to the BSS """
        # expect "<blah>NNN<blah> ...", extract the 'NNN'
        job_id = None
        expr = self.get_extract_id_expr()
        m = re.search(expr, submit_result)
        if m is not None:
            job_id = m.group(1)
        return job_id

    def extract_info(self, qstat_line):
        raise RuntimeError("Method not implemented!")

    def convert_status(self, bss_state):
        raise RuntimeError("Method not implemented!")

    __ustates = ["COMPLETED", "QUEUED", "SUSPENDED", "RUNNING"]

    def parse_status_listing(self, qstat_result):
        """ Does the actual parsing of the status listing. """
        states = {}
        for line in qstat_result.splitlines():
            (bssid, state, queue_name) = self.extract_info(Utils.encode(line))
            if bssid is None:
                continue
            ustate = self.convert_status(state)
            if states.get(bssid, None) is None:
                states[bssid]=(ustate,queue_name)
            else:
                have_state,_ = states[bssid]
                if self.__ustates.index(ustate)>self.__ustates.index(have_state):
                    states[bssid]=(ustate,queue_name)
 
        # generate reply to UNICORE/X
        result = "QSTAT\n"
        for bssid in states:
            ustate, queue_name = states[bssid]
            result += " %s %s %s\n" % (bssid, ustate, queue_name)
        return result

    def get_status_listing(self, message, connector, config, LOG):
        """ Get info about all the batch jobs and parses it.
        """
        qstat_cmd = config["tsi.qstat_cmd"]
        (success, qstat_output) = Utils.run_command(qstat_cmd)
        if not success:
            connector.failed(qstat_output)
            return
        result = self.parse_status_listing(qstat_output)
        connector.write_message(result)

    def get_process_listing(self, message, connector, config, LOG):
        """ Get list of the processes on this machine.
        """
        ps_cmd = Utils.extract_parameter(message, "PS", config["tsi.get_processes_cmd"])
        Utils.run_and_report(ps_cmd, connector)

    def parse_job_details(self, raw_info):
        """ Converts the raw job info into a dictionary """
        result = {}
        try:
            tokens = re.compile("\s+").split(raw_info.strip())
            for t in tokens:
                try:
                    kv = t.split("=",1)
                    result[kv[0]] = kv[1]
                except:
                    pass
        except:
            result['errorMessage'] = "Could not parse BSS job details"
            result['BSSJobDetails'] = raw_info
        return result

    def get_job_details(self, message, connector, config, LOG):
        bssid = Utils.extract_parameter(message, "BSSID")
        cmd = config["tsi.details_cmd"] + " " + bssid
        (success, output) = Utils.run_command(cmd)
        if not success:
            connector.failed(output)
            return
        result = self.parse_job_details(output)
        try:
            import json
            out = json.dumps(result)
        except:
            out = str(result)
        connector.ok("%s\n" % out)

    def abort_job(self, message, connector, config, LOG):
        bssid = Utils.extract_parameter(message, "BSSID")
        cmd = config["tsi.abort_cmd"] % bssid
        Utils.run_and_report(cmd, connector)

    def hold_job(self, message, connector, config, LOG):
        bssid = Utils.extract_parameter(message, "BSSID")
        cmd = config["tsi.hold_cmd"] + " " + bssid
        Utils.run_and_report(cmd, connector)

    def resume_job(self, message, connector, config, LOG):
        bssid = Utils.extract_parameter(message, "BSSID")
        cmd = config["tsi.resume_cmd"] + " " + bssid
        Utils.run_and_report(cmd, connector)

    def get_budget(self, message, connector, config, LOG):
        """ Gets the remaining compute time for the current user 
        on this resource. See Quota.get_quota() for details.
        """
        quota = Quota.get_quota(config, LOG)
        connector.ok("%s\n" % quota)
