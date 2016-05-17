import functools
import logging
import multiprocessing
import random
import re
import time

import sys
import traceback

from SSHInteractive import SSHInteractive
from configure_threading import thread_this

logger = logging.getLogger('check_for_cable_errors')


def get_switch_members(output):
    logger.debug('Gathering switch stack members')
    switches = []
    for line in output.splitlines():
        m = re.match('.([0-9]) .*(ctive|tandby|ember).*$', line)
        if m:
            switches.append(m.group(1))

    return switches


def check_for_cable_errors(device, user="user", passwd="password", cmdlist1=[], cmdlist2=[]):
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
    logger.info("=" * 40)
    # Set up prompts
    if not device.lower().endswith(".homedepot.com"):
        preprompt = device
        prompt = device.strip() + "#"
        device = preprompt + ".homedepot.com"
    else:
        preprompt = device.replace('homedepot.com', '')
        prompt = preprompt + "#"
    logger.debug(prompt)
    devob = SSHInteractive(device, prompt)

    # SSH
    try:
        logger.info('Making ssh connection to {}'.format(device))
        devob.sshconnect(username=user, password=passwd)
    except Exception as exc:
        logger.info("Exception encountered during SSH to device {}".format(device))
        logger.debug(exc)
        return device, None, exc
    if devob.sshconnected:
        try:
            result_cmdlist1 = devob.ssh_cmd_run(cmdlist1)
            switches = get_switch_members(result_cmdlist1)
            errors = {}
            for switch in switches:
                result_errors = devob.ssh_cmd_run('show platform port-asic 0 read register SifRacRwCrcErrorCnt switch ' + switch)
                errors[switch] = result_errors
                logger.debug("device {} switch {} error result {}".format(device, switch, result_errors))
            result_cmdlist2 = devob.ssh_cmd_run(cmdlist2)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = traceback.extract_tb(exc_traceback)
            logger.error(sys.exc_info())
            logger.error(stacktrace)
            logger.critical("Exception encountered while sending commands to device {}".format(device))
            return [device, None, sys.exc_info()]
    response_filename = device + time.strftime("_%y%m%d%H%M%S", time.gmtime()) + '.txt'
    try:
        with open(response_filename, 'wt') as logs:
            logs.write(result_cmdlist1)
            logs.write("\n\n", str(errors))
            logs.write("\n\n", result_cmdlist2)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stacktrace = traceback.extract_tb(exc_traceback)
        logger.error(sys.exc_info())
        logger.error(stacktrace)
        logger.critical("For some reason the output file, " + response_filename + " for " + device + " cannot be created.")



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
    dvaswshm1.dv9119#config t
Enter configuration commands, one per line.  End with CNTL/Z.
dvaswshm1.dv9119(config)#authentication mac-move permit
dvaswshm1.dv9119(config)#end

dvaswshm1.dv9119#show run | in authentication mac-move
authentication mac-move permit
dvaswshm1.dv9119#wr mem
"""

    devices = """switch1
    switch2
    switch3
""".splitlines()
    print(devices)
    username = 'username'
    password = 'password'

    cmd_list1 = ["show switch"]
    cmd_list2 = ["show clock", "show switch stack-ports", "show switch stack-ports summ"]

    check_for_cable_errors_partial = functools.partial(check_for_cable_errors, user=username, passwd=password, cmdlist1=cmd_list1,
                                           cmdlist2=cmd_list2)
    num_threads = min(len(devices), multiprocessing.cpu_count() * 4)

    start = time.time()
    results = thread_this(check_for_cable_errors_partial, devices, max_threads=num_threads)
    print("{} threads total time : {}".format(num_threads, time.time() - start))

    print(results)

