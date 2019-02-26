import getpass
import logging
import re
import socket
import sys
import traceback

import nxos_XML_errors
from command_parser import commandparse, ConfigParse
from ncssh import SshConnect

__version__ = '2019.02.25.2'

logger = logging.getLogger('sshinteractive')

CISCO_CONFIG_PROMPT = r"\(config\S*\)#"
CISCO_BASE_PROMPT = r'>'
CISCO_PRIV_PROMPT = r'#'
CISCO_COPY_CONFIG_SAVE_PATTERN = r"\[startup-config\]\?"


class SSHInteractive(SshConnect):
    """
    A subclass of NxosConnect that adds the ability to switch between VDCs

    This is only possible by ssh'ing to the cli, running the switchto vdc command and then dropping into the xml subsystem
    """

    def __init__(self):
        """

         A subclass of NxosConnect that adds the ability to switch between VDCs

        This is only possible by ssh'ing to the cli, running the switchto vdc command and then dropping into the xml subsystem



        """
        self.logger = logging.getLogger('SSHInteractive.SSHInteractive')
        self.logger.debug("Instantiating SSH object")

    def sshconnect(self, host, *args, prompt=None, username=None, password=None, type='Cisco', check_priv=True,
                   enable_password=None, command_timeout=10, log_session_file=None, log_file_mode='w', **kwargs):
        super().__init__(host)
        self.type = type
        self.prompt = prompt
        self.check_priv = check_priv
        self.enable_password = enable_password
        super().sshconnect(*args, username=username, password=password,
                           command_timeout=command_timeout, log_session_file=log_session_file,
                           log_file_mode=log_file_mode, **kwargs)

    # SSH object requires that the subclass define the object
    def setup_channel(self):
        """
        Activating an interactive shell for device
        """
        self.ssh_shell()
        self.look_for_prompt()
        if self.check_priv:
            try:
                self.enable()
            except:
                self.logger.error("SSHInteractive look_for_prompt: failed to elevate to privileged mode")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stacktrace = traceback.extract_tb(exc_traceback)
                self.logger.debug(sys.exc_info())
                self.logger.debug(stacktrace)
                self.close()
                raise

    def look_for_prompt(self):
        """
        Look for prompt from interactive shell
        @return:
        """

        if self.prompt is None:
            self.set_base_prompt()
        else:
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
                "SSHInteractive Send: receive message from device {}: {}".format(self.host, response))
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
        self.logger.debug("SSHInteractive Send: Received response {}".format(response))
        if re.search('ERROR', response):
            self.logger.error(
                "SSHInteractive Send: Error at :  " + self.host + " while running :  " + cmd + "  Output:  " + response + "\n")
            if 'Invalid input detected' in response:
                self.logger.error(
                    "SSHInteractive Send: Invalid Input detected on :  " + self.host + " while running :  " + cmd + "  Output:  " + response + "\n")
            if re.search(r"%\s*Error", response) or re.search(r"%\s*Invalid", response):
                self.logger.error(
                    "SSHInteractive Send: %Error detected on :  " + self.host + " while running :  " + cmd + "  Output:  " + response + "\n")
        return response

    def ssh_cmd_run(self, cmdlist, stop_on_error=False):
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
                self.logger.debug("SSHInteractive ssh_cmd_run: Received response " + response + " from " + self.host)
                buff += response
                if stop_on_error and (re.search(r"%\s*Invalid", response) or re.search(r"%\s*Error", response)):
                    self.logger.error("SSHInteractive ssh_cmd_action: Error Sending " + cmd + " on " + self.host)
                    self.logger.debug("SSHInteractive ssh_cmd_action: Response " + response)
                    raise ValueError("Error Sending " + cmd + " on " + self.host + ": command output " + response)
        except:
            raise
        self.logger.debug("SSHInteractive ssh_cmd_run: Sending response {}".format(buff))
        return buff

    def ssh_cmd_action(self, cmdlist, replace_prompt=False, config=True, stop_on_error=False, save_config=False,
                       prompt=""):
        this_action_list = []
        if replace_prompt and config:
            for command, prompt in cmdlist:
                this_action_list.append((command, CISCO_CONFIG_PROMPT))
        elif replace_prompt:
            for command, prompt in cmdlist:
                this_action_list.append((command, self.base_prompt + prompt))
            logger.debug("New action list {}".format(this_action_list))
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
                if stop_on_error and (re.search(r"%\s*Invalid", response) or re.search(r"%\s*Error", response)):
                    self.logger.error("SSHInteractive ssh_cmd_action: Error Sending " + cmd + " on " + self.host)
                    self.logger.debug("SSHInteractive ssh_cmd_action: Response " + response)
                    raise ValueError("Error Sending " + cmd + " on " + self.host + ": command output " + response)
            if save_config:
                self.exit_config_mode()
                self.save_config()
        except:
            raise
        self.logger.debug("SSHInteractive ssh_cmd_action: Sending response {}".format(buff))
        return buff

    def ssh_config_cmd_set(self, cmdlist, config_mode_command=None, stop_on_error=False, save_config=True, prompt=""):
        """

        :param config_mode_command:
        :param cmdlist: iterable with multiple configuration commands
        :param prompt:
        :return:
        """

        if cmdlist is None:
            return ''
        elif isinstance(cmdlist, str):
            cmdlist = (cmdlist,)

        if not hasattr(cmdlist, '__iter__'):
            raise ValueError("Invalid argument passed into ssh_config_cmd_set")

        self.enable()
        cfg_mode_args = (config_mode_command,) if config_mode_command else tuple()
        self.config_mode(*cfg_mode_args)
        if not prompt:
            prompt = self.prompt

        # Send config commands
        action_list = []
        for cmd in cmdlist:
            action_list.append((cmd, prompt))

        # Gather output
        output = ''
        try:
            output = self.ssh_cmd_action(action_list, stop_on_error=stop_on_error, save_config=save_config)
        except:
            self.logger.error("SSHInteractive ssh_config_cmd_set: error running command set")
            self.logger.debug("SSHInteractive ssh_config_cmd_set: error output {}".format(output))
            raise

        self.logger.debug("SSHInteractive ssh_config_cmd_set: output {}".format(output))

        # exit configuration mode
        self.exit_config_mode()

        return output

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
        command_outputs = ""
        for cmdr in parselist:
            self.logger.debug("SSHInteractive ssh_parse_test: Sending command {} to {}".format(cmdr, self.host))
            response = self.ssh_cmd_run(cmdr)
            self.logger.debug("SSHInteractive ssh_parse_test: " + self.host + " - Results of {}".format(response))
            self.logger.debug(
                "SSHInteractive ssh_parse_test: " + self.host + " - Testing {} {}".format(response, parselist[cmdr]))
            parseresult = response
            command_outputs += response
            if parselist[cmdr] is not None:
                parseresult = commandparse(ConfigParse(response), parselist[cmdr])
                self.logger.debug("SSHInteractive ssh_parse_test: result of testing: {}".format(str(parseresult)))
                for result in parseresult.values():
                    if (False in result) or (None in result) or ('Error' in result) or re.search(r"%\s*Invalid",
                                                                                                 response) or re.search(
                            r"%\s*Error", response):
                        self.logger.error(
                            "SSHInteractive ssh_parse_test: {} has failed this test. Result {} for cmdr {}".format(
                                self.host, result, cmdr))
                        self.logger.debug("SSHInteractive ssh_parse_test: command output: {}".format(response))
                        passed = False
            parseresults[cmdr] = parseresult
        if self.session_log:
            self.session_log.write("Test Result = {}\n".format(passed))
            self.session_log.write("Test Results: {}".format(parseresults))
        return passed, parseresults, command_outputs

    def set_base_prompt(self, pri_prompt_terminator='#',
                        alt_prompt_terminator='>'):
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
        """
        prompt = self.find_prompt()
        if not prompt[-1] in (pri_prompt_terminator, alt_prompt_terminator):
            raise ValueError("Router prompt not found: {0}".format(repr(prompt)))
        # Strip off trailing terminator
        self.prompt = prompt
        self.base_prompt = prompt[:-1]
        self.logger.debug(
            "SSHInteractive: set_base_prompt: prompt: {}, base_prompt: {}".format(self.prompt, self.base_prompt))
        return self.base_prompt

    def find_prompt(self):
        """Finds the current network device prompt, last line only.
        """
        self.send("\n")
        prompt = self.rpexpect('', code=5, timer=1.5)
        prompt = prompt.strip()
        # Check if the only thing you received was a newline

        # If multiple lines in the output take the last line
        prompt = prompt.strip().splitlines()[-1]
        if not prompt:
            raise ValueError("Unable to find prompt: {}".format(prompt))
        return prompt

    def check_enable_mode(self, check_string=CISCO_PRIV_PROMPT, pattern=''):
        """Check if in enable mode. Return boolean.
        :param pattern:
        :param check_string: Identification of privilege mode from device
        :type check_string: str
        """
        self.logger.info("Checking enable mode on device {}".format(self.host))
        return self._check_mode(check_string=check_string, pattern=pattern)

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
                combined_pattern = r"{}|{}".format(self.base_prompt + CISCO_PRIV_PROMPT, pattern)
                output = self._send(cmd, tprompt=combined_pattern)
                if pattern in output:
                    if self.enable_password is None:
                        self.enable_password = getpass.getpass("Enter enable password for " + self.username + " :  ")
                    output = self._send(self.enable_password,
                                        tprompt="{}{}".format(self.base_prompt, CISCO_PRIV_PROMPT))
            except:
                self.logger.error(msg)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stacktrace = traceback.extract_tb(exc_traceback)
                self.logger.debug(
                    "SSHInteractive enable: receive message from device {}: {}".format(str(output), self.host))
                self.logger.debug(sys.exc_info())
                self.logger.debug(stacktrace)
                raise
            if not self.check_enable_mode():
                self.logger.error(msg)
                raise ValueError(msg)
        self.prompt = self.base_prompt + CISCO_PRIV_PROMPT
        return output

    def exit_enable_mode(self, exit_command='disable'):
        """Exit enable mode.
        :param exit_command: Command that exits the session from privileged mode
        :type exit_command: str
        """

        output = ''
        if self.check_enable_mode():
            try:
                output = self._send(exit_command, tprompt=r"{}{}".format(self.base_prompt, CISCO_BASE_PROMPT))
                if self.check_enable_mode():
                    self.logger.error("Failed to exit enable mode.")
                    self.logger.debug("SSHInteractive exit_enable_mode: received output {}".format(output))
                    raise ValueError("Failed to exit enable mode.")
            except:
                self.logger.error("Failed to exit enable mode.")
                self.logger.debug("SSHInteractive exit_enable_mode: received output {}".format(output))
                raise
        self.prompt = self.base_prompt + CISCO_BASE_PROMPT
        return output

    def check_config_mode(self, check_string=CISCO_CONFIG_PROMPT, pattern=''):
        """Checks if the device is in configuration mode or not.
        :param check_string: Identification of configuration mode from the device
        :type check_string: str
        :param pattern: Pattern to terminate reading of channel
        :type pattern: str
        """

        self.logger.info("Checking config mode on device {}".format(self.host))
        return self._check_mode(check_string=check_string, pattern=pattern)

    def _check_mode(self, check_string=CISCO_CONFIG_PROMPT, pattern='', prompt_pattern=None):

        if prompt_pattern is None:
            r"{}|{}|{}".format(self.base_prompt, CISCO_BASE_PROMPT, CISCO_PRIV_PROMPT)
        output = ''
        try:
            if not pattern:
                output = self._send("\n",
                                    tprompt=prompt_pattern)
            else:
                output = self._send("\n", tprompt=pattern)
            self.logger.debug("SSHInteractive check__mode: output {}".format(output))
        except:
            self.logger.error("SSHInteractive check__mode: Error attempting to check configuration mode")
            self.logger.debug("SSHInteractive check__mode: output {}".format(output))
            raise
        if re.search(check_string, output):
            return True
        return False

    def config_mode(self, config_command='config term', pattern=''):
        """Enter into config_mode.
        :param config_command: Configuration command to send to the device
        :type config_command: str
        :param pattern: Pattern to terminate reading of channel
        :type pattern: str
        """
        output = ''
        if not pattern:
            pattern = CISCO_CONFIG_PROMPT
        if not self.check_config_mode():
            try:
                output = self._send(config_command, tprompt=pattern)
            except:
                self.logger.error("SSHInteractive config_mode: Failed to enter config mode")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stacktrace = traceback.extract_tb(exc_traceback)
                self.logger.debug(
                    "SSHInteractive config mode: receive message from device {}".format(str(output)))
                self.logger.debug(sys.exc_info())
                self.logger.debug(stacktrace)
                raise
            if not self.check_config_mode():
                self.logger.debug(
                    "SSHInteractive: config_mode: Failed to enter configuration mode: output {}".format(output))
                raise ValueError("Failed to enter configuration mode.")
        self.prompt = CISCO_CONFIG_PROMPT
        return output

    def exit_config_mode(self, exit_config='end', pattern=CISCO_PRIV_PROMPT):
        """Exit from configuration mode.
        :param exit_config: Command to exit configuration mode
        :type exit_config: str
        :param pattern: Pattern to terminate reading of channel
        :type pattern: str
        """
        output = ''
        if self.check_config_mode():
            try:
                output = self._send(exit_config, tprompt="{}{}".format(self.base_prompt, pattern))
                self.logger.debug("SSHInteractive exit_config_mode: output: {}".format(output))
            except:
                self.logger.error("SSHInteractive config_mode: Failed to exit config mode")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stacktrace = traceback.extract_tb(exc_traceback)
                self.logger.debug(
                    "SSHInteractive exit_config mode: receive message from device {}".format(str(output)))
                self.logger.debug(sys.exc_info())
                self.logger.debug(stacktrace)
                raise
            if self.check_config_mode():
                self.logger.error("Failed to exit configuration mode")
                raise ValueError("Failed to exit configuration mode")
        self.prompt = self.base_prompt + CISCO_PRIV_PROMPT
        return output

    def save_config(
            self,
            cmd="copy running-config startup-config",
            pat=CISCO_COPY_CONFIG_SAVE_PATTERN,
            verification=r"\[OK\]"):
        """Saves Config."""

        output = ''
        self.enable()
        pat = "{}|{}".format(pat, self.prompt)
        try:
            output = self._send(cmd, tprompt=pat)
            if re.search(CISCO_COPY_CONFIG_SAVE_PATTERN, output):
                output += self._send("\n")
        except:
            self.logger.error("SSHInteractive save_config: Error attempting to save configuration")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            self.logger.debug(
                "SSHInteractive save_config: receive message from device {}".format(str(output)))
            self.logger.debug(sys.exc_info())
            self.logger.debug(stacktrace)
            raise

        if not re.search(verification, output) or (
                re.search(r"%\s*Invalid", output) or re.search(r"%\s*Error", output)):
            raise ValueError(
                "An error occurred attempting to save the configuration: output returned: {}".format(output)
            )
        return output
