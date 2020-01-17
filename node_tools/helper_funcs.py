# coding: utf-8

"""Miscellaneous helper functions."""
from __future__ import print_function

import sys
import logging

from configparser import ConfigParser as SafeConfigParser


logger = logging.getLogger(__name__)


class Constant(tuple):
    "Pretty display of immutable constant."
    def __new__(cls, name):
        return tuple.__new__(cls, (name,))

    def __repr__(self):
        return '%s' % self[0]


ENODATA = Constant('ENODATA')  # error return for async state data updates

NODE_SETTINGS = {
    u'max_cache_age': 60,  # maximum cache age in seconds
    u'use_localhost': True,  # messaging interface to use
    u'node_role': None,  # role this node will run as
    u'moon_list': ['4f4114472a'],  # list of fpn moons to orbiit
    u'home_dir': None,
    u'debug': False
}


def check_and_set_role(role, path=None):
    """
    Check for role-specific paths to set tentative initial fpn role,
    one of <None|moon|controller>.  Once the cache is populated the
    initial role is verified and updated if needed.
    :param role: the non-default role to query for <moon|ctlr>
    :return <True|False>: True if role query is a match
    """
    import os
    import fnmatch

    new_role = False
    if not path:
        path = get_filepath()

    if role == 'moon':
        role_path = os.path.join(path, 'moons.d')
        # print(role_path)
    elif role == 'controller':
        role_path = os.path.join(path, 'controller.d')
    else:
        return new_role

    if os.path.exists(role_path):
        for file in os.listdir(role_path):
            role_file = fnmatch.fnmatch(file, '*.' + role)
            # print(role_file)
            if role_file:
                NODE_SETTINGS['node_role'] = None
                new_role = False

    return new_role


def config_from_ini(file_path=None):
    config = SafeConfigParser()
    candidates = ['/etc/fpnd.ini',
                  '/etc/fpnd/fpnd.ini',
                  '/usr/lib/fpnd/fpnd.ini',
                  'test/test_data/settings.ini',
                  ]
    if file_path:
        candidates.append(file_path)
    found = config.read(candidates)

    if not found:
        message = 'No usable cfg found, files in /tmp/ dir.'
        return False, message

    for tgt_ini in found:
        if 'fpnd' in tgt_ini:
            message = 'Found system settings...'
            return config, message
        if 'settings' in tgt_ini and config.has_option('Options', 'prefix'):
            message = 'Found local settings...'
            config['Paths']['log_path'] = ''
            config['Paths']['pid_path'] = ''
            config['Options']['prefix'] = 'local_'
            return config, message


def do_setup():
    import os

    my_conf, msg = config_from_ini()
    if my_conf:
        debug = my_conf.getboolean('Options', 'debug')
        home = my_conf['Paths']['home_dir']
        NODE_SETTINGS['debug'] = debug
        NODE_SETTINGS['home_dir'] = home
        if 'system' not in msg:
            prefix = my_conf['Options']['prefix']
        else:
            prefix = ''
        pid_path = my_conf['Paths']['pid_path']
        log_path = my_conf['Paths']['log_path']
        pid_file = my_conf['Options']['pid_name']
        log_file = my_conf['Options']['log_name']
        pid = os.path.join(pid_path, prefix, pid_file)
        log = os.path.join(log_path, prefix, log_file)

    else:
        home = None
        debug = False
        pid = '/tmp/fpnd.pid'
        log = '/tmp/fpnd.log'
    return home, pid, log, debug, msg


def exec_full(filepath):
    global_namespace = {
        "__file__": filepath,
        "__name__": "__main__",
    }
    with open(filepath, 'rb') as file:
        exec(compile(file.read(), filepath, 'exec'), global_namespace)


def find_ipv4_iface(addr_string, strip=True):
    """
    This is intended only for picking the IPv4 address from the list
    of 'assignedAddresses' in the JSON network data payload for a
    single ZT network.
    :param addr_string: IPv4 address in CIDR format
                            eg: 192.168.1.10/24
    :param strip:
    :return stripped addr_str: if 'strip' return IPv4 addr only, or
    :return True: if not 'strip' or False if addr not valid
    """
    import ipaddress
    try:
        interface = ipaddress.IPv4Interface(addr_string)
        if not strip:
            return True
        else:
            return str(interface.ip)
    except ValueError:
        return False


def get_cachedir(dir_name='fpn_cache'):
    """
    Get temp cachedir according to OS (create it if needed)
    * override the dir_name arg for non-cache data
    """
    import os
    import tempfile
    temp_dir = tempfile.gettempdir()
    cache_dir = os.path.join(temp_dir, dir_name)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir


def get_filepath():
    import platform
    """Get filepath according to OS"""
    if platform.system() == "Linux":
        return "/var/lib/zerotier-one"
    elif platform.system() == "Darwin":
        return "/Library/Application Support/ZeroTier/One"
    elif platform.system() == "FreeBSD" or platform.system() == "OpenBSD":
        return "/var/db/zerotier-one"
    elif platform.system() == "Windows":
        return "C:\\ProgramData\\ZeroTier\\One"


def get_token():
    """Get authentication token (requires root or user acl)"""
    with open(get_filepath()+"/authtoken.secret") as file:
        auth_token = file.read()
    return auth_token


