import functools
import logging
import multiprocessing
import random
import time

import sys
import traceback

from SSHInteractive import SSHInteractive
from configure_threading import thread_this

logger = logging.getLogger('configure')

def change_mac(device, user="user", passwd="password", checkdict={"show version" : None}, actionlist=None):
    """

    :param device:
    :param user:
    :param passwd:
    :param actionlist:
    :param checkdict:
    :return:
    """
    time.sleep(3 * random.random())
    device = device.strip()
    logger.info(device)
    logger.info("="*40)
    #Set up prompts
    if not device.lower().endswith(".homedepot.com"):
        preprompt = device
        prompt = device.strip() + "#"
        device = preprompt + ".homedepot.com"
    else:
        preprompt = device.replace('homedepot.com', '')
        prompt = preprompt + "#"
    logger.debug(prompt)
    devob = SSHInteractive(device, prompt)
    this_action_list = []

    #Replace prompts in actionlist with actual device prompts
    if actionlist is not None:
        for command, prompt in actionlist:
            this_action_list.append((command, preprompt + prompt))
        logger.debug("New action list {}".format(this_action_list))

    #SSH
    try:
        logger.info('Making ssh connection to {}'.format(device))
        devob.sshconnect(username=user, password=passwd)
    except Exception as exc:
        logger.info("Exception encountered during SSH to device {}".format(device))
        logger.debug(exc)
        return device, None, exc
    if devob.sshconnected:
        try:
            if actionlist is not None:
                logger.info("Action!!!!! for device {}".format(device))
                action_response = devob.ssh_cmd_action(this_action_list)
                logger.debug("action responsed for {}: {}".format(device, action_response))
            logger.info("Check!!!! for device {}".format(device))
            passed, check_response = devob.ssh_parse_test(checkdict)
            logger.info("Check response for {}: {}".format(device, check_response))
            result = device, True, check_response
            if not passed:
                logger.info("{} has failed testing. ".format(device))
                result = device, False, check_response
        except Exception as exc:
            logger.info("Exception encountered while sending commands to device {}".format(device))
            logger.debug(exc)
            return device, None, exc
    response_filename = device + time.strftime("_%y%m%d%H%M%S", time.gmtime()) + '.txt'
    try:
        with open(response_filename, 'wt') as logs:
            if actionlist is not None: logs.write(action_response)
            logs.write("change mac response: ".format(str(check_response)))
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stacktrace = traceback.extract_tb(exc_traceback)
        logger.debug(sys.exc_info())
        logger.debug(stacktrace)
        logger.debug("For some reason the output file, " + response_filename + " for " + device + " cannot be created.")
    logger.debug("change mac result: ".format(result))
    return result


if __name__ == "__main__":
    LOGFILE = "cat3850macmove" + time.strftime("_%y%m%d%H%M%S", time.gmtime()) + ".log"
    SCREENLOGLEVEL = logging.DEBUG
    FILELOGLEVEL = logging.DEBUG
    format_string = '%(asctime)s: %(threadName)s - %(funcName)s - %(name)s - %(levelname)s - %(message)s'
    logformat = logging.Formatter(format_string)

    logging.basicConfig(level=FILELOGLEVEL,
                        format=format_string,
                        filename=LOGFILE)

    # screen handler
    ch = logging.StreamHandler()
    ch.setLevel(SCREENLOGLEVEL)
    ch.setFormatter(logformat)

    logging.getLogger('').addHandler(ch)

    logger = logging.getLogger('configurator')

    logger.critical("Started")

    """Config t
authentication mac-move permit
show run | in authentication
wr mem
exit"""

    """
    switch1#config t
Enter configuration commands, one per line.  End with CNTL/Z.
switch1#(config)#authentication mac-move permit
switch1#(config)#end

switch1##show run | in authentication mac-move
authentication mac-move permit
switch1##wr mem
"""

    devices = """switch1
    switch2
    switch3
""".splitlines()
    print(devices)
    actionlist = [('config t', r'\(config\)#'), ('authentication mac-move permit', r'\(config\)#'), ('end', '#'), ('wr mem', '#')]
    checkdict = {'show run | in authentication mac-move' : {'existl' : [r'authentication mac-move permit']}}
    username = 'username'
    password = 'password'

    change_mac_partial = functools.partial(change_mac, user=username, passwd=password, checkdict=checkdict, actionlist=None)
    num_threads = min(len(devices), multiprocessing.cpu_count() * 4)

    start = time.time()
    results = thread_this(change_mac_partial, devices, max_threads=num_threads)
    print("{} threads total time : {}".format(num_threads, time.time() - start))

    print(results)

