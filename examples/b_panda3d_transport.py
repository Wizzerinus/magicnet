import dataclasses

import panda3d.core as p3dcore
from direct.distributed.PyDatagram import PyDatagram
from direct.task import TaskManagerGlobal

from magicnet.core.connection import ConnectionHandle
from magicnet.core.transport_handler import TransportHandler
from magicnet.util.messenger import StandardEvents


@dataclasses.dataclass
class Panda3DTransport(TransportHandler):
    connmap: dict[p3dcore.Connection, ConnectionHandle] = dataclasses.field(
        default_factory=dict
    )

    conn_mgr = None
    conn_listener = None
    conn_reader = None
    conn_writer = None
    tcp_rendezvous = None

    def __post_init__(self):
        super().__post_init__()
        self.conn_mgr = p3dcore.QueuedConnectionManager()
        self.conn_reader = p3dcore.QueuedConnectionReader(self.conn_mgr, 0)
        self.conn_writer = p3dcore.ConnectionWriter(self.conn_mgr, 0)
        # We need to put reader and writer in raw mode
        # so they don't try to operate on little endian datagrams
        self.conn_reader.setRawMode(True)
        self.conn_writer.setRawMode(True)

    def send(self, connection: ConnectionHandle, dg: bytes) -> None:
        pydg = PyDatagram()
        # Unfortunately add_blob is also little endian
        pydg.addFixedString(len(dg).to_bytes(2, "big"), 2)
        pydg.addFixedString(dg, len(dg))
        self.conn_writer.send(pydg, connection.connection_data)  # type: ignore

    def connect(self, host: str, port: int) -> None:
        conn = self.conn_mgr.openTCPClientConnection(host, port, 2000)
        if conn:
            self.add_connection(conn)
            TaskManagerGlobal.taskMgr.add(self.poll_reader, "p3d-poll-read", -40)
        else:
            raise RuntimeError(f"Unable to connect to the server at {host}:{port}")

    def open_server(self, host: str, port: int) -> None:
        self.conn_listener = p3dcore.QueuedConnectionListener(self.conn_mgr, 0)
        self.tcp_rendezvous = self.conn_mgr.openTCPServerRendezvous(host, port, 1000)
        self.conn_listener.addConnection(self.tcp_rendezvous)
        TaskManagerGlobal.taskMgr.add(self.poll_rendezvous, "p3d-poll-tcp", -39)
        TaskManagerGlobal.taskMgr.add(self.poll_reader, "p3d-poll-read", -40)

    def add_connection(self, conn: p3dcore.Connection) -> ConnectionHandle:
        self.conn_reader.addConnection(conn)
        handle = ConnectionHandle(self, conn)
        self.connmap[conn] = handle
        return handle

    def poll_rendezvous(self, task):
        if self.conn_listener.newConnectionAvailable():
            rendezvous = p3dcore.PointerToConnection()
            net_addr = p3dcore.NetAddress()
            conn_p = p3dcore.PointerToConnection()
            if self.conn_listener.getNewConnection(rendezvous, net_addr, conn_p):
                conn = conn_p.p()
                handle = self.add_connection(conn)
                self.send_motd(handle)
        return task.cont

    def poll_reader(self, task):
        if self.conn_reader.dataAvailable():
            dg = p3dcore.NetDatagram()
            if self.conn_reader.getData(dg):
                # no idea how this works but it doesn't care about the length
                bytestr = dg.getMessage()
                conn = dg.getConnection()
                handle = self.connmap.get(conn)
                if not handle:
                    hex_text = bytestr.hex()
                    self.emit(StandardEvents.WARNING, f"Stray datagram: {hex_text}")
                else:
                    self.datagram_received(handle, bytestr[2:])
        return task.cont

    def before_disconnect(self, handle: ConnectionHandle) -> None:
        self.conn_mgr.closeConnection(handle.connection_data)
