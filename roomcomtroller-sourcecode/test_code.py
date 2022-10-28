import json
import os
import requests
from apis import *
from requests.structures import CaseInsensitiveDict

# BASE DIRECTORIES
ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
MASTER_DIRECTORY = os.path.join(os.environ.get("HOME"), "CluemasterRoomController")
APPLICATION_DATA_DIRECTORY = os.path.join(MASTER_DIRECTORY, "assets/application_data")


def main():
    with open(os.path.join(APPLICATION_DATA_DIRECTORY, "unique_ids.json")) as unique_code_file:
        unique_codes_file_response = json.load(unique_code_file)
        device_id = unique_codes_file_response["device_id"]
        api_token = unique_codes_file_response["api_token"]

    # api bearer data ---
    api_bearer_data = CaseInsensitiveDict()
    api_bearer_data["Authorization"] = f"basic {device_id}:{api_token}"
    api_bearer_data['Content-Type'] = 'application/json'
    print(api_bearer_data)

    # api details ---
    post_new_input_relay_discovery = POST_NEW_INPUT_RELAY_DISCOVERY.format(device_id=device_id)
    devices_info = [{"IP": "192.168.0.1921", "ServerPort": 2101, "MacAddress": "MRITTUNJOYSE"},
                    {"IP": "192.168.2.21", "ServerPort": 2101, "MacAddress": "MRITTUNJOYED"}]

    # requests ---
    api_response = requests.post(post_new_input_relay_discovery, headers=api_bearer_data, data=json.dumps(devices_info))
    print("API Status Code - ", api_response.status_code)
    print("Url", api_response.url)
    print("API Response - ", api_response.text)


main()
