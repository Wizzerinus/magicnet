***MagicNet** — A fun and flexible networking library for Python applications.*

---

Source code: <https://github.com/wizzerinus/magicnet>

---

## Introduction

MagicNet is a modern library for building real-time web applications.

Its key features are:

* **Client simplicity**: write simple and intuitive Python code, typehint your code if you want,
  write zero boilerplate, and get efficient network interaction in any scenario.
* **Client flexibility**:
  * MagicNet makes no assumptions about the networking stack of your application.
    Many libraries require a specific networking stack (i.e. AsyncIO), which may not at all
    work with a different event loop.
  * MagicNet's low level functionality is completely decoupled from the high-level functionality.
    Most of the time, changing the networking stack is as simple as changing one variable
    indicating the way to send pure bytestrings. The application code itself
    does not need to care about the networking stack or event loop used.
* **Server flexibility**: MagicNet can be used with a simple client-server structure,
  as well as a more complicated structure with multiple servers, proxies, etc.
  Proxies themselves can be also implemented in the same library using the
  transport middleware system.
* **Fast prototyping:** MagicNet can be used with a Native connection protocol,
  which merges all parts of the application into one process without changing
  the internal functionality. Any client code that works on this protocol
  is almost guaranteed to work on any different protocol.
* **Simple protocol**: If any server is slower than desired, that server can be rewritten
  in a different language (such as Go or Rust) without touching the rest of infrastructure,
  or the application-specific code used.

---

## Requirements

Requires Python 3.10+. 

The default installation of MagicNetworking has no dependencies and can be used out of the box,
however, it is recommended to install `magicnet[standard]` which includes the following:

* Msgpack, for more efficient message packager.
* Pydantic, for type validation middleware
  (by default, unsocilited clients can cause errors by sending valid but semantically malformed messages).

---

## Example

MagicNet packages two main APIs — the Message-level API (procedural)
and the Object-level API (object-oriented). Both APIs work on the same
underlying networking stack and are useful in different scenarios:
globally used methods are likely better to put into the Message API,
while methods specific to an object are likely better as an object API.

### Message API

```python
from magicnet.core.net_message import NetMessage
from magicnet.protocol import network_types
from magicnet.protocol.processor_base import MessageProcessor

# 0-63 are reserved for builtin message IDs
# Custom message IDs can start with 64
MSG_CUSTOM = 64
MSG_RESPONSE = 65

class MsgCustom(MessageProcessor):
    arg_type = tuple[network_types.s256]

    def invoke(self, message: NetMessage):
        # this will be called on the server, as the client sends this message
        client_name = message.sent_from.context.get("username")
        if not client_name:
            message.disconnect_sender(10, "MsgCustom requires a username!")
            return

        print(f"Client {client_name} sent:", message.parameters[0])
        to_send = NetMessage(
            MSG_RESPONSE,
            ["".join(reversed(message.parameters[0]))],
            # uncomment if you want only the sender to receive the message
            # destination=message.sent_from,
        )
        self.manager.send_message(to_send)

class MsgCustomResponse(MessageProcessor):
    arg_type = tuple[network_types.s256]

    def invoke(self, message: NetMessage):
        # this will be called on the client, as the server sends this message
        print("Reversed message:", message.parameters[0])

custom_messages = {MSG_CUSTOM: MsgCustom, MSG_RESPONSE: MsgCustomResponse}

# define the server parameters in one script...
# define the client parameters in another or the same script...
client = ...
msg = NetMessage(MSG_CUSTOM, ["some string"])
client.send(msg)
```

### Object API

(currently not implemented)

Full-fledged examples can be found in `examples` directory.

---

## Networking stacks

The defining power of MagicNet is being able to work with different networking stacks.
Out of the box are included an AsyncIO-TCP-based stack, and a native single-process stack.
An example of a custom networking stack is included in the example `b_client_panda3d`:
only the networking adapter (a very small fraction of the application code in real applications)
had to be changed to migrate to a completely different asynchronous stack
with no AsyncIO knowledge whatsoever.

The same way, applications can be migrated from one launching type into another
without making any changes to the application code. For example, if a game has
proper client-server separation (which is made easier by the internal structure of the library),
the server can be normally run in the same process using the native transport handler.
The game then can add a "local server" feature opening a socket-based connection
with other players, while keeping the native handler for the first player intact.
If the server has to be extracted into a separate application, the only thing that
has to be changed is the transport handler between the first player and the server,
with the entire game client and server code remaining intact!
