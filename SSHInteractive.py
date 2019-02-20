import logging
import re
import socket
import sys
import time
import traceback

import nxos_XML_errors
from command_parser import commandparse, Configparse
from ncssh import SshConnect

__version__ = '2015.12.16.1'

logger = logging.getLogger('sshinteractive')

CISCO_CONFIG_PROMPT = r"\(config\S*\)#"
CISCO_BASE_PROMPT = r'>'
CISCO_PRIV_PROMPT = r'#'


class SSHInteractive(SshConnect):
    """
    A subclass of NxosConnect that adds the ability to switch between VDCs

    This is only possible by ssh'ing to the cli, running the switchto vdc command and then dropping into the xml subsystem
    """

    def __init__(self):
        """

         A subclass of NxosConnect that adds the ability to switch between VDCs

        This is only possible by ssh'ing to the cli, running the switchto vdc command and then dropping into the xml subsystem

        @param host: str
        @param prompt: str, need a prompt so we can detect when a cli command has finished running
        :type check_enable: bool
        @param check_enable: if True and device is not in priv mode, attempt to put in privilege mode

        """
        self.logger = logging.getLogger('SSHInteractive.SSHInteractive')
        self.logger.debug("Instantiating SSH object for {}".format(self.host))

    def sshconnect(self, host, *args, prompt=None, username=None, password=None, type='Cisco', check_priv=True,
                   enable_password=None, **kwargs):
        super().__init__(host)
        self.type = type
        self.prompt = prompt
        self.check_priv = check_priv
        self.enable_password = enable_password
        super().sshconnect(*args, username=username, password=password, **kwargs)

    # SSH object requires that the subclass define the object
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

        if self.prompt is None:
            self.prompt = self.set_base_prompt()
        s = None
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
        if self.check_priv and not self.check_enable_mode():
            self.


    def _send(self, cmd, tprompt=None):

        """
        Send constructed command message to device

        Any exceptions returned by ncssh.rpexpect are reraised


        """
        prompt = self.prompt
        if tprompt is not None:
            prompt = tprompt

        # send message to server
        self.logger.debug(
            "SSHInteractive Send: Sending command {} to device {}: waiting for {}".format(cmd, self.host, prompt))
        self.send(cmd.strip() + '\n')

        # wait for response from server
        self.logger.debug("Waiting for response from device {} ".format(self.host))
        response = None
        try:
            response = self.rpexpect(prompt)
            self.logger.debug("SSHInteractive Send: response from device {}: {}".format(self.host, response))
        except socket.timeout:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error(
                "SSHInteractive Send: Socket timeout waiting for response to {} to {}".format(cmd, self.host))
            self.logger.debug(
                "SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            raise
        except nxos_XML_errors.TimeoutExpiredError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error(
                "SSHInteractive Send: Loop timeout waiting for response to {} to {}".format(cmd, self.host))
            self.logger.debug(
                "SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            raise
        except nxos_XML_errors.ServerClosedChannelError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error(
                "SSHInteractive Send: Server closed channel while waiting for response to {} to {}".format(cmd,
                                                                                                           self.host))
            self.logger.debug(
                "SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            self.close()
            # do not propagate exception, closesession will raise one
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.error(
                "SSHInteractive Send: Unexpected error while waiting for response to {} to {}".format(cmd, self.host))
            self.logger.debug(
                "SSHInteractive Send: receive message from device {}: {}".format(str(response), self.host))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            raise

        # parse response and check for errors
        self.logger.debug("SSHInteractive Send: Received respone {}".format(response))
        if re.search('ERROR', response):
            self.logger.error(
                "SSHInteractive Send: Error at :  " + self.host + " while running :  " + cmd + "  Output:  " + response + "\n")
        return response

    def ssh_cmd_run(self, cmdlist):
        buff = ''
        if isinstance(cmdlist, str):
            cmdlist = [cmdlist]
        self.logger.debug("SSHInteractive ssh_cmd_run: Command list for device {}: {}".format(self.host, str(cmdlist)))
        try:
            if self.type == 'Cisco':
                self.logger.debug(
                    "SSHInteractive ssh_cmd_run: Sending command 'term len 0' to device {}".format(self.host))
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
            # if OPTS['cisco']:
            for cmd, prompt in cmdlist:
                response = self._send(cmd, prompt)
                self.logger.debug("SSHInteractive ssh_cmd_action: Sending " + cmd + " on " + self.host)
                self.logger.debug("SSHInteractive ssh_cmd_action: Waiting for {} on {} ".format(prompt, self.host))
                self.logger.debug("SSHInteractive ssh_cmd_action: Response " + response)
                buff += response
        except:
            raise
        self.logger.debug("SSHInteractive ssh_cmd_action: Sending response {}".format(buff))
        return buff

    def ssh_cmd_set(self, cmdlist, prompt=r'[^\(\)]#'):
        """

        :param cmdlist:
        :param base_prompt:
        :return:
        """


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
            self.logger.debug(
                "SSHInteractive ssh_parse_test: " + self.host + " - Testng {} {}".format(response, parselist[cmdr]))
            parseresult = response
            if parselist[cmdr] is not None:
                parseresult = commandparse(Configparse(response), parselist[cmdr])
                self.logger.debug("SSHInteractive ssh_parse_test: result of testing: {}".format(str(parseresult)))
                for result in parseresult.values():
                    if (False in result) or (None in result) or ('Error' in result):
                        self.logger.error(
                            "SSHInteractive ssh_parse_test: {} has failed this test. Result {} for cmdr {}".format(
                                self.host, result, cmdr))
                        passed = False
            parseresults[cmdr] = parseresult
        return passed, parseresults

    def set_base_prompt(self, pri_prompt_terminator='#',
                        alt_prompt_terminator='>', delay_factor=1):
        """Sets self.base_prompt
        Used as delimiter for stripping of trailing prompt in output.
        Should be set to something that is general and applies in multiple contexts. For Cisco
        devices this will be set to router hostname (i.e. prompt without '>' or '#').
        This will be set on entering user exec or privileged exec on Cisco, but not when
        entering/exiting config mode.
        :param pri_prompt_terminator: Primary trailing delimiter for identifying a device prompt
        :type pri_prompt_terminator: str
        :param alt_prompt_terminator: Alternate trailing delimiter for identifying a device prompt
        :type alt_prompt_terminator: str
        :param delay_factor: See __init__: global_delay_factor
        :type delay_factor: int
        """
        prompt = self.find_prompt(delay_factor=delay_factor)
        if not prompt[-1] in (pri_prompt_terminator, alt_prompt_terminator):
            raise ValueError("Router prompt not found: {0}".format(repr(prompt)))
        # Strip off trailing terminator
        self.base_prompt = prompt[:-1]
        return self.base_prompt

    def find_prompt(self, delay_factor=1):
        """Finds the current network device prompt, last line only.
        :param delay_factor: See __init__: global_delay_factor
        :type delay_factor: int
        """
        self.send("\n")
        time.sleep(delay_factor * .1)
        prompt = self._channel.recv(9999)
        # Check if the only thing you received was a newline
        count = 0
        prompt = prompt.strip()
        while count <= 10 and not prompt:
            prompt = self._channel.recv(9999).strip()
            if not prompt:
                prompt = self._send("\n")
                time.sleep(delay_factor * .1)
            count += 1

        # If multiple lines in the output take the last line
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Unable to find prompt: {}".format(prompt))
        return prompt

    def check_enable_mode(self, check_string=CISCO_PRIV_PROMPT):
        """Check if in enable mode. Return boolean.
        :param check_string: Identification of privilege mode from device
        :type check_string: str
        """
        self.send("\n")
        output = self._channel.recv(9999).strip()
        if not output:
            output = self._channel.recv(9999).strip()
        return check_string in output

    def enable(self, cmd='enable', pattern='ssword', re_flags=re.IGNORECASE):
        """Enter enable mode.
        :param cmd: Device command to enter enable mode
        :type cmd: str
        :param pattern: pattern to search for indicating device is waiting for password
        :type pattern: str
        :param re_flags: Regular expression flags used in conjunction with pattern
        :type re_flags: int
        """
        output = ""
        msg = "Failed to enter enable mode. Please ensure you pass " \
              "the 'secret' argument to ConnectHandler."
        if not self.check_enable_mode():
            try:
                combined_pattern = r"{}|{}".format(self.prompt + "#", pattern)
                output = self.rpexpect(reguexp=combined_pattern)
                if pattern in output:
                    output = self._send(self.enable_password, tprompt="{}#".format(self.prompt))
            except:
                self.logger.error(msg)
                raise ValueError(msg)
            if not self.check_enable_mode():
                self.logger.error(msg)
                raise ValueError(msg)
        return output

    def exit_enable_mode(self, exit_command='disable'):
        """Exit enable mode.
        :param exit_command: Command that exits the session from privileged mode
        :type exit_command: str
        """
        output = ""
        if self.check_enable_mode():
            self.write_channel(self.normalize_cmd(exit_command))
            output += self.read_until_prompt()
            if self.check_enable_mode():
                raise ValueError("Failed to exit enable mode.")
        return output

    def check_config_mode(self, check_string='', pattern=''):
        """Checks if the device is in configuration mode or not.
        :param check_string: Identification of configuration mode from the device
        :type check_string: str
        :param pattern: Pattern to terminate reading of channel
        :type pattern: str
        """
        self.write_channel(self.RETURN)
        # You can encounter an issue here (on router name changes) prefer delay-based solution
        if not pattern:
            output = self._read_channel_timing()
        else:
            output = self.read_until_pattern(pattern=pattern)
        return check_string in output

    def config_mode(self, config_command='', pattern=''):
        """Enter into config_mode.
        :param config_command: Configuration command to send to the device
        :type config_command: str
        :param pattern: Pattern to terminate reading of channel
        :type pattern: str
        """
        output = ''
        if not self.check_config_mode():
            self.write_channel(self.normalize_cmd(config_command))
            output = self.read_until_pattern(pattern=pattern)
            if not self.check_config_mode():
                raise ValueError("Failed to enter configuration mode.")
        return output

    def exit_config_mode(self, exit_config='', pattern=''):
        """Exit from configuration mode.
        :param exit_config: Command to exit configuration mode
        :type exit_config: str
        :param pattern: Pattern to terminate reading of channel
        :type pattern: str
        """
        output = ''
        if self.check_config_mode():
            self.write_channel(self.normalize_cmd(exit_config))
            output = self.read_until_pattern(pattern=pattern)
            if self.check_config_mode():
                raise ValueError("Failed to exit configuration mode")
        log.debug("exit_config_mode: {}".format(output))
        return output
