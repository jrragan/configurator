import logging
import multiprocessing
import time
from copy import deepcopy

from configure import configure_device
from configure_threading import thread_this

logger = logging.getLogger('configure_multi_config')



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
    results = thread_this(configure_device, max_threads=num_threads, args=device_vars)
    print("{} threads total time : {}".format(num_threads, time.time() - start))

    print(results)
