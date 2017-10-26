Python 3 and Paramiko required

# configurator

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
  r  esults = thread_this(change_mac_partial, devices, max_threads=num_threads)
```
The multithreading is done with concurrent.futures. The task is started by passing the partial function, the device list and the max threads parameter to the "thread_this" function. Since this task is IO bound, the num_threads can be very large. It has been tested up to 80 threads. 

