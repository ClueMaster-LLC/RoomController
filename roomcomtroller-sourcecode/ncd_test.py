# import the pyserial module
import socket
import ncd_industrial_devices

# set up your socket with the desired settings.
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# instantiate the board object and pass it the network socket
ncd = ncd_industrial_devices.NCD_Controller(sock)
# connect the socket using desired IP and Port
IP_ADDRESS = "192.168.1.19"
PORT = 2101
sock.connect((IP_ADDRESS, PORT))
sock.settimeout(1.5)

print(ncd.get_dc_all_inputs())  # get value of all banks and inputs
print(ncd.get_dc_bank_status(0))  # get value of single bank inputs
print(ncd.get_dc_bank_status(1))  # get value of single bank inputs

# close the interface, not necessary here, but you may need to in your application
sock.close()
