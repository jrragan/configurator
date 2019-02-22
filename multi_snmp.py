import logging
import multiprocessing
import time
from pprint import pprint

from configure import configure_device
from configure_threading import thread_this

logger = logging.getLogger('multi_snmp')


def generate_snmp(store):
    cmd_list = ['snmp-server community public RO', 'snmp-server trap-source GigabitEthernet1',
                'snmp-server host 10.10.10.10 vrf mgmt public', 'snmp-server host 11.11.11.11 vrf mgmt public',
                'snmp-server host 12.12.12.12 vrf mgmt public', ]
    rtr1_cmd_list = cmd_list + ['snmp-server chassis-id "{}"'.format('rtr1_' + store.strip().lower() + '_CSR1K'), ]
    rtr2_cmd_list = cmd_list + ['snmp-server chassis-id "{}"'.format('rtr2_' + store.strip().lower() + '_CSR2K'), ]

    return rtr1_cmd_list, rtr2_cmd_list


if __name__ == "__main__":
    LOGFILE = "snmp_config" + time.strftime("_%y%m%d%H%M%S", time.gmtime()) + ".log"
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

    stores = [('st1111', '172.16.1.110'), ('st2222', '172.16.1.111')]
    checkdict = {'show run | in snmp': {
        'existl': [r'snmp-server trap-source GigabitEthernet1', r'snmp-server community public RO',
                   r'snmp-server host 10.10.10.10 vrf mgmt public', 'snmp-server host 11.11.11.11 vrf mgmt public',
                   r'snmp-server host 12.12.12.12 vrf mgmt public', r'rtr\d_st\d\d\d\d_CSR']}}
    device_vars = {}
    # with open("device_file.txt") as f:
    #     for device in f.readline():
    #         actionlist_dev = actionlist[:]
    #         actionlist_dev[2][0] = actionlist_dev[2][0].format(device)
    #         checkdict_dev = deepcopy(checkdict)
    #         checkdict_dev['show run | in snmp']['existl'][0] = r'snmp-server chassis-id {}'.format(device)
    #         device_vars[device] = {'username': 'username', 'password': 'password',
    #                                'actionlist': actionlist_dev, 'checkdict': checkdict_dev}
    for store, ip in stores:
        device_vars[ip] = {'user': 'cisco',
                           'passwd': 'cisco',
                           'cfg_cmd_set': generate_snmp(store)[0],
                           'checkdict': checkdict}
    print(device_vars)

    num_threads = min(len(device_vars), multiprocessing.cpu_count() * 4)

    start = time.time()
    results = thread_this(configure_device, max_threads=num_threads, args=device_vars)
    print("{} threads total time : {}".format(num_threads, time.time() - start))

    pprint(results)

    print("\nThe following devices failed:")
    for device, result, cause in results:
        if not result:
            print("{}\t\t{}".format(device, cause))
