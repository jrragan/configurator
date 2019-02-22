Python 3 and Paramiko required

# configurator

### Example

configure.py and check_for_cable_errors.py are examples for using the other modules.

From configure.py, the other modules are imported

```Python
  from SSHInteractive import SSHInteractive
  from configure_threading import thread_this
```
  
The first is a wrapper for Paramiko which returns a shell for running an interactive session.

The work is done in the change_mac function. It's purpose is to impement the following config on multiple 3850 switch stacks

```
    switch1#config t
    Enter configuration commands, one per line.  End with CNTL/Z.
    switch1#(config)#authentication mac-move permit
    switch1#(config)#end
```
  
and then test that the configuration was applied

```
    switch1##show run | in authentication mac-move
    authentication mac-move permit
    switch1##wr mem
```

The function is called "change_mac" but it is not limited to that purpose. It can be used to do any similar set of configuration
changes and post-change checks.
  
The function

```Python
    def change_mac(device, user="user", passwd="password", checkdict={"show version" : None}, actionlist=None):
```

is called with several parameters. The device to act on, username and password, a dictionary containing the instructions for testing 
that the configuraton was done and a list of expect-like command, prompt tuples.

```Python
    actionlist = [('config t', r'\(config\)#'), ('authentication mac-move permit', r'\(config\)#'), ('end', '#'), ('wr mem', '#')]
    checkdict = {'show run | in authentication mac-move' : {'existl' : [r'authentication mac-move permit']}}
 ```
 
When run with multi-threading, the following command keeps dozens of devices from hitting the tacacs server at the same time

```Python
    time.sleep(3 * random.random())
```  
The next block of commands normalizes the device name

```Python
    device = device.strip()
    logger.info(device)
    logger.info("="*40)
    #Set up prompts
    if not device.lower().endswith(".example.com"):
        preprompt = device
        prompt = device.strip() + "#"
        device = preprompt + ".example.com"
    else:
        preprompt = device.replace('example.com', '')
        prompt = preprompt + "#"
    logger.debug(prompt)
```

We create the SSH shell object

```Python
    devob = SSHInteractive(device, prompt)
```  
Now we log in to the device

```Python
    try:
        logger.info('Making ssh connection to {}'.format(device))
        devob.sshconnect(username=user, password=passwd)
    except Exception as exc:
        logger.info("Exception encountered during SSH to device {}".format(device))
        logger.debug(exc)
        return device, None, exc
```        
If the connection is successful, we run the commands in the action list using the "ssh_cmd_action" method. After the configuration, we test with the "ssh_parse_test" method. The results are logged.

The main method creates a partial function, but this is optional.

```Python
    username = 'username'
    password = 'password'

    change_mac_partial = functools.partial(change_mac, user=username, passwd=password, checkdict=checkdict, actionlist=actionlist)
    num_threads = min(len(devices), multiprocessing.cpu_count() * 4)

    start = time.time()
    results = thread_this(change_mac_partial, devices, max_threads=num_threads)
```
The multithreading is done with concurrent.futures. The task is started by passing the partial function, the device list and the max threads parameter to the "thread_this" function. Since this task is IO bound, the num_threads can be very large. It has been tested up to 80 threads. 

### Example 2 - show_ver.py

The module show_ver.py contains the `simple_configure` function which is functionally identical to the `change_mac` function. 

```Python
devices = """172.16.1.139
""".splitlines()
    print(devices)
    username = 'cisco'
    password = 'cisco'

    simple_configure_partial = functools.partial(simple_configure, prompt="csr1000v-1#", user=username, passwd=password)
    num_threads = min(len(devices), multiprocessing.cpu_count() * 4)

    start = time.time()
    results = thread_this(simple_configure_partial, devices, max_threads=num_threads)
    print("{} threads total time : {}".format(num_threads, time.time() - start))

    print(results)
    #print(results[0][2]['show version'])
    ver = re.search(r"Cisco .*, +Version +(\S*)", results[0][2]['show version']).group(0)
    print(ver)
 ```
In this example we want to get the show versions from a list of devices and then parses out IOS-XE version. After running we get the following output.

