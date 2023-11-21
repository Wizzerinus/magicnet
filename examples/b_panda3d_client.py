import functools
import logging

from direct.gui.DirectEntry import DirectEntry
from direct.gui.DirectLabel import DirectLabel
from direct.showbase.ShowBase import ShowBase

import b_common
from b_panda3d_transport import Panda3DTransport
from magicnet.batteries.logging_node import LoggerNode
from magicnet.batteries.transport_managers import EverywhereTransportManager
from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.core.network_manager import NetworkManager
from magicnet.core.transport_manager import TransportParameters


# for debugging
# loadPrcFileData("", "notify-level-net spam")


transport = {
    "client": {
        "server": TransportParameters(
            b_common.encoder,
            Panda3DTransport,
            b_common.EverywhereExceptBack,
            b_common.middlewares,
        )
    }
}

client = NetworkManager.create_root(
    transport_type=EverywhereTransportManager,
    transport_params=("client", b_common.ports, transport),
    extras=b_common.extra_message_types,
    shutdown_on_disconnect=True,
)
cl_logger = client.create_child(LoggerNode, prefix="panda3dsocket.client")
cl_logger.listen(MNEvents.MOTD_SET, functools.partial(cl_logger.log, logging.INFO))
cl_logger.listen(MNEvents.DISCONNECT, functools.partial(cl_logger.log, logging.WARNING))


def do_send(x):
    if not base.sent_name:
        msg = NetMessage(b_common.MSG_SET_NAME, [x])
        client.send_message(msg)
        base.sent_name = True
        textbox["text"] = f"Name: {x}"
    else:
        msg = NetMessage(b_common.MSG_CUSTOM, [x])
        client.send_message(msg)
    entry.set("")


base = ShowBase()
base.sent_name = False
entry = DirectEntry(pos=(-0.5, 0, -0.075), scale=0.1, command=do_send)
textbox = DirectLabel(
    pos=(0, 0, 0.075), scale=0.1, text="Enter your name:", relief=None
)
client.open_connection("127.0.0.1", 5000)
base.run()
