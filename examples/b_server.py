import functools

import b_common
from magicnet.batteries.asyncio_network_manager import AsyncIONetworkManager
from magicnet.batteries.logging_node import LoggerNode
from magicnet.batteries.transport_managers import EverywhereTransportManager
from magicnet.core.net_globals import MNEvents


server = AsyncIONetworkManager.create_root(
    transport_type=EverywhereTransportManager,
    transport_params=("server", b_common.transport),
    motd="An example native host",
    extras=b_common.extra_message_types,
)
sr_logger = server.create_child(LoggerNode, prefix="asynciosocket.server")
sr_logger.listen(MNEvents.HANDLE_ACTIVATED, functools.partial(print, "server handle:"))
sr_logger.listen(MNEvents.HANDLE_DESTROYED, functools.partial(print, "handle died:"))
server.open_server(client=("127.0.0.1", 5000))
