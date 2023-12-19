***MagicNet** — A fun and flexible networking library for Python applications.*

---

Source code: <https://github.com/wizzerinus/magicnet>

---

## Requirements

Requires Python 3.10+. 

The default installation of MagicNetworking has no dependencies and can be used out of the box,
however, it is recommended to install `magicnet[standard]` which includes the following:

* Msgpack, for more efficient message packager.

---

## Example

MagicNet packages two main APIs — the Message-level API (procedural)
and the Object-level API (object-oriented). Both APIs work on the same
underlying networking stack and are useful in different scenarios:
globally used methods are likely better to put into the Message API,
while methods specific to an object are likely better as an object API.

### Running provided examples

Full-fledged examples can be found in `examples` directory.

* Native connection: run `a_native_connection.py`.
  * Note that this example will immediately exit after sending a few messages.
* Client-server basics: run `b_server.py`, then `b_client.py` or `b_panda3d_client.py`
  * The Panda3D client requires a reasonably recent version of Panda3D.
  * The Panda3D client is very barebones and mostly included as a test of working with different event loops.
* Network objects: run `c_network_objects/c_marshal_things.py`, then `c_network_objects/c_server.py`,
  then `c_network_objects/c_client.py`.

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
    # If typehints are used and the MessageValidation middleware
    # is used, messages that do not match the typehints are rejected

    def invoke(self, message: NetMessage):
        # this will be called on the server, as the client sends this message
        client_name = message.sent_from.context.get("username")
        if not client_name:
            message.disconnect_sender(10, "MsgCustom requires a username!")
            return

        print(f"Client {client_name} sent:", message.parameters[0])
        to_send = NetMessage(
            MSG_RESPONSE,
            ("".join(reversed(message.parameters[0])), ),
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

```python
import dataclasses

from magicnet.netobjects.network_object import NetworkObject
from magicnet.netobjects.network_field import NetworkField
from magicnet.protocol import network_types

# On the server
@dataclasses.dataclass
class NetworkNumberServer(NetworkObject):
    # All roles can also use the same class if needed, see netobject tests
    network_name = "one-number"
    object_role = 1
    value: int = dataclasses.field(init=False, default=0)

    def net_create(self):
        pass

    def net_delete(self):
        pass

    @NetworkField
    def set_init_value(self, value: network_types.int32):
        # If typehints are used, all messages that do not pass the typehints are rejected
        # Note: only a subset of typehints is supported due to the difficulty
        # of encoding a typehint as a string (which is required to i.e.
        # exclude server classes from being imported in the client)
        self.value = value
        self.send_message("set_current_value", [self.value])

    @NetworkField
    def add_value(self, value: network_types.int32):
        self.value += value
        # Not validating integer overflow in this example, for simplicity
        # (the server won't crash, just the number won't be sent back)
        self.send_message("set_current_value", [self.value])

# On the client
@dataclasses.dataclass
class NetworkNumberClient(NetworkObject):
    network_name = "one-number"
    object_role = 0
    value: int = dataclasses.field(init=False, default=0)

    def net_create(self):
        # This runs when the object was created
        self.send_message("add_value", [15])

    def net_delete(self):
        pass

    @NetworkField
    def set_current_value(self, value: network_types.int32):
        print(f"Object's value changed: {self.value} -> {value}")
        self.value = value

# Creating the object
# The API is the same on the server and the client side, although
# the semantics of the network datagrams used differ
client = ...
obj = NetworkNumberClient(controller=client)
obj.send_message("set_init_value", [10])
obj.request_generate()
```

---

## Component information

This is the list of all components I would want to implement, but not all of them are done yet.
The components that can be implemented easily but are not in the standard library
due to being opinionated are marked as domain-specific.

### Object API

* **Generation and removal of objects** - implemented
* **Network fields** - implemented
* **Field type validation** - implemented
* **Passing structs as arguments** - implemented
* **RAM persistence of fields** - implemented
* **Database persistence** - not implemented
  * Most likely, I will implement three backends (SQL, MongoDB, dbm for local development).
* **Object API routing** - implemented
  * Zone-based message routing is currently implemented (each client "sees" a set of zones,
    and each object is in exactly one zone). The set of visible zones can be configured
    through shared parameters (i.e., on handle-to-handle basis).

### Message and Connection Layer

* **Handshake** - fully functional
* **Shared parameters** - fully functional
  * Includes a way to save data on a connection that is shared between both sides.
    Note that there is not a built in security protocol for this. 
* **Middleware servers** - not implemented
  * This includes, for example, a server that merely routes datagrams,
    instead of processing it immediately. This would require somehow packing the
    connection into the datagram and making virtual connections on both sides.
    For the usecases of this, see below "High-load scenarios".
* **Connection transfer** - not implemented
  * This is useful for High-load scenarios as well as reconnection.
* **Reconnection** - not implemented
  * As reconnection cannot be implemented on some stacks like TCP,
    it really is just "making a new connection to the same server without losing state".
    This is application logic-dependent and may be easier than I think it is.
* **Custom messages** - fully implemented

### Network Layer

This part is really annoying due to a completely unavoidable combinatoric explosion
of connection types and event loops being in use (two in the standard library and many
other event loops made by other libraries).

* **In-memory transfer (server and client in the same process)** - functional
  * This may sound stupid but it's actually really nice for local prototyping!
* **AsyncIO/TCP combination** - functional
* **AsyncIO/UDP combination** - not done
* **AsyncIO/Websockets combination** - not done
* **Threads/TCP combination** - not done
* **Threads/UDP combination** - not done
* **Threads/Websockets combination** - not done

* **Bonus: Panda3D/TCP combination** - functional but not included in the main distribution
  * Currently this may be downloaded from the `examples` folder and used mostly as-is.

### Security Layer

* **Message API typechecking** - functional
  * Requires the use of `MessageValidatorMiddleware`
    (recommended to have in all setups in a bridge or server node
     to prevent malicious clients from crashing a server)
* **Object API typechecking** - fully functional
  * Available out of the box
* **Message API permissions** - domain-specific
  * Requires the use of a custom TransportMiddleware
* **Object API permissions** - domain-specific
  * Requires the use of a custom event handler (`MNMathTargets.FIELD_CALL_ALLOWED`)
* **Message API routing** - domain-specific 
  * Requires the use of a custom TransportManager or HandleFilter
* **Message-level security** - partially implemented / domain-specific
  * This includes things like "Reject MOTD from the clients" and "Reject unauthenticated messages".
    Those are currently implemented.
  * This also includes things like "Encrypt all messages". This is a domain-specific area -
    everything can be done through middlewares, and also goes out of the scope of the library.
* **Protocol-level security** - not implemented
  * This includes things like
    "Prevent a client from sending 4 billion bytes in one socket operation" and
    "Prevent 100000 clients from being created on the same IP".
    I am not totally sure how do prevent this, anyway, and am open to suggestions.

### Different scenarios

* **Local development** - functional
* **Single all-to-all communication** - functional
* **High-load scenarios** - not implemented
  * For high-load scenarios, sending any message that is not pointing at a certain
    client, it will be routed to every single connected client. This is quite slow
    in Python. For these, I recommend making a middleware server, so that the server talks
    to the middleware, the clients talk to the middleware, and the server is behind
    a firewall so it can't be directly connected to. Unfortunately this does not fix
    all of the problems of such setups unless the middleware is written in a language like
    Rust, which goes beyond the scope of this library.
  * Another possible remedy is to have a middleware chain acting as a load balancer. For example,
    the server talks to 10 middlewares, and each client connection is sent to one of them.
    This reduces the load substantially, allowing better scaling, but is significantly harder
    to implement. It also requires an ability to "transfer" a connection from one pair of clients
    to another pair of clients (see above).

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

---

## Caveats

* This project is a work-in-progress, and things may change at any time.
  More importantly, many components have not been implemented yet.
* Things like Trio/Curio/etc.-based event loops and network transports
  will not be implemented in the main library. (On the flip side, those aren't too hard to write
  if you need them in your application!)
* I am not a security specialist, so some fatal mistakes may have slipped through.
  Please report any security issues you find on the issue tracker so I can fix them!
* The message processing is synchronous, as this library has to work in both synchronous
  and asynchronous contexts. This means if your messages require something like database interaction,
  it will be harder to do efficiently without callback hell (synchronous database handlers 
  tend to be quite slow). I do not currently have a solution in mind,
  but will implement one if a reasonably good one is suggested.

---

## Comparison with similar libraries

### gRPC

gRPC is a very popular library for building networked applications. The scope of gRPC is
quite different from MagicNet, however:

* Any message in gRPC is sent from the client, which will then expect a response.
  This means the library is not suitable for real-time applications, which will often
  send messages from the server to the client, and messages don't have a response
  (which can be simulated by sending a message back).
* For gRPC language compatibility is very important. While the protocol of MagicNet
  is language-agnostic, the library itself is written in Python and will require additional work
  to be used in other languages.
* gRPC's protocol has to be configured through Protobuf. While this is important for language
  compatibility, it is less intuitive than using typehints.

### Astron

Astron is a library for building real-time applications, originally made for Disney's Toontown Online.
MagicNet is inspired by Astron in many ways, as I have worked with Astron for a long time.
(In fact, the reason why MagicNet was created is because there was not a powerful enough networking
library that worked with Panda3D!) That said there are some key differences:

* The core of Astron is written in C++, while MagicNet is written in Python.
  This means that Astron is much faster, but also much harder to use.
  (This can be somewhat remedied by rewriting the core of the library in a modern language, which is planned.)
* Astron currently doesn't have a free (as in, not proprietary) client implementation.
  The CMU protocol implemented in Panda3D does not incorporate many of the features of the Astron protocol,
  such as Distributed objects. In addition, the Panda3D implementation only really works
  with the event loop of that engine, which means AsyncIO cannot be used easily.
* Adding custom message codes to most Astron implementations is relatively difficult due to the
  way the software is designed. MagicNet is designed to be as flexible as possible in this regard.
* The distributed fields have to be configured through DC files, which are not very intuitive.
  MagicNet uses typehints instead, which are much easier to use.

In general Astron is quite archaic and tends itself to be used in a very specific way
(mostly creating MMORPG games) due to the complexity of the server component, although it's quite good at that.
MagicNet is better suitable for smaller projects, and is much easier to use.

