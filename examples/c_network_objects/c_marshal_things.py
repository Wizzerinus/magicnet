from c_network_objects import c_client, c_common, c_server


def main():
    c_client.manager.marshalling_mode = c_common.client_signature
    c_server.manager.marshalling_mode = c_common.server_signature
    c_client.manager.object_registry.activate()
    c_server.manager.object_registry.activate()
    print("Marshalling done!")


if __name__ == "__main__":
    main()
