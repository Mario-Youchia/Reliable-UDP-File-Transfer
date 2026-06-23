import socket
import sys
import itertools
import datetime
import hashlib
import time
import os
import tqdm
import inspect
import threading
import playsound
from tqdm.auto import tqdm as progressBar

os.system('cls')

# Set the socket parameters
arguments_number = 3
# Read filename, receiver IP address and receiver port from command line interface args
if len(sys.argv) < arguments_number:
    print("\033[91mExpected Format: python receiver.py <filename> <host> <port>\033[0m")
    sys.exit(1)

host = sys.argv[1]
port = int(sys.argv[2])

packet_id_size = 2
file_id_size = 2
trailer_size = 4
MSS = 1024
file_size_bytes = 8
key_file_name = 'Key File.txt'
file_key_length = 32 #bytes
# Get the current minute of the hour
current_time = datetime.datetime.now()
hour = current_time.hour
minute = current_time.minute
second = current_time.second

# Generate the key based on the minute
Key = (hour + minute) % 256
#print("Hour",hour,"minute",minute)

print(f"Private key is \033[92m{Key}\033[0m")
max_allowed_file_size = 64e6

directory = "Received Files"
# Create the directory if it doesn't exist
if not os.path.exists(directory):
    os.makedirs(directory)

def decryption(key, encrypted_data):
    # Step 1: Decrypt the data using XOR
    encrypted_data = [[int.from_bytes(byte, byteorder='big') for byte in sublist] for sublist in encrypted_data]
    decrypted_data = []
    for sublist in encrypted_data:
        encrypted_sublist = [b ^ key for b in sublist]
        decrypted_data.append(encrypted_sublist)
    # Step 2: Split all sublists into 2 equal parts and concatenate them in the reverse order
    result = []
    for i in range(len(decrypted_data)):
      if i == 0 and i == len(decrypted_data) - 1:
        partA = decrypted_data[i][:len(decrypted_data[i]) // 2]
        partB = decrypted_data[i][len(decrypted_data[i]) // 2:]
      elif i == 0:
        partA = decrypted_data[i][:MSS // 2]
        partB = decrypted_data[len(decrypted_data) - 1 - i][-MSS // 2:]
      elif i == len(decrypted_data) - 1:
        partA = decrypted_data[i][:len(decrypted_data[i]) - MSS // 2]
        partB = decrypted_data[len(decrypted_data) - 1 - i][MSS // 2:]
      else:
        partA = decrypted_data[i][:len(decrypted_data[i]) // 2]
        partB = decrypted_data[len(decrypted_data) - 1 - i][len(decrypted_data[len(decrypted_data) - 1 - i]) // 2:]
      subResult = []
      subResult.extend(partA)
      subResult.extend(partB)
      result.append(subResult)
    decryption = result
    # Step 3: Flip each two adjacent bytes in the sublist
    for sublist in decryption:
        for i in range(0, len(sublist), 2):
            if i < len(sublist) - 1:
                sublist[i], sublist[i+1] = sublist[i+1], sublist[i]
    return bytes(list(itertools.chain.from_iterable(decryption)))

buffer_size = packet_id_size + file_id_size + MSS + trailer_size

# Modifying the print function to print progress bars
old_print = print
def new_print(*args, **kwargs):
    try:
        tqdm.tqdm.write(*args, **kwargs)
    except:
        old_print(*args, ** kwargs)
inspect.builtins.print = new_print

def bar(function, string, expectedDuration, args):
    def track_progress():
        _percentage = 0
        with tqdm.tqdm(total=100, bar_format=f'{string}:' + ' {percentage:.0f}% {bar}') as pbar:
            while not func_completed:
                if _percentage < pbar.total:
                    _percentage += 1
                    pbar.update(_percentage - pbar.n)
                    if _percentage < pbar.total/3:
                        pbar.colour = "red"
                    elif _percentage < (pbar.total*2)/3:
                        pbar.colour = 'yellow'
                    else:
                        pbar.colour = 'green'
                    pbar.set_postfix(progress=_percentage)
                time.sleep(expectedDuration/pbar.total)
            pbar.update(pbar.total - pbar.n)
            pbar.colour = 'green'
    global func_completed
    func_completed = False
    progress_thread = threading.Thread(target=track_progress)
    progress_thread.start()
    try:
        value = function(*args)
    except TypeError:
        value = function()
    func_completed = True
    progress_thread.join()
    return value
time_to_read_key_file = 0.02665090560913086 # By Simulation
time_to_decrypt_50MB_file = 43.995115518569946 # By Simulation
# read the contents of the key file
def get_key_file(fileName):
    with open(fileName, 'r') as f:
        key_file_data = f.read()
    # convert the string to bytes and generate the hash, finally get the key
    return hashlib.sha256(key_file_data.encode()).digest()
file_key = bar(function=get_key_file, string="Reading Key File", expectedDuration=time_to_read_key_file, args=(key_file_name, ))
print(f"File key is \033[92m{file_key}\033[0m")

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the host and port
sock.bind((host, port))

# Receive the packets
cumulative_packet_id = 0
cumulative_timeout = 0
cumulative_bytes_received = 0
cumulative_duplicates = 0
max_timeout = 10
ack_timeout = 10
sock.settimeout(ack_timeout)
expected_file_id = 0
prev_cumulative_packet_id = 0
while True:
    isLost = True
    expected_packet_id = 0
    num_of_duplicates = 0
    file_data = []
    if expected_file_id % 2 == 0:
        start_time = (datetime.datetime.now() + datetime.timedelta(hours=0)).strftime("%Y-%b-%d %I:%M:%S %p")
        start_time_seconds = time.time()
        bytes_received = 0
        print(f"\033[104m################################################ Receiving Proces Started ################################################\033[0m")
    else:
        pbar = progressBar(total=(int(file_size/MSS)+int(file_size/MSS > int(file_size/MSS))), bar_format=f'{"Receiving File"}:' + ' {percentage:.0f}% {bar}', position=0) #position=0
    while True:
        # Setting a delay to visualize the progress bar, ONLY FOR DEMONSTRATION
        #time.sleep(0.1)
        try:
            packet, addr = sock.recvfrom(buffer_size)
            # Extract the packet ID, file ID, data, and trailer from the packet
            packet_id = int.from_bytes(packet[:packet_id_size], byteorder="big")
            file_id = int.from_bytes(packet[file_id_size:packet_id_size+file_id_size], byteorder="big")
            data = packet[packet_id_size+file_id_size:-trailer_size]
            data = [data[i].to_bytes(1,byteorder='big') for i in range(len(data))]
            trailer_bit = int.from_bytes(packet[-trailer_size:], byteorder="big")
            # Check if the packet ID is as expected
            if file_id == expected_file_id:
                if packet_id - cumulative_packet_id == expected_packet_id:
                    file_data.append(data)
                    expected_packet_id += 1
                    ack_packet = packet[:packet_id_size+file_id_size]
                    isLost = False
                    cumulative_timeout = 0
                    if trailer_bit == 0xFFFF:
                        print(f"Successfully received {'the last ' if trailer_bit == 0xFFFF else ''}packet {packet_id}") #'\t'
                    elif packet_id < 100:
                        print(f"Successfully received {'the last ' if trailer_bit == 0xFFFF else ''}packet {packet_id}") #'\t\t\t'
                    elif packet_id > 99:
                        print(f"Successfully received {'the last ' if trailer_bit == 0xFFFF else ''}packet {packet_id}") #'\t\t'
                elif packet_id - cumulative_packet_id > expected_packet_id or file_id != expected_file_id:
                    print(f"\033[91mError: Missing packet {expected_packet_id + cumulative_packet_id}\033[0m")
                    try:
                        ack_packet = (expected_packet_id + cumulative_packet_id -1).to_bytes(packet_id_size, byteorder="big") + \
                            packet[file_id_size:packet_id_size + file_id_size]
                    except OverflowError:
                        print("\n\033[91mError: No more packets could be received.\033[m")
                        print("\033[91mExiting Receiver ... \033[0m\U0001F44B")
                        sys.exit()
                elif packet_id - cumulative_packet_id < expected_packet_id:
                    num_of_duplicates += 1
                    print(f"\033[91mError: Duplicate packet {packet_id}, Note: duplicate packet is discarded\033[0m")
            else:
                print(f"\033[91mError: Expected File ID is {expected_file_id} but Received is {file_id}\033[0m")
            # Send the acknowledgement
            sock.sendto(ack_packet, addr)
            # Check if we have received all the packets, the isLost boolean indicates whether there is a loss or not
            if trailer_bit == 0xFFFF and isLost == False:
                prev_cumulative_packet_id = cumulative_packet_id
                cumulative_packet_id += expected_packet_id
                break
            isLost = True
            try:
                if pbar.total != 0 and expected_file_id % 2 != 0:
                    pbar.update(packet_id - cumulative_packet_id - pbar.n) # = pbar.n
                    pbar.refresh()
                    if packet_id - cumulative_packet_id < pbar.total/3:
                        pbar.colour = "red"
                    elif packet_id - cumulative_packet_id < (pbar.total*2)/3:
                        pbar.colour = 'yellow'
                    else:
                        pbar.colour = 'green'
                    pbar.set_postfix(progress=packet_id - cumulative_packet_id)
            except NameError:
                pass
            print(f"\t\t\t\t\tSending Acknowledgement: {int.from_bytes(ack_packet[:packet_id_size], byteorder='big')}")
        except socket.timeout:
            cumulative_timeout += 1
            if cumulative_timeout > max_timeout:
                print("\033[91mConnection Timeout. Try to connect later.\033[0m")
                print("\033[91mExiting Receiver ... \033[0m\U0001F44B")
                connection_timeout = True
                sys.exit()
            print("\033[91mTimeout: Waiting for something to be sent.\033[0m")
    try:
        if pbar.total != 0 and expected_file_id % 2 != 0:
            pbar.update(pbar.total - pbar.n)
            pbar.colour = 'green'
        pbar.close()
    except NameError:
        pass
    if (expected_file_id % 2 == 0):
        metadata = bar(function=decryption, string="Decrypting File", expectedDuration=(time_to_decrypt_50MB_file*len(file_data))/50e6, args=(Key, file_data))
        file_name = metadata[:-file_size_bytes-file_key_length].decode('utf-8')
        file_size = int.from_bytes(metadata[-file_size_bytes-file_key_length:-file_key_length], byteorder='big')
        file_key_received = metadata[-file_key_length:]
        print(f"File Name: \033[92m{file_name}\033[0m")
        print(f"File Size: \033[92m{file_size}\033[0m")
        print(f"File Key Received: \033[92m{file_key_received}\033[0m")
        bytes_received += file_size + file_size_bytes + len(file_key) + len(file_name) #For the Random1MB file: 1,000,000 + 8 + 32 + 9 = 1,000,049 Bytes
        if file_key_received != file_key:
            print(f"\033[91mError: Signature Mismatch!\033[0m")
            print("\033[91mExiting Receiver ... \033[0m\U0001F44B")
            sys.exit()
        if file_size > max_allowed_file_size or cumulative_packet_id * MSS + file_size > max_allowed_file_size + MSS:
            print(f"\033[91mError: Cannot receive more than 64 MB.\033[0m")
            print(f"\033[91mNote: File \"{file_name}\" is not received.\033[0m")
            print("\033[91mExiting Receiver ... \033[0m\U0001F44B")
            sys.exit()
        def waitingFunc():
            i = 0
            while (i < int(file_size/2.5e6) + int(file_size/2.5e6 > int(file_size/2.5e6))):
                i += 1 # Assuming each 2.5MBs are processed in 1 second
                time.sleep(1)
        bar(function=waitingFunc, string="Waiting for the sender to process the file", expectedDuration=(int(file_size/2.5e6) + int(file_size/2.5e6 > int(file_size/2.5e6))), args=None)
    else:
        cumulative_bytes_received += bytes_received
        cumulative_duplicates += num_of_duplicates
        print(f"File \033[92m{file_name}\033[0m of size \033[92m{file_size}\033[0m bytes has been received successfully received. \U0001f600")
        print(f'\033[42mNetwork Performance Metrics at the receiver:\033[0m')
        print(f'Start Time:\033[92m {start_time}\033[0m')
        end_time = (datetime.datetime.now() + datetime.timedelta(hours=0)).strftime("%Y-%b-%d %I:%M:%S %p")
        print(f'End Time:\033[92m {end_time}\033[0m')
        elapsed_seconds = time.time() - start_time_seconds
        print(f"Elapsed Time:\033[92m {int(elapsed_seconds // 3600)} Hours, {int((elapsed_seconds % 3600) // 60)} Minutes, {round((elapsed_seconds % 3600) % 60,2)} Seconds\033[0m")
        print(f"Number of Packets received for this file:\033[92m {expected_packet_id + 1} Packets\033[0m")
        print(f"Total Number of Packets sent for all files:\033[92m {expected_packet_id + prev_cumulative_packet_id} Packets\033[0m")
        print(f"Number of Bytes sent for this file \033[4mWITHOUT Header and Trailer\033[0m:\033[92m {bytes_received:,} Bytes\033[0m")
        print(f"Number of Bytes sent for this file \033[4mWITH Header and Trailer\033[0m:\033[92m {bytes_received + (expected_packet_id + 1) * (packet_id_size + file_id_size + trailer_size):,} Bytes\033[0m")
        print(f"Total Number of Bytes sent for all files \033[4mWITHOUT Header and Trailer\033[0m:\033[92m {cumulative_bytes_received:,} Bytes\033[0m")
        print(f"Total Number of Bytes sent for all files \033[4mWITH Header and Trailer\033[0m:\033[92m {cumulative_bytes_received + (expected_packet_id + prev_cumulative_packet_id) * (packet_id_size + file_id_size + trailer_size):,} Bytes\033[0m")
        print(f"Number of Received Duplicates for this file: \033[92m{num_of_duplicates:,}\033[0m")
        print(f"Total Number of Received Duplicates for all files: \033[92m{cumulative_duplicates:,}\033[0m")
        avg_receiving_rate_packets_sec = (expected_packet_id + 1) / elapsed_seconds
        avg_receiving_rate_bytes_sec =  (bytes_received + (expected_packet_id + 1) * (packet_id_size + file_id_size + trailer_size)) / elapsed_seconds
        print(f"Average Receiving Rate: \033[92m{round(avg_receiving_rate_packets_sec,2):,} packets/sec\033[0m")
        print(f"Average Receiving Rate: \033[92m{round(avg_receiving_rate_bytes_sec,2):,} bytes/sec\033[0m")
        # Write the received data to a file
        file_data = bar(function=decryption, string="Decrypting File", expectedDuration=(time_to_decrypt_50MB_file*len(file_data))/50e6, args=(Key, file_data))
        file_path = os.path.join(directory, file_name)
        with open(file_path, "wb") as f:
            f.write(file_data)
        sound_file = "Notification.wav"
        playsound.playsound(sound_file)
        os.startfile(directory)
    expected_file_id += 1