import dataclasses
from typing import Iterable
from unittest.mock import MagicMock

from magicnet.core.net_globals import MNEvents
from magicnet.core.net_message import NetMessage
from magicnet.core.network_manager import NetworkManager
from magicnet.protocol.protocol_globals import StandardMessageTypes
from magicnet.util.messenger import StandardEvents
from net_tester_generic import TwoNodeNetworkTester


@dataclasses.dataclass
class HackedNetworkManager(NetworkManager):
    def send_message(self, message: NetMessage):
        if (
            message.message_type == StandardMessageTypes.HELLO
            and message.parameters[0] == 3
        ):
            # don't do a proper handshake
            return
        self.transport.send(message)

    def process_datagram(self, messages: Iterable[NetMessage]):
        self.emit("messages", messages)
        super().process_datagram(messages)


@dataclasses.dataclass
class HackedNetworkTester(TwoNodeNetworkTester):
    middlewares = []
    client_cls = HackedNetworkManager
    do_raise_err = False


def test_unauthenticated_messages():
    tester = HackedNetworkTester.create_and_start()
    msg = NetMessage(StandardMessageTypes.REQUEST_VISIBLE_OBJECTS)

    mock = MagicMock()
    tester.client.listen(MNEvents.DISCONNECT, mock)
    tester.client.send_message(msg)
    tester.client.transport.empty_queue()
    assert "different message" in mock.call_args.args[0]


def test_bad_hello():
    tester = HackedNetworkTester.create_and_start()
    msg = NetMessage(StandardMessageTypes.HELLO, (-1, b"123"))

    mock = MagicMock()
    tester.client.listen(MNEvents.DISCONNECT, mock)
    tester.client.send_message(msg)
    tester.client.transport.empty_queue()
    assert "server version" in mock.call_args.args[0]


def test_no_motd():
    tester = HackedNetworkTester.create_and_start()
    msg = NetMessage(StandardMessageTypes.MOTD, ("I am malicious",))

    mock = MagicMock()
    tester.server.listen(StandardEvents.WARNING, mock)
    cl_mock = MagicMock()
    tester.client.listen("messages", cl_mock)
    tester.client.send_message(msg)
    tester.client.transport.empty_queue()
    assert "Unexpected MOTD message" in mock.call_args.args[0]
    assert not cl_mock.call_args
