import functools
import logging
import multiprocessing
import random
import sys
import time
import traceback

from SSHInteractive import SSHInteractive
from configure_threading import thread_this

logger = logging.getLogger('configure')


def configure_device(device, user=None, passwd=None, enable_passwd=None, prompt=None, check_priv=True,
                     checkdict={"show version": None}, actionlist=None, action_config=True, cfg_cmd_set=None):
    """

    :param prompt:
    :param cfg_cmd_set:
    :param action_config:
    :param device:
    :param user:
    :param passwd:
    :param actionlist:
    :param checkdict:
    :param enable_passwd: str, enable password
    :param check_priv: if True, check if in privilege mode and attempt to put into privilege mode
    :return:
    """
    time.sleep(3 * random.random())
    device = device.strip()
    logger.info(device)
    logger.info("=" * 40)

    this_action_list = []

    # SSH
    try:
        devob = SSHInteractive()
        logger.info('Making ssh connection to {}'.format(device))
        devob.sshconnect(device, prompt=prompt, username=user, password=passwd, check_priv=check_priv,
                         enable_passwd=enable_passwd)
    except Exception as exc:
        logger.info("Exception encountered during SSH to device {}".format(device))
        logger.debug(exc)
        return device, None, exc
    action_response, cmd_response, check_response, result, check_outputs = None, None, None, None, None
    if devob.sshconnected:
        try:
            if actionlist is not None:
                logger.info("Action!!!!! for device {}".format(device))
                action_response = devob.ssh_cmd_action(this_action_list, replace_prompt=True, config=action_config)
                logger.debug("action responsed for {}: {}".format(device, action_response))
            if cfg_cmd_set is not None:
                logger.info("Config Set!!!!! for device {}".format(device))
                cmd_response = devob.ssh_config_cmd_set(cfg_cmd_set)
                logger.debug("action responsed for {}: {}".format(device, cmd_response))
            logger.info("Check!!!! for device {}".format(device))
            passed, check_response, check_outputs = devob.ssh_parse_test(checkdict)
            logger.info("Check response for {}: {}".format(device, check_response))
            result = device, True, check_response
            if not passed:
                logger.info("{} has failed testing. ".format(device))
                result = device, False, check_response
        except Exception as exc:
            logger.error("Exception encountered while sending commands to device {}".format(device))
            logger.debug(exc)
            message = exc
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if "Invalid input detected at" in str(exc_value):
                message = "exc: {}, Error on device: {}".format(exc, exc_value)
            return device, None, message
    response_filename = device + time.strftime("_%y%m%d%H%M%S", time.gmtime()) + '.txt'
    try:
        with open(response_filename, 'wt') as logs:
            if actionlist is not None: logs.write(action_response)
            if cfg_cmd_set is not None: logs.write(cmd_response)
            logs.write(check_outputs)
            logs.write("\nResult: {}".format(result))

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stacktrace = traceback.extract_tb(exc_traceback)
        logger.debug(sys.exc_info())
        logger.debug(stacktrace)
        logger.debug("For some reason the output file, " + response_filename + " for " + device + " cannot be created.")
    logger.debug("result: {}".format(result))
    return result


if __name__ == "__main__":
    LOGFILE = "configure" + time.strftime("_%y%m%d%H%M%S", time.gmtime()) + ".log"
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
    actionlist = [('config t', r'\(config\)#'), ('authentication mac-move permit', r'\(config\)#'), ('end', '#'),
                  ('wr mem', '#')]
    checkdict = {'show run | in authentication mac-move': {'existl': [r'authentication mac-move permit']}}
    username = 'username'
    password = 'password'

    change_mac_partial = functools.partial(configure_device, user=username, passwd=password, checkdict=checkdict,
                                           actionlist=actionlist)
    num_threads = min(len(devices), multiprocessing.cpu_count() * 4)

    start = time.time()
    results = thread_this(change_mac_partial, devices, max_threads=num_threads)
    print("{} threads total time : {}".format(num_threads, time.time() - start))

    print(results)

    print("The following devices failed:")
    for device, result, cause in results:
        if not result:
            print("{}\t\t{}".format(device, cause))
