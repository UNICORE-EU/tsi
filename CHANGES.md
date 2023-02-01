Changelog for the UNICORE TSI
=============================

Issue tracker: https://sourceforge.net/p/unicore/issues

Version 9.1.3
-------------
 - improvement: also pass original BSS status to UNICORE/X
   (e.g. "CONFIGURING" on Slurm)

Version 9.1.2
-------------
 - fix: RPM package file permissions
   (thanks to Daniel Fernandez)
 - new feature: add support for Slurm "--comment" option
   (thanks to Daniel Fernandez)
 - improvement: configure setpriv via SETPRIV_OPTIONS variable
   in startup.properties (thanks to Daniel Fernandez)

Version 9.1.1
-------------
 - fix: async scripts are started in a new session
 - fix: handling deprecated property names was buggy
   (in some cases tsi.unicorex_machine was always set
   to "localhost")

Version 9.1.0
-------------
 - new feature: port forwarding from a service accessible
   by the TSI to UNICORE/X
 - fix: when setpriv is not available, TSI should run as root,
   not as the system user ("unicore") configured in 'startup.properties' 

Version 9.0.1
-------------
 - fix: parse_qstat_listing() could not handle UNKNOWN job state

Version 9.0.0
-------------
 - new feature: add TSI API call to get user information including
   public keys from a configurable list of sources
 - new feature: (optional) configurable range of local ports
   for the TSI to use
 - fix: logging to file was not working correctly
 - simplified PAM.py module
 - rename a few config properties for more clarity
   (old property names are still accepted) 
 - code cleanup
 - fix: Install.sh should allow read access to lib/*.py files
   (required when using TSI for uftp data staging)
 - fix rpm/deb build errors

Version 8.3.0
-------------
 - new feature: new job type: 'allocate' which will
   allocate resources without launching anything
   Currently implemented only for Slurm via 'salloc'
 - new feature: PAM support for optionally registering 
   user tasks with a user session (#292)
 - new feature: UFTP support (get/put of remote files
   via builtin uftp client)
 - fix: Slurm: rounding error for small runtimes leads
   to "#SBATCH --time 0"
 - fix: handle invalid messages from UNICORE/X gracefully
 - new feature: add TSI API call to get the process listing
   (via 'ps -e' by default)
 - code cleanup
 - fix minor issues in deb/rpm packaging

Version 8.2.1
-------------
 - improvment: allow to run as unprivileged user with added
   setuid/setgid capabilities via 'setpriv' or similar tool
 - fix: wrong pid in systemd service file

Version 8.2.0
-------------
 - re-organize logging, log to syslog by default
 - fix: split DNs only on ","
 - remove duplicate code in BecomeUser.py

Version 8.1.0
-------------
 - drop Python2 support

Version 8.0.5
-------------
 - fix: typos in Makefile
 - fix: python3 "FutureWarning: split() requires a non-empty pattern match"

Version 8.0.4
-------------
 n/a

Version 8.0.3
-------------
 - fix: GetJobDetails should return with "TSI_OK"

Version 8.0.2
-------------
 n/a

Version 8.0.1
-------------
 - GetJobDetails returns JSON

Version 8.0.0
-------------
 - new file Quota.py containing API to retrieve the user's
   compute budget per project (#252)
 - fix: Slurm: "--workdir" option replaced by "--chdir"
 - fix: Slurm: stricter parsing of sbatch reply
 - new feature "#TSI_JOB_MODE raw" uses the file supplied via
   "#TSI_JOB_FILE <filename>" as batch system submit specification
   (without any further processing of resources requested via UNICORE)
 - new feature: pre-defined resource "QoS" (mapped e.g in Slurm
   to "#SBATCH --qos")

Version 7.12.0
--------------
 - fix: Slurm: detect illegal characters in job name (#230)
 - fix: add alternate implementation for getting all supplementary
   groups. set "tsi.use_id_to_resolve_gids=true" to enable (#238)
 - new feature: "#TSI_JOB_MODE"

Version 7.11.0
--------------
 - fix: LSF: new syntax to specify GPUs
 - fix: fail if invalid user is requested by UNICORE/X

Version 7.10.2
--------------
 - remove *.pyc files on startup, to avoid changes not being picked
   up (#220)

Version 7.10.1
--------------
 - fix: Slurm, Torque: BSS nodes filter handling (#212)

Version 7.10.0
--------------
 - fix: ACL implementation was buggy (#199)
 - fix: default BSS abort commands were missing '%s' (#202)
 - fix: add missing job states to LSF BSS.py (#201)
 - improve handling of numeric resource values

Version 7.9.0
-------------
 - fix: nobatch TSI should kill all processes for a job (#176)
 - fix: reading port from UNICORE/X did not work when using Python3,
   leading to an error when connecting (#158)
 - fix: numerical resource values must be integers
 - fix: handle invalid messages to main TSI process without
   exiting 
 - use timeout when connecting back to UNICORE/X to avoid deadlocks
 - fix parsing allowed DNs from TSI properties file (#183)
 - fix: LSF: use resource spec to specify processors per node and GPUs
 - add systemd support (#165)
 - fix: handle non-ascii characters in qstat listing (#191)

Version 7.8.0
-------------
 - add some hooks for site-local adaptations
 - improvement: handle socket errors more cleanly
 - fix: allow more characters in user/group name (#137)
 - fix: group handling in TSI.py was buggy (#138)
 - fix: treat empty "#TSI_..." parameters as "NONE"

Version 7.7.0
-------------
 - fix: safer cleanup of subprocesses
 - fix: possible message encoding problem (#124)

Version 7.6.0
-------------
 - new feature: support for array jobs (Torque, Slurm, LSF)
 - fix: LoadLeveler: mismatch in job ID comparison (#81)
 - fix: LoadLeveler: job ID extraction broken (#82)
 - fix: change the TSI process's initial directory to
   something safe ('/tmp') to avoid "permission denied" errors
 - setup TCP keep-alive for command and data sockets to avoid data socket
   shutdown due to inactivity
 - fix: run execute_script stuff in the background (#95)
 - improve and simplify the BSS code
 
Version 7.5.1
-------------
 - fix: typo in BSSCommon.py leading to errors when aborting jobs
   "TSI_FAILED: global name 'TSI' is not defined"
   (https://sourceforge.net/p/unicore/issues/69)
 - fix: handle missing TSI_TIME correctly
   (https://sourceforge.net/p/unicore/issues/70)
 - fix: IP check was not implemented
   (https://sourceforge.net/p/unicore/issues/72)
 - fix: several small issues in the manual were fixed

Version 7.5.0
-------------
 - clean re-implementation in Python
 - packages (deb,rpm,tgz) for Nobatch, Torque, Slurm, LSF, 
   LoadLeveler, as well as a generic tgz with an Install.sh script
 - start.sh, stop.sh, status.sh scripts similar to 
   other UNICORE components
 - configuration centralized into tsi.properties and startup.properties
 - SSL plus a list of allowed DNs to validate connections
 - DF and LS are now internal TSI functions as opposed to 
   external Perl scripts
 - uses the powerful Python logging API
 - simpler code, easier to adapt to site-local setup
 - possibility to easily test and check your installation without 
   having to go through the full UNICORE stack
 - updated manual

Version 7.4.0
-------------
 - improvement: add alternative implementation to get the
   supplementary groups, since users have reported one case 
   where the current implementation did not work
 - fix: start_tsi script uses conf/ directory as fallback

Version 7.2.0
-------------

 - fix: Slurm: remove extra "\n" when setting "--account"
 - fix: tsi_ls: replace newline by '?'
 - fix: cleanup SSL code, make it more portable with respect 
   to IPv6/IPv4. Use separate key and certificate files.
 - update docs on configuring SSL
 - add section on securing/hardening the TSI to the manual
 - fix .deb packaging

Version 7.1.0
-------------
 - new feature: bind to specific network interface
   (SF feature #336)
 - provide Linux packages for Nobatch, Torque, Slurm, 
   SGE and LSF

Version 7.0.3
-------------
 - improvement: new PutFileChunk function for faster
   file writes
 - improvement: deb/rpm packages are now batch-system specific 
   (available for torque. TBD: slurm, lsf, sge, nobatch)

Version 7.0.2
-------------
 - fix: runtime specification syntax for Slurm

Version 7.0.1
-------------

 - fix: SGE: remove non-word characters from job name
   (SF bug #707)
 - improvement: Slurm: configure getting job details

Version 7.0.0
-------------

 - add configurable expiry to uid, gid cache, so entries
   are uid/gid mappings are updated without server restart
 - report errors (debug level) when uid/gid setting fails
 - fix: do not change file permissions when writing to existing 
   files (SF bug #639)
 - fix: memory and walltime settings in LSF Submit.pm
 - fix: LSF GetStatusListing.pm
 - fix: SGE: add command for getting job details
 - added helper tool (see test_job_status/README) to test 
   that GetStatusListing.pm works correctly

Version 6.5.1
-------------

 - new feature: TSI supports filtering execution nodes by node properties
   (implemented for Slurm, Torque)
 - fix: NOBATCH: do not remove submitted file in Submit.pm
 - fix: NOBATCH: "get job details" caused exception in UNICORE/X
 - fix: NOBATCH: status check was not working correctly 
   (SF bugs #3560312 and #3560663)
 - fix: NOBATCH: reduce forked process' niceness and ionice class
   to reduce load on the TSI node (SF bug #3560657)
 - new feature: ResourceReservation.pm module for Slurm
 - improvement: updated ResourceReservation.pm module for Maui, added
   to Torque TSI
 - improvement: SLURM: handle reservation, better GetStatusListing.pm
 - improvement: better reporting of file write errors to XNJS 

Version 6.5.0
-------------

 - improvement: tsi_df reports back errors to XNJS
 - improvement: Torque Submit.pm: set default directory 
 - fix: delete PID file after stopping TSI (SF bug #3482191)
 - improvement: SGE: use "qstat -u '*'" to show jobs from all users
 - improvement: clean up perl code formatting using "perltidy"
 - delete obsolete EndProcessing.pm
 - fix: do not chmod if appending to files (SF bug #3331135)
 - fix: Install.sh will backup existing, modified files in
   the target install directory
 - new feature: add XNJS/TSI API to get detailed information about
   a single job (SF improvements #3405627)
 - update API documentation
 - update linux_pbs variant (mostly the same as linux_torque)
 - fix: make Torque GetStatusListing.pm regexp fit when qstat does not
   report number of nodes

Version 6.4.2
-------------

 - improvement: ACL.pm allows for setting and getting default ACL. Also support 
   for recursive ACL operations is added. It is explicitly stated that the 
   current implementation will work only with the Linux implementation of 
   the get/setfacl commands (SF enhancements #3380959)
 - improvement: new XNJS/TSI API #TSI_UMASK for setting the default umask 
   for directories and jobs (SF enhancements #3385750)
 - improvement: optionally return queue information in GetStatusListing.pm
 - improvement: new XNJS/TSI API #TSI_PROJECT for specifying the project.
   Project support added for: Torque, Slurm, SGE
 - fix: setting "tsi.fail_on_invalid_gids=false" did not have the intended effect
 - fix: use "vmem" on Torque (SF bug #2885645)
 - added scp-wrapper.pl and scp-wrapper.sh (TCL) helper scripts for scp data staging
 - improvement: LL Submit.pm passes reservation reference (SF patch #3427717)

Version 6.4.1
-------------

 - Submit.pm: handle TSI_STDERR and TSI_STDOUT sent from XNJS for redirecting
   output and error
 - new feature: tsi_ls is returning more information on files: owner, owning group, 
   full UNIX permissions
 - new feature: module ACL.pm for getting/setting filesystem ACL
 - fix: Torque: GetStatusListing.pm does not allow non-word characters in queue 
   name
 - updated the manual

Version 6.4.0
-------------

 - new feature: allow logging to syslog (contributed by Xavier Delaruelle, CEA)
 - Slurm: fix memory and cpus/nodes specification (contributed by Xavier Delaruelle, CEA)
 - No-batch: fix typo in PING processing
 - new feature: RPM packaging
 - new feature: reservation module for Maui in contrib/schedulers/maui
 - documentation in HTML and PDF formats

Version 6.3.2
-------------

 - fix path in template tsi.properties (SF bug #3098113)
 - fix abort in Nobatch TSI (SF bug #3044284)
 - TSI_PING replies with version number (as defined in $main::my_version)
 - set version numbers to "6.3" in the supported TSI versions
 - Torque TSI: when submit error occurs, output standard error message 
   returned by qsub instead of the standard output
 - fix handling of comma-separated lists of XNJS hostnames in Initialisation.pm
 - Torque TSI: queue passed from XNJS is actually used. When there is no
   queue sent by XNJS, the default queue is used (not 'batch' as it used to be)
 - TSI allows for flexible groups selection. It is possible to request:
   primary group, list of supplementary groups, an OS-default primary group
   and to use all OS-default supplementary groups for the user (also along
   with the list of additional supplementary groups). The new configuration
   option can be used to limit this behavior: tsi.enforce_gids_consistency
 - 'tsi' files (BSS specific) were split into two parts. The BSS independent 
   code is in SHARED/SharedConfiguration.pm now and 'tsi' file contains 
   only truly BSS or OS specific code
 - tsi.properties is now parsed in SharedConfiguration.pm. The only one command
   line argument to tsi Perl application is tsi.properties file location. 

Version 6.3.1
-------------

(no changes)

Version 6.3.0
-------------

 - Install.sh now will copy ALL files (incl. bin, conf) to the 
   installation directory (sf feature #2937301)
 - TSI/XNJS SSL support (contributed by Clement Coussirat, CEA)
 - TSI/XNJS port negotiation to allow multiple XNJS instances to 
   connect to the TSI (contributed by Clement Coussirat, CEA)
 - Fix usage of open3 system call which caused zombie processes 
   to last after every submit was fixed
 - Fix tsi_ls to work correctly on filesystems using ACLs

Version 6.2.2
-------------

 - when no group (aka project) is chosen then BecomeUser.pm sets also 
   supplementary groups for the user process.
 - actually include the change to ExecuteScript.pm described in version
   6.2.1 below
 - add TSI module for Cray XT / Torque (contributed by Troy Baer)

Version 6.2.1
-------------

 - new XNJS/TSI protocol variable TSI_TOTAL_PROCESSORS giving the total
   number of processors. The TSI_PROCESSORS stays as-is
 - made ExecuteScript.pm more flexible by allowing to discard script 
   output and thus start processes in the background

Version 6.1.3
-------------

 - introduce "COMPLETED" state (see linux_torque GetStatusListing.pm) for
   completed jobs that are still listed in the qstat output
 - fix bin/start_tsi (setup log directory)

Version 6.1.2 
-------------

 - apply patches from Xavier Delaruelle for some minor bugs (SHARED
   BecomeUser.pm, JobControl.pm, PutFiles.pm)
 - added TSI implementation for SLURM, provided by BSC and adapted by 
   Xavier Delaruelle
 - allow to run the Install.sh script non-interactively

Version 6.0.1 November 2007
---------------------------

 - general cleanup and move to the UNICORE SVN. Move older/obsolete TSI
   versions to the tsi_contrib/ directory.
 - NOTE: some TSIs still need testing (e.g. Condor)
 - new config parameter for setting the log dir, defaults to <basedir>/logs,
   e.g. tsi_NOBATCH/logs
 - extended resource reservation support, please see
   tsi/SHARED/ResourceReservation.pm for details


Version 4.1.2 Aug 24, 2005
---------------------------

 - added ResourceReservation.pm dummy resource reservation module to the 
  SHARED TSI code. It is called from MainLoop.pm if the NJS command includes a 
  line #TSI_RESERVATION_REFERENCE nnnnn 
  Otherwise 'submit' is called.

 - TSI for LSF modified to work with version LSF 6.0 (contributed by SARA)
 PLEASE CHECK GetStatusListing.pm if you want to use LSF

Version 4.1.1 March 31, 2005
----------------------------

 - new TSI for Sun GridEngine (5.3 tested, 6.0 needs modification due
 to changed qstat output, check GetStatusListing.pm).

Version 4.1
-----------

 - Replaced GetDirectory by simpler GetFileChunk (Mandatory update)
 - Optional implementation of FREEZE command and state

first sf.net upload, 29.04.2004
-------------------------------

 - included "no-zombie" patch (from K.-D. Oertel) into NOBATCH TSI 

Version 4.0.4, sep 05, 2003
---------------------------

 - updated tsi/SHARED/GetDirectory.pm for use with NJS 4.0.3
 - new tsi/superux/BecomeUser.pm for NEC
 - bin/start_tsi checks whether the 'tsi' file exists


Version 4.0.3, jun 12, 2003
---------------------------

 - new version for LSF on SGI


