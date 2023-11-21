import functools
import logging

from magicnet.batteries.logging_node import LoggerNode
from magicnet.batteries.encoders import MsgpackEncoder
from magicnet.batteries.middlewares.message_validation import MessageValidatorMiddleware
from magicnet.batteries.transports.single_app import SingleAppTransport
from magicnet.batteries.transport_managers import EverywhereTransportManager
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.core.network_manager import NetworkManager
from magicnet.core.transport_manager import TransportParameters
from magicnet.protocol.protocol_globals import StandardMessageTypes

middlewares = [MessageValidatorMiddleware]
encoder = MsgpackEncoder()
transport = {
    "client": {
        "server": TransportParameters(encoder, SingleAppTransport, None, middlewares)
    }
}


server = NetworkManager.create_root(
    transport_type=EverywhereTransportManager,
    transport_params=("server", transport),
    motd="An example native host",
)
sr_logger = server.create_child(LoggerNode, prefix="native.server")
sr_logger.listen(MNEvents.HANDLE_ACTIVATED, functools.partial(print, "server handle:"))

client = NetworkManager.create_root(
    transport_type=EverywhereTransportManager,
    transport_params=("client", transport),
)
cl_logger = client.create_child(LoggerNode, prefix="native.client")
cl_logger.listen(MNEvents.MOTD_SET, functools.partial(cl_logger.log, logging.INFO))
cl_logger.listen(MNEvents.DISCONNECT, functools.partial(cl_logger.log, logging.WARNING))
cl_logger.listen(MNEvents.HANDLE_ACTIVATED, functools.partial(print, "client handle:"))

server.open_server(client=())
client.open_connection(server=[server])
message = NetMessage(StandardMessageTypes.HELLO, [2, b"123"])
client.send_message(message)
