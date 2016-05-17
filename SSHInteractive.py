import logging
import socket
import traceback
import sys

import time

import re
from lxml import etree

import nxos_XML_errors
from command_parser import commandparse, Configparse
from ncssh import SshConnect

__version__ = '2015.12.16.1'

logger = logging.getLogger('sshinteractive')


class SSHInteractive(SshConnect):
    """
    A subclass of NxosConnect that adds the ability to switch between VDCs

    This is only possible by ssh'ing to the cli, running the switchto vdc command and then dropping into the xml subsystem
    """
    def __init__(self, host, prompt, type='Cisco'):
        """

         A subclass of NxosConnect that adds the ability to switch between VDCs

        This is only possible by ssh'ing to the cli, running the switchto vdc command and then dropping into the xml subsystem

        @param host: str
        @param prompt: str, need a prompt so we can detect when a cli command has finished running

        """
        SshConnect.__init__(self, host)
        self.type = type
        self.prompt = prompt
        self.logger = logging.getLogger('SSHInteractive.SSHInteractive')
        self.logger.debug("Instantiating SSH object for {}".format(self.host))

    #SSH object requires that the subclass define the object
    def setup_channel(self):
        """
        Activating an interactive shell for device
        """
        self.ssh_shell()
        self.look_for_prompt()

    def look_for_prompt(self):
        """
        Look for prompt from interactive shell
        @return:
        """
        try:
            self.logger.debug("Waiting for ssh shell prompt {}".format(self.prompt))
            s = self.rpexpect(self.prompt)
            self.logger.debug("Received from server {}".format(s))
        except:
            self.logger.error("Unexpected string from device {} - {}".format(self.host, s))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            self.close()
            raise

    def _send(self, cmd, tprompt = None):

        """
        Send constructed command message to device

        Any exceptions returned by ncssh.rpexpect are reraised


        """
        prompt = self.prompt
        if tprompt is not None:
            prompt = tprompt

        #send message to server
        self.logger.debug("SSHInteractive Send: Sending command {} to device {}: waiting for {}".format(cmd, self.host, prompt))
        self.send(cmd.strip() + '\n')

        #wait for response from server
        self.logger.debug("Waiting for response from device {} ".format(self.host))
        response = None
        try:
            response = self.rpexpect(prompt)
            self.logger.debug("SSHInteractive Send: response from device {}: {}".format(self.host, response))
        except socket.timeout:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error("SSHInteractive Send: Socket timeout waiting for response to {} to {}".format(cmd, self.host))
            self.logger.debug("SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            raise
        except nxos_XML_errors.TimeoutExpiredError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error("SSHInteractive Send: Loop timeout waiting for response to {} to {}".format(cmd, self.host))
            self.logger.debug("SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            raise
        except nxos_XML_errors.ServerClosedChannelError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error("SSHInteractive Send: Server closed channel while waiting for response to {} to {}".format(cmd, self.host))
            self.logger.debug("SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            self.closesession()
            #do not propagate exception, closesession will raise one
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error("SSHInteractive Send: Unexpected error while waiting for response to {} to {}".format(cmd, self.host))
            self.logger.debug("SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            raise

        #parse response and check for errors
        self.logger.debug("SSHInteractive Send: Received respone {}".format(response))
        if re.search('ERROR', response):
            self.logger.error("SSHInteractive Send: Error at :  " + self.host + " while running :  " + cmd + "  Output:  "  + response + "\n")
        return response

    def ssh_cmd_run(self, cmdlist):
        buff = ''
        if isinstance(cmdlist, str):
            cmdlist = [cmdlist]
        self.logger.debug("SSHInteractive ssh_cmd_run: Command list for device {}: {}".format(self.host, str(cmdlist)))
        try:
            if self.type == 'Cisco':
                self.logger.debug("SSHInteractive ssh_cmd_run: Sending command 'term len 0' to device {}".format(self.host))
                response = self._send('term len 0')
            for cmd in cmdlist:
                response = self._send(cmd)
                self.logger.debug("SSHInteractive ssh_cmd_run: Running " + cmd + " on " + self.host)
                self.logger.debug("SSHInteractive ssh_cmd_run: Received resonse " + response + " from " + self.host)
                buff += response
        except:
            raise
        self.logger.debug("SSHInteractive ssh_cmd_run: Sending response {}".format(buff))
        return buff

    def ssh_cmd_action(self, cmdlist):
        self.logger.debug("SSHInteractive ssh_cmd_action: action list: {}".format(cmdlist))
        buff = ''
        try:
            #if OPTS['cisco']:
            for cmd, prompt in cmdlist:
                response = self._send(cmd, prompt)
                self.logger.debug( "SSHInteractive ssh_cmd_action: Sending " + cmd + " on " + self.host)
                self.logger.debug( "SSHInteractive ssh_cmd_action: Waiting for {} on {} ".format(prompt, self.host))
                self.logger.debug( "SSHInteractive ssh_cmd_action: Response " + response)
                buff += response
        except:
            raise
        self.logger.debug("SSHInteractive ssh_cmd_action: Sending response {}".format(buff))
        return buff

    def ssh_parse_test(self, parselist):
        """
        parselist is a dictionary of the form:
        {command1:
            {
                flag1:
                    [regex1, regex2, ...],
                flag2:
                    [regex3, regex4, ...],
                ...
                flagn:[regexm, regexn]
            }
        command2:...}

        allowed flags are existl, notexistl, cmpcountl
        :param parselist: dictionary
        :return: dictionary
        """
        parseresults = {}
        passed = True
        for cmdr in parselist:
            self.logger.debug("SSHInteractive ssh_parse_test: Sending command {} to {}".format(cmdr, self.host))
            response = self.ssh_cmd_run(cmdr)
            self.logger.debug("SSHInteractive ssh_parse_test: " + self.host + " - Results of {}".format(response))
            self.logger.debug("SSHInteractive ssh_parse_test: " + self.host + " - Testng {} {}".format(response, parselist[cmdr]))
            parseresult = response
            if parselist[cmdr] is not None:
                parseresult = commandparse(Configparse(response), parselist[cmdr])
                self.logger.debug("SSHInteractive ssh_parse_test: result of testing: {}".format(str(parseresult)))
                for result in parseresult.values():
                    if (False in result) or (None in result) or ('Error' in result):
                        self.logger.error("SSHInteractive ssh_parse_test: {} has failed this test. Result {} for cmdr {}".format(self.host, result, cmdr))
                        passed = False
            parseresults[cmdr] = parseresult
        return passed, parseresults
