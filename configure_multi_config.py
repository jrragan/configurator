import logging
import multiprocessing
import random
import sys
import time
import traceback
from copy import deepcopy

from SSHInteractive import SSHInteractive
from configure_threading import thread_this

logger = logging.getLogger('configure_multi_config')


def change_device_config(device, user="user", passwd="password", checkdict={"show version": None},
                         actionlist=None, command_timeout=30):
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
    if not device.lower().endswith(".example.com"):
        preprompt = device
        prompt = device.strip() + "#"
        device = preprompt + ".example.com"
    else:
        preprompt = device.replace('example.com', '')
        prompt = preprompt + "#"
    logger.debug(prompt)
    devob = SSHInteractive(device, prompt)
    this_action_list = []

    # Replace prompts in actionlist with actual device prompts
    if actionlist is not None:
        for command, prompt in actionlist:
            this_action_list.append((command, preprompt + prompt))
        logger.debug("New action list {}".format(this_action_list))

    # SSH
    try:
        logger.info('Making ssh connection to {}'.format(device))
        devob.sshconnect(username=user, password=passwd, command_timeout=command_timeout)
    except Exception as exc:
        logger.info("Exception encountered during SSH to device {}".format(device))
        logger.debug(exc)
        return device, None, exc
    action_response = check_response = result = None
    if devob.sshconnected:
        try:
            if actionlist is not None:
                logger.info("Action!!!!! for device {}".format(device))
                action_response = devob.ssh_cmd_action(this_action_list)
                logger.debug("action response for {}: {}".format(device, action_response))
            logger.info("Check!!!! for device {}".format(device))
            passed, check_response = devob.ssh_parse_test(checkdict)
            logger.info("Check response for {}: {}".format(device, check_response))
            result = device, True, check_response
            if not passed:
                logger.info("{} has failed testing. ".format(device))
                result = device, False, check_response
        except Exception as exc:
            logger.error("Exception encountered while sending commands to device {}".format(device))
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
    logger.debug("configure_device: ".format(result))
    return result


if __name__ == "__main__":
    LOGFILE = "multi_config" + time.strftime("_%y%m%d%H%M%S", time.gmtime()) + ".log"
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

    actionlist = [('config t', r'\(config\)#'), ['snmp-server chassis-id {}', r'\(config\)#'], ('end', '#'),
                  ('wr mem', '#')]
    checkdict = {'show run | in snmp': {'existl': [r'snmp-server chassis-id {}']}}
    device_vars = {}
    with open("device_file.txt") as f:
        for device in f.readline():
            actionlist_dev = actionlist[:]
            actionlist_dev[2][0] = actionlist_dev[2][0].format(device)
            checkdict_dev = deepcopy(checkdict)
            checkdict_dev['show run | in snmp']['existl'][0] = r'snmp-server chassis-id {}'.format(device)
            device_vars[device] = {'username': 'username', 'password': 'password',
                                   'actionlist': actionlist_dev, 'checkdict': checkdict_dev}
    print(device_vars)

    username = 'username'
    password = 'password'

    num_threads = min(len(device_vars), multiprocessing.cpu_count() * 4)

    start = time.time()
    results = thread_this(change_device_config, max_threads=num_threads, args=device_vars)
    print("{} threads total time : {}".format(num_threads, time.time() - start))

    print(results)
