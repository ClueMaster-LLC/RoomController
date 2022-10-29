master_base_url = "https://devapi.cluemaster.io/"
# apis available to cluemaster room controller

# GETs
GENERATE_API_TOKEN_API = master_base_url + "api/Auth/PostGenerateApiKey"
ROOM_CONTROLLER_REQUEST_API = master_base_url + "api/roomcontroller/GetRoomControllerRequest/{device_id}"
NEW_RELAYS_DISCOVERY_REQUEST = master_base_url + "api/roomcontroller/GetNewInputRelayDiscoveryRequest/{device_id}"
GET_NEW_INPUT_RELAY_LIST_REQUEST = master_base_url + "api/roomcontroller/GetNewInputRelayListRequest/{device_id}"
GET_NEW_INPUT_RELAY_LIST = master_base_url + "api/roomcontroller/GetLatestInputRelayList/{device_id}"

# POSTs
POST_ROOM_CONTROLLER_REQUEST = master_base_url + "api/roomcontroller/PostRoomControllerRequest/{device_id}/{request_id}"
POST_NEW_INPUT_RELAY_DISCOVERY = master_base_url + "api/roomcontroller/PostNewInputRelayDiscovery/devicekey?devicekey={device_id}"
POST_INPUT_RELAY_REQUEST_UPDATE = master_base_url + "api/roomcontroller/PostInputRelayRequestUpdate/"
