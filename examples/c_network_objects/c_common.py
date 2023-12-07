from magicnet.batteries.encoders import MsgpackEncoder
from magicnet.batteries.middlewares.message_validation import MessageValidatorMiddleware
from magicnet.batteries.transports.socket_asyncio import AsyncIOSocketTransport
from magicnet.core.transport_manager import TransportParameters

middlewares = [MessageValidatorMiddleware]
encoder = MsgpackEncoder()
transport = {
    "client": {
        "server": TransportParameters(
            encoder, AsyncIOSocketTransport, None, middlewares
        )
    }
}

client_signature = "client-signature.json"
server_signature = "server-signature.json"
signature_filenames = [client_signature, server_signature]
