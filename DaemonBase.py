#!/usr/bin/env python3

# From: https://github.com/aigo9/python-daemon-example/blob/master/pd_example.py

import sys
import os
import time
import argparse
import logging
# python-daemon                    2.2.4
import daemon
import signal

# lockfile                         0.12.2
from lockfile.pidlockfile import PIDLockFile

class DaemonBase(object):
    def __init__(self, name, pid_file=None, working_directory=None, stdout_file=None, stderr_file=None, log_file=None, verbose=False):
        self.name = name

        if pid_file is None:
            pid_file = os.path.join("/var/run", self.name + ".pid")

        if working_directory is None:
            working_directory = os.path.join("/var/lib", self.name)

        if stdout_file is None:
            stdout_file = os.path.join("/var/log", self.name + ".stdout")

        if stderr_file is None:
            stderr_file = os.path.join("/var/log", self.name + ".stderr")

        if log_file is None:
            log_file = os.path.join("/var/log", self.name + ".log")

        self.pid_file = pid_file
        self.working_directory = working_directory
        self.stdout_file = stdout_file
        self.stderr_file = stderr_file
        self.log_file = log_file
        self.verbose = verbose
        self.args = None # Command line arguments from argparse.ArgumentParser.parse_args()

    def run(self):
        # Do the actual work of the daemon
        pass
                
    def start(self, args=None):
        if self.verbose:
            print("{0}: starting...".format(self.name))
            print("{0}: PID file = {1}".format(self.name, self.pid_file))
            print("{0}: Log file = {1}".format(self.name, self.log_file))
# TODO don't start if already running.
# TODO Create any needed directories?
        self._createDirectories( self.pid_file, isFile=True )
        self._createDirectories( self.working_directory, isFile=False )
        self._createDirectories( self.stdout_file, isFile=True )
        self._createDirectories( self.stderr_file, isFile=True )
        self._createDirectories( self.log_file, isFile=True )
        with daemon.DaemonContext(
            working_directory=self.working_directory,
            umask=0o002,
            pidfile=PIDLockFile(self.pid_file, timeout=2.0),
            stdout=open(self.stdout_file, "a+"),
            stderr=open(self.stderr_file, "a+")):
            self.run()

    def stop(self, args=None):
        if self.verbose:
            print("{0}: stopping...".format(self.name))

        plf = PIDLockFile(self.pid_file)
        pid = plf.read_pid()
        if plf.is_locked() and pid is not None:
            os.kill(pid, signal.SIGTERM)
        else:
            print("{0}: NOT running".format(self.name))

    def restart(self, args=None):
        self.stop(args)
        self.start(args)

    def status(self, args=None):
        plf = PIDLockFile(self.pid_file)
        pid = plf.read_pid()
        if plf.is_locked() and pid is not None:
            print("{0}: running, PID = {1}".format(self.name, pid))
            if self.verbose:
                print(f"{self.name}: Working directory: {self.working_directory}")
                print(f"{self.name}: PID file: {self.pid_file}")
                print(f"{self.name}: Log file: {self.log_file}")
                if self.stdout_file != self.log_file:
                    print(f"{self.name}: Stdout file: {self.stdout_file}")
                if self.stderr_file != self.log_file:
                    print(f"{self.name}: Stderr file: {self.stderr_file}")
        else:
            print("{0}: NOT running".format(self.name))

    def createArgsParser(self,description):
        parser = argparse.ArgumentParser( description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter )

        parser.add_argument( "-v", "--verbose", help="print additional messages to stdout", action="store_true")

        parser.add_argument('-n', '--name', default=self.name, help="Daemon name. Used in filenames and logs.")
        parser.add_argument('-d', '--dir', default='/var', help="Base directory for all files.")
        parser.add_argument('-p', '--pid_file', default=None, help="Override PID pathname.")
        parser.add_argument('-w', '--working_directory', default=None, help="Override working directory.")
        parser.add_argument('-l', '--log_file', default=None, help="Override log pathname.")
        parser.add_argument('-s', '--stdout_file', default=None, help="Override pathname for stdout.")
        parser.add_argument('-e', '--stderr_file', default=None, help="Override pathname for stdout.")

# See https://stackoverflow.com/questions/48648036/python-argparse-args-has-no-attribute-func
        parser.set_defaults(func=lambda args: parser.print_help())

        subparsers = parser.add_subparsers(title="commands")
        sp_start = subparsers.add_parser("start", description="start daemon")
        sp_start.set_defaults(func=self.start)
        sp_stop = subparsers.add_parser("stop", description="stop daemon")
        sp_stop.set_defaults(func=self.stop)
        sp_restart = subparsers.add_parser("restart", description="restart daemon")
        sp_restart.set_defaults(func=self.restart)
        sp_status = subparsers.add_parser("status", description="check daemon status")
        sp_status.set_defaults(func=self.status)

        self.parser = parser
        return parser

    def handleArgs(self):
        args = self.parser.parse_args()

        self.args = args
        self.name = args.name
        self.verbose = args.verbose

        self.working_directory = os.path.join(args.dir, "lib", self.name )
        self.pid_file =  os.path.join(args.dir, "run", self.name + ".pid")
        self.log_file = os.path.join(args.dir, "log", self.name + ".log")
        self.stdout_file = self.log_file
        self.stderr_file = self.log_file

        if args.working_directory is not None:
            self.working_directory = args.working_directory
        if args.log_file is not None:
            self.log_file = args.log_file
        if args.pid_file is not None:
            self.pid_file = args.pid_file
        if args.stdout_file is not None:
            self.stdout_file = args.stdout_file
        if args.stderr_file is not None:
            self.stderr_file = args.stderr_file

        args.func(args)

    def _createDirectories( self, path, isFile=False ):
        if isFile:
            path = os.path.dirname(path)
        if os.path.isdir(path):
            return
        os.makedirs(path)

class TestDaemon(DaemonBase):
    def __init__(self, extra1, *args, extra2=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra1 = extra1
        self.extra2 = extra2

    def run(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)

        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.INFO)

        log_format = '%(asctime)s|%(levelname)s|%(message)s'

        fh.setFormatter(logging.Formatter(log_format))

        logger.addHandler(fh)

        if self.verbose:
            print( f"Extra1: {self.extra1}" )
            print( f"Extra2: {self.extra2}" )

        while True:
            logger.info("sample INFO message")
            time.sleep(5)

if __name__ == "__main__":
    here = os.path.abspath(os.path.dirname(__file__))
    base_name = os.path.basename(__file__).split('.')[0]

    # To avoid dealing with permissions and to simplify this example
    # setting working directory, pid file and log file location etc.
    # to the directory where the script is located. Normally these files
    # go to various subdirectories of /var

    # working directory, normally /var/lib/<daemon_name>
    working_directory = here

    # log file, normally /var/log/<daemon_name>.log
    log_file = os.path.join(here, base_name + ".log")

    # pid lock file, normally /var/run/<daemon_name>.pid
    pid_file = os.path.join(here, base_name + ".pid")

    # stdout, normally /var/log/<daemon_name>.stdout
    stdout_file = os.path.join(here, base_name + ".stdout")

    # stderr, normally /var/log/<daemon_name>.stderr
    stderr_file = os.path.join(here, base_name + ".stderr")

    test = TestDaemon( "extra1arg", base_name, extra2="foo", pid_file=pid_file, working_directory=working_directory, stdout_file=stdout_file, stderr_file=stderr_file, log_file=log_file, verbose=False)
    parser = test.createArgsParser(description="Minimalist example of using DaemonBase class")
    # add any extra command line arguments here
    test.handleArgs()
