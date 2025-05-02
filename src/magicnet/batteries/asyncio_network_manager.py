__all__ = ["AsyncIONetworkManager"]

import asyncio
import dataclasses
import signal
from collections.abc import Coroutine, Iterable
from typing import Any

from magicnet.core.connection import ConnectionHandle
from magicnet.core.net_globals import MNEvents
from magicnet.core.network_manager import NetworkManager
from magicnet.util.messenger import StandardEvents


@dataclasses.dataclass(kw_only=True)
class AsyncIONetworkManager(NetworkManager):
    """
    AsyncIONetworkManager simplifies the management of event loops and tasks
    in an application using AsyncIO. It is not exactly pythonic,
    but it's not really doable to make a pythonic one
    with how MagicNet is constructed (being asynchronousness-agnostic).
    """

    spawned_tasks: set[asyncio.Task[Any]] = dataclasses.field(default_factory=set, repr=False)
    add_signal_handlers: bool = dataclasses.field(default=True)
    loop: asyncio.AbstractEventLoop = dataclasses.field(repr=False, default_factory=asyncio.new_event_loop)

    def __post_init__(self):
        super().__post_init__()
        if self.add_signal_handlers:
            signals = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
            for s in signals:
                self.loop.add_signal_handler(s, self.shutdown)

    def shutdown(self):
        self.emit(StandardEvents.INFO, "Gracefully terminating.")
        self.spawn_task(self.async_shutdown())

    async def async_shutdown(self):
        super().shutdown()
        self.emit(StandardEvents.INFO, "Finishing tasks...")
        all_tasks = asyncio.all_tasks() - {asyncio.current_task()}
        for task in all_tasks:
            task.cancel()
        await asyncio.gather(*all_tasks, return_exceptions=True)
        self.emit(StandardEvents.INFO, "Stopping the event loop...")
        self.loop.stop()
        self.emit(StandardEvents.INFO, "Termination done.")

    def despawn_task(self, task: asyncio.Task[Any]):
        self.spawned_tasks.discard(task)
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return

        if exc:
            self.emit(StandardEvents.EXCEPTION, "Error in asynchronous code", exc)

    def spawn_task(self, coro: Coroutine[Any, Any, Any]):
        """
        Schedules an asynchronous task, prevents its garbage collection,
        and emits any exceptions created by the task.
        This is a wrapper around ``asyncio.create_task``, which by default
        suppresses any exceptions, and lets the task to be garbage collected,
        which we cannot do anything about due to running from a synchronous context.
        """
        task = self.loop.create_task(coro)
        self.spawned_tasks.add(task)
        task.add_done_callback(self.despawn_task)

    def open_server(self, **kwargs: Iterable[Any]):
        """
        Starts one or more servers.
        Note that kwargs should map the foreign role to the parameters
        provided to that role. So if you run this on a node with
        the role = 'server', and the other node in your network
        is called 'client', you should map 'client' to the parameters.

        Note: this method is blocking, no code will be executed after this
        until the server is stopped.
        """
        super_open_server = super().open_server
        self.loop.call_soon(lambda: super_open_server(**kwargs))
        self.loop.run_forever()

    def open_connection(self, **kwargs: Iterable[Any]):
        """
        Connects to one or more servers.
        Note that kwargs should map the foreign role to the parameters
        provided to that role. So if you run this on a node with
        the role = 'client', and the other node in your network
        is called 'server', you should map 'server' to the parameters.

        Note: this method is blocking, no code will be executed after this
        until the client is disconnected.
        """
        super_open_connection = super().open_connection
        self.loop.call_soon(lambda: super_open_connection(**kwargs))
        self.loop.run_forever()

    def wait_for_connection(self) -> asyncio.Future[ConnectionHandle]:
        """
        Waits for the next ConnectionHandle, then returns it.
        This method is supposed to be used in an ``await`` statement.
        """

        future = asyncio.Future[ConnectionHandle]()
        self.listen(MNEvents.HANDLE_ACTIVATED, future.set_result)
        return future
