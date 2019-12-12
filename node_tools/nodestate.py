# coding: utf-8

"""Get data from a given node."""
import asyncio
import aiohttp
import logging

from diskcache import Index
from ztcli_api import ZeroTier
from ztcli_api import exceptions
from node_tools.helper_funcs import get_token, get_cachedir, AttrDict

logger = logging.getLogger(__name__)


async def main():
    """Example code to retrieve data from a ZeroTier node using tasks."""
    async with aiohttp.ClientSession() as session:
        ZT_API = get_token()
        client = ZeroTier(ZT_API, loop, session)

        try:
            # get status details of the local node
            await client.get_data('status')
            status_data = AttrDict.from_nested_dict(client.data)
            node_id = client.data.get('address')
            logger.info('Found node: {}'.format(node_id))
            cache.update([(node_id, status_data)])

            # get status details of the node peers
            await client.get_data('peer')
            peer_data = client.data
            for peer in peer_data:
                peer_status = AttrDict.from_nested_dict(peer)
                peer_id = peer.get('address')
                logger.info('Peer: {}'.format(peer_id))
                cache.update([(peer_id, peer_status)])

            # get/display all available network data
            await client.get_data('network')
            network_data = client.data
            for network in network_data:
                net_status = AttrDict.from_nested_dict(network)
                net_id = network.get('address')
                logger.info('Network: {}'.format(net_id))
                cache.update([(net_id, net_status)])

        except exceptions.ZeroTierConnectionError:
            pass

cache = Index(get_cachedir())
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