```Python
1 threads total time : 1.620133638381958

[('172.16.1.179', True, {'show version': 'show version\r\nCisco IOS XE Software, Version 16.05.01b\r\nCisco IOS Software [Everest], Virtual XE Software (X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 16.5.1b, RELEASE SOFTWARE (fc1)\r\nTechnical Support: http://www.cisco.com/techsupport\r\nCopyright (c) 1986-2017 by Cisco Systems, Inc.\r\nCompiled Tue 11-Apr-17 16:41 by mcpre\r\n\r\n\r\nCisco IOS-XE software, Copyright (c) 2005-2017 by cisco Systems, Inc.\r\nAll rights reserved.  Certain components of Cisco IOS-XE software are\r\nlicensed under the GNU General Public License ("GPL") Version 2.0.  The\r\nsoftware code licensed under GPL Version 2.0 is free software that comes\r\nwith ABSOLUTELY NO WARRANTY.  You can redistribute and/or modify such\r\nGPL code under the terms of GPL Version 2.0.  For more details, see the\r\ndocumentation or "License Notice" file accompanying the IOS-XE software,\r\nor the applicable URL provided on the flyer accompanying the IOS-XE\r\nsoftware.\r\n\r\n\r\nROM: IOS-XE ROMMON\r\n\r\ncsr1000v-1 uptime is 10 minutes\r\nUptime for this control processor is 12 minutes\r\nSystem returned to ROM by reload\r\nSystem image file is "bootflash:packages.conf"\r\nLast reload reason: Reload Command\r\n\r\n\r\n\r\nThis product contains cryptographic features and is subject to United\r\nStates and local country laws governing import, export, transfer and\r\nuse. Delivery of Cisco cryptographic products does not imply\r\nthird-party authority to import, export, distribute or use encryption.\r\nImporters, exporters, distributors and users are responsible for\r\ncompliance with U.S. and local country laws. By using this product you\r\nagree to comply with applicable laws and regulations. If you are unable\r\nto comply with U.S. and local laws, return this product immediately.\r\n\r\nA summary of U.S. laws governing Cisco cryptographic products may be found at:\r\nhttp://www.cisco.com/wwl/export/crypto/tool/stqrg.html\r\n\r\nIf you require further assistance please contact us by sending email to\r\nexport@cisco.com.\r\n\r\nLicense Level: ax\r\nLicense Type: Default. No valid license found.\r\nNext reload license Level: ax\r\n\r\ncisco CSR1000V (VXE) processor (revision VXE) with 1126522K/3075K bytes of memory.\r\nProcessor board ID 9DEXZKU69XK\r\n1 Gigabit Ethernet interface\r\n32768K bytes of non-volatile configuration memory.\r\n3018840K bytes of physical memory.\r\n7774207K bytes of virtual hard disk at bootflash:.\r\n0K bytes of WebUI ODM Files at webui:.\r\n\r\nConfiguration register is 0x2102\r\n\r\ncsr1000v-1#'})]

Cisco IOS XE Software, Version 16.05.01b
```

### Example 3 - Pushing out a device specific configuration to a set of devices

```import logging
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
```

This configuration builds a unique configuration for every device. The configure_device function is a generic function allowing you to do a number of configurations and post-configuration checks. In this case, we are using a new capability that allows us to provide a list of configuration commands and have the backend automatically detect the prompt, go to enable mode if necessary and go to configuration mode. It then automatically does the desired expect functionaly for each command. 

In this example, one device would not accept three of the commands. The other device rejected connection attempts. The output is

```
2 threads total time : 3.744600772857666
[('172.16.1.110',
  False,
  {'show run | in snmp': {'existl': [True, True, False, False, False, True]}}),
 ('172.16.1.111',
  None,
  NoValidConnectionsError(None, 'Unable to connect to port 22 on 172.16.1.111'))]
The following devices failed:
172.16.1.110		{'show run | in snmp': {'existl': [True, True, False, False, False, True]}}
172.16.1.111		[Errno None] Unable to connect to port 22 on 172.16.1.111
```
