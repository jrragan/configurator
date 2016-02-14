import concurrent.futures
import logging
import multiprocessing

logger = logging.getLogger('multithreading')

def wait_for( futures):
    """

    :param futures:
    :return:
    """
    canceled = False
    results = []
    logger.info("Waiting for threading to complete...")
    try:
        for future in concurrent.futures.as_completed( futures):
            err = future.exception()
            if err is None:
                result = future.result()
                logger.debug("Result: ".format(result))
                if result is None:
                    logger.debug("Problem with result...")
                results.append(result)
            else:
                logger.debug("Exception: ".format(err))
                results.append(err)
    except KeyboardInterrupt:
        logger.info.report(" canceling...")
        canceled = True
        for future in futures:
            future.cancel()
    return canceled, results

def thread_this(fn, vars, max_threads=multiprocessing.cpu_count()):
    """

    :param fn:
    :param vars:
    :param max_threads:
    :param timeout:
    :return:
    """
    logger.info(" starting multithreading: pool of {}".format(max_threads))
    futures = set()
    with concurrent.futures.ThreadPoolExecutor( max_workers = max_threads) as executor:
        for var in vars:
            future = executor.submit( fn, var )
            futures.add( future)
        canceled, results = wait_for( futures)
        if canceled:
            logger.info("Cancelled...")
            executor.shutdown()
    logger.info(" ran {} devices using {} threads{}". format( len( futures), max_threads, " [canceled]" if canceled else ""))
    return results