def json_dump_file(endpoint, data, dirname=None):
    import os
    import json

    def opener(dirname, flags):
        return os.open(dirname, flags, mode=0o600, dir_fd=dir_fd)

    if dirname:
        dir_fd = os.open(dirname, os.O_RDONLY)
    else:
        opener = None

    with open(endpoint + '.json', 'w', opener=opener) as fp:
        json.dump(data, fp)
    logger.debug('{} data in {}.json'.format(endpoint, endpoint))


def json_load_file(endpoint, dirname=None):
    import os
    import json

    def opener(dirname, flags):
        return os.open(dirname, flags, dir_fd=dir_fd)

    if dirname:
        dir_fd = os.open(dirname, os.O_RDONLY)
    else:
        opener = None

    with open(endpoint + '.json', 'r', opener=opener) as fp:
        data = json.load(fp)
    logger.debug('{} data read from {}.json'.format(endpoint, endpoint))
    return data


def log_fpn_state(diff=None):
    if diff is None:
        from node_tools import state_data as st
        diff = st.changes

    if diff:
        for iface, state in diff:
            if iface in ['fpn0', 'fpn1']:
                if state:
                    logger.info('{} is UP'.format(iface))
                else:
                    logger.info('{} is DOWN'.format(iface))


def net_change_handler(iface, state):
    """
    Net change event handler for configuring fpn network devices
    (calls net cmds for a given interface/state).  Schedules a new
    run_net_cmd() job for each change event.
    :param iface: <'fpn0'|'fpn1'> fpn interface to act on
    :param state: <True|False> new iface state, ie, up|down
    """
    import schedule
    from node_tools.network_funcs import get_net_cmds
    from node_tools.network_funcs import run_net_cmd

    fpn_home = NODE_SETTINGS['home_dir']

    cmd = get_net_cmds(fpn_home, iface, state)
    if cmd:
        logger.debug('get_net_cmds returned: {}'.format(cmd))
        schedule.every(1).seconds.do(run_net_cmd, cmd).tag('net-change')
    else:
        logger.error('get_net_cmds returned None')
        # raise Exception('Missing command return from get_net_cmds()!')


def run_event_handlers(diff=None):
    """
    Run state change event handlers (currently just the net handler)
    :param diff: State change diff, ie, st.changes
    """
    if diff is None:
        from node_tools import state_data as st
        diff = st.changes

    if diff:
        for iface, state in diff:
            if iface in ['fpn0', 'fpn1']:
                logger.debug('running net_change_handler for iface {} and state {}'.format(iface, state))
                net_change_handler(iface, state)


def send_announce_msg(fpn_id, addr):
    """
    Send node announcement message (hey, this is my id).
    """
    import schedule
    from node_tools.network_funcs import echo_client

    if fpn_id:
        logger.debug('Sending msg: {} to addr {}'.format(fpn_id, addr))
        schedule.every(1).seconds.do(echo_client, fpn_id, addr).tag('hey-moon')


def startup_handlers():
    """
    Event handlers that need to run at, well, startup (currently only
    the moon announcement message).
    """
    from node_tools import state_data as st
    nodeState = AttrDict.from_nested_dict(st.fpnState)

    if nodeState.moon_id0 in NODE_SETTINGS['moon_list']:
        addr = nodeState.moon_addr
    if NODE_SETTINGS['use_localhost'] or not addr:
        addr = '127.0.0.1'

    send_announce_msg(nodeState.fpn_id, addr)


def update_state():
    import pathlib
    here = pathlib.Path(__file__).parent
    node_scr = here.joinpath("nodestate.py")
    try:
        exec_full(node_scr)
        return 'OK'
    except Exception as exc:
        logger.warning('update_state exception: {}'.format(exc))
        return ENODATA


def validate_role():
    """
    Validate and set initial role with state data from the cache.
    """
    from node_tools import state_data as st
    nodeState = AttrDict.from_nested_dict(st.fpnState)

    if nodeState.fpn_id in NODE_SETTINGS['moon_list']:
        NODE_SETTINGS['node_role'] = 'moon'
    else:
        NODE_SETTINGS['node_role'] = None
    logger.debug('ROLE: validated role is {}'.format(NODE_SETTINGS['node_role']))


def xform_state_diff(diff):
    """
    Function to extract and transform state diff type to a new
    dictionary (this means the input must be non-empty). Note the
    object returned is mutable!
    :caveats: if returned k,v are tuples of (old, new) state values
              the returned keys are prefixed with `old_` and `new_`
    :param state_data.changes obj: list of tuples with state changes
    :return AttrDict: dict with state changes (with attribute access)
    """

    d = {}
    if not diff:
        return d

    for item in diff:
        if isinstance(item, tuple) or isinstance(item, list):
            if isinstance(item[0], str):
                d[item[0]] = item[1]
            elif isinstance(item[0], tuple):
                # we know we have duplicate keys so make new ones
                # using 'old_' and 'new_' prefix
                old_key = 'old_' + item[0][0]
                d[old_key] = item[0][1]
                new_key = 'new_' + item[1][0]
                d[new_key] = item[1][1]

    return AttrDict.from_nested_dict(d)


class AttrDict(dict):
    """ Dictionary subclass whose entries can be accessed by attributes
        (as well as normally).
    """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @staticmethod
    def from_nested_dict(data):
        """ Construct nested AttrDicts from nested dictionaries. """
        if not isinstance(data, dict):
            return data
        else:
            return AttrDict({key: AttrDict.from_nested_dict(data[key])
                             for key in data})
