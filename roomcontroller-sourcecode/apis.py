master_base_url = "https://dev-deviceapi.cluemaster.io/"
# signalr_hub_url = "https://cluemaster-signalr-win.azurewebsites.net/"
signalr_hub_url = "wss://dev-comhub.cluemaster.io/"
# apis available to cluemaster room controller

# GETs
GENERATE_API_TOKEN_API = master_base_url + "api/Auth/PostGenerateApiKey"
ROOM_CONTROLLER_REQUEST_API = master_base_url + "api/roomcontroller/GetRoomControllerRequest/{device_id}"
NEW_RELAYS_DISCOVERY_REQUEST = master_base_url + "api/roomcontroller/GetNewInputRelayDiscoveryRequest/{device_id}"
GET_NEW_INPUT_RELAY_LIST_REQUEST = master_base_url + "api/roomcontroller/GetNewInputRelayListRequest/{device_id}"
GET_NEW_INPUT_RELAY_LIST = master_base_url + "api/roomcontroller/GetLatestInputRelayList/{device_id}"
GET_ROOM_AUTOMATION_MASTER = master_base_url + "api/roomcontroller/GetRoomAutomationMaster/{device_id}"
GET_ROOM_CONTROLLER_AUTOMATION_REQUEST = master_base_url + "api/roomcontroller/GetRoomControllerAutomationRequest/{device_id}"

# POSTs
POST_ROOM_CONTROLLER_REQUEST = master_base_url + "api/roomcontroller/PostRoomControllerRequest/{device_id}/{request_id}"
POST_NEW_INPUT_RELAY_DISCOVERY = master_base_url + "api/roomcontroller/PostNewInputRelayDiscovery?devicekey={device_id}"
POST_INPUT_RELAY_REQUEST_UPDATE = master_base_url + "api/roomcontroller/PostInputRelayRequestUpdate"
POST_ROOM_CONTROLLER_ERRORLOG = master_base_url + "api/roomcontroller/PostLogError/{device_id}/{ErrorLog}"
POST_DEVICE_HEARTBEAT = master_base_url + "api/Device/PostDeviceHeartBeat/{device_id}/{CpuAvg}/{MemoryAvg}/{NetworkAvg}"

# SIGNALR
API_SIGNALR = signalr_hub_url + "chathub"
