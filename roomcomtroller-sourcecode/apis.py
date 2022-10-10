master_base_url = "https://devapi.cluemaster.io/"

# apis available to cluemaster room controller
GENERATE_API_TOKEN_API = "https://devapi.cluemaster.io/api/Auth/PostGenerateApiKey"
ROOM_CONTROLLER_REQUEST_API = master_base_url + "api/roomcontroller/GetRoomControllerRequest/{device_id}"
POST_ROOM_CONTROLLER_REQUEST = master_base_url + "api/roomcontroller/PostRoomControllerRequest/{device_id}/{request_id}"
NEW_RELAYS_DISCOVERY_REQUEST = master_base_url + "api/roomcontroller/GetNewInputRelayDiscoveryRequest/{device_id}"

POST_NEW_INPUT_RELAY_DISCOVERY = master_base_url + "api/roomcontroller/PostNewInputRelayDiscovery/{device_id}/" \
                                                   "{device_desc}/{number_of_relays}/{type}/{ip_address}/" \
                                                   "{serial_number}/{number_of_input}"

