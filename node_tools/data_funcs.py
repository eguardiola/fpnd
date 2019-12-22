# coding: utf-8

"""Data update helper functions."""
from __future__ import print_function

import logging
import datetime
import functools

from diskcache import Index
from node_tools.helper_funcs import update_state, get_cachedir
from node_tools.helper_funcs import ENODATA, NODE_SETTINGS

try:
    from datetime import timezone
    utc = timezone.utc
except ImportError:
    from daemon.timezone import UTC
    utc = UTC()


logger = logging.getLogger(__name__)
cache = Index(get_cachedir())
max_age = NODE_SETTINGS['max_cache_age']


def do_logstats(msg=None):
    """Log cache size/key stats with optional ``msg`` string"""
    size = len(cache)
    if msg:
        logger.debug(msg)
    logger.debug('{} items currently in cache.'.format(size))
    logger.debug('Cache items: {}'.format(list(cache)))


def with_cache_aging(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """reset timestamp and clear if needed"""
        utc_stamp = datetime.datetime.now(utc)
        do_logstats('Entering cache wrapper')
        if 'utc-time' in cache:
            stamp = cache['utc-time']
            cache_age = utc_stamp - stamp  # this is a timedelta
            logger.debug('Cache age is: {} sec'.format(cache_age.seconds))
            logger.debug('Maximum cache age: {} sec'.format(max_age))
            if cache_age.seconds > max_age:
                logger.debug('Cache data is too old!!')
                logger.debug('Stale data will be removed!!')
                cache.clear()

        result = func(*args, **kwargs)

        if result is ENODATA or result is None:
            cache.update([('utc-time', stamp)])
            logger.debug('Old cache time is: {}'.format(stamp.isoformat(' ', 'seconds')))
        else:
            cache.update([('utc-time', utc_stamp)])
            logger.debug('New cache time is: {}'.format(utc_stamp.isoformat(' ', 'seconds')))
        return result
    return wrapper


@with_cache_aging
def update_runner():
    do_logstats('Entering update runner')

    try:
        res = update_state()
        size = len(cache)
    except:  # noqa: E722
        logger.debug('No data available, cache was NOT updated')
    else:
        if size < 1:
            logger.debug('No data available (live or cached)')
        elif size > 0:
            logger.debug('Get data result: {}'.format(res))
            do_logstats()
        else:
            logger.debug('Cache empty and API returned ENODATA')
    return res
