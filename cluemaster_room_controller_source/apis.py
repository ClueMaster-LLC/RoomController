master_base_url = "https://devapi.cluemaster.io/"

# apis available to cluemaster room controller
GENERATE_API_TOKEN_API = "https://deviceapi.cluemaster.io/api/Auth/PostGenerateApiKey"
ROOM_CONTROLLER_REQUEST_API = master_base_url + "api/roomcontroller/GetRoomControllerRequest/{device_id}"
POST_ROOM_CONTROLLER_REQUEST = master_base_url + "api/roomcontroller/PostRoomControllerRequest/{device_id}/{request_id}"
