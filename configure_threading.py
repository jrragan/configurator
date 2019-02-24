import concurrent.futures
import logging
import multiprocessing
import sys
import traceback

__version__ = '2019.02.22.1'

logger = logging.getLogger('configure_threading')


def wait_for(futures, timeout=None):
    """

    :param timeout:
    :param futures:
    :return:
    """
    canceled = False
    results = []
    logger.info("Waiting for threading to complete...")
    try:
        for future in concurrent.futures.as_completed(futures):
            try:
                err = future.exception(timeout=timeout)
                if err is None:
                    result = future.result(timeout=timeout)
                    logger.debug("Result: {}".format(result))
                    if result is None:
                        logger.error("Problem with result...")
                    results.append(result)
                else:
                    logger.debug("Exception: ".format(err))
                    results.append("Error: future.exception: {}".format(err))
            except TimeoutError as err:
                logger.error("Timeout waiting for exception or for result.")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stacktrace = traceback.extract_tb(exc_traceback)
                logger.debug(sys.exc_info())
                logger.debug(stacktrace)
                results.append("Error: Timeout: {}".format(err))
            except:
                logger.error("Unhandled exception waiting for fn in thread to complete.")
                exc_type, exc_value, exc_traceback = sys.exc_info()
                stacktrace = traceback.extract_tb(exc_traceback)
                logger.debug(sys.exc_info())
                logger.debug(stacktrace)
                results.append("Error: {}".format(exc_type))
    except KeyboardInterrupt:
        logger.info(" cancelling...")
        canceled = True
        for future in futures:
            future.cancel()
    return canceled, results


def thread_this(fn, vars=None, args=None, max_threads=multiprocessing.cpu_count(), timeout=None):
    """

    :type args: dict
    :param args: dictionary with with keyword arguments to pass to fn. The key is the corresponding var
    :param fn: function object
    :param vars: list of positional arguments to pass to fn
    :param max_threads:
    :param timeout:
    :return:
    """
    logger.info(" starting multithreading: pool of {}".format(max_threads))
    futures = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        if vars and args:
            for var in vars:
                future = executor.submit(fn, var, **args[var])
                futures.add(future)
            canceled, results = wait_for(futures, timeout=timeout)
            if canceled:
                logger.info("Cancelled...")
                executor.shutdown()
        elif vars:
            for var in vars:
                future = executor.submit(fn, var)
                futures.add(future)
            canceled, results = wait_for(futures, timeout=timeout)
            if canceled:
                logger.info("Cancelled...")
                executor.shutdown()
        elif args:
            for arg in args:
                future = executor.submit(fn, arg, **args[arg])
                futures.add(future)
            canceled, results = wait_for(futures, timeout=timeout)
            if canceled:
                logger.info("Cancelled...")
                executor.shutdown()
        else:
            raise ValueError("Either args or vars (or both) must be specified")

    logger.info(
        " ran {} devices using {} threads{}".format(len(futures), max_threads, " [canceled]" if canceled else ""))
    return results
