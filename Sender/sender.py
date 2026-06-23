import socket
import sys
import select
import os
import itertools
import datetime
import hashlib
import time
import threading
import tqdm
import inspect
import matplotlib.pyplot

os.system('clear')
# Set the socket parameters
packet_id_size = 2
file_id_size = 2
MSS = 1024 # 1 kB
cwnd = 1
# Large Max_cwnd with small timeout will result in more losses
Max_cwnd = 32
ack_timeout = 0.01
ssthresh = 12
dupACKcount = 0
max_timeout = 1000
cumulative_timeout = 0
connection_timeout = False
trailer_size = 4
buffer_size = packet_id_size + file_id_size
arguments_number = 4
input_timeout = 10
file_size_bytes = 8
file_size = 0
key_file_name = 'Key File.txt'
# Get the current minute of the hour
current_time = datetime.datetime.now()
hour = current_time.hour
minute = current_time.minute
second = current_time.second

# Generate the key based on time
Key = (hour + minute + 1) % 256

def encryption(key, data):
    # Step 1: Flip each two adjacent bytes in the sublist
    for sublist in data:
        for i in range(0, len(sublist), 2):
            if i < len(sublist) - 1:
                sublist[i], sublist[i+1] = sublist[i+1], sublist[i]
    # Step 2: Split all sublists into 2 equal parts and concatenate them in the reverse order
    result = []
    for i in range(len(data)):
        partA = data[i][:len(data[i]) // 2]
        partB = data[len(data) - 1 - i][len(data[len(data) - 1 - i]) // 2:]
        subResult = []
        subResult.extend(partA)
        subResult.extend(partB)
        result.append(subResult)
    data = result
    # Step 3: Encrypt the data using XOR
    encrypted_data = []
    for sublist in data:
        encrypted_sublist = [b ^ key for b in sublist]
        encrypted_data.append(encrypted_sublist)
    return [[encrypted_byte.to_bytes(1, byteorder='big') for encrypted_byte in sublist] for sublist in encrypted_data]

# The following functions will be used to handle sender interruptions
# Saving cumulative_packet_id to a file
def save_cumulative_packet_id(cumulative_packet_id):
    with open("cumulative_packet_id", "w") as file:
        file.write(str(cumulative_packet_id))

# Reading cumulative_packet_id from a file
def read_cumulative_packet_id():
    try:
        with open("cumulative_packet_id", "r") as file:
            cumulative_packet_id = int(file.read())
    except FileNotFoundError:
        cumulative_packet_id = 0
    return cumulative_packet_id

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

time_to_read_key_file = 0.0013217926025390625 # By simulation
time_to_encrypt_50MB_file = 17.00293788909912 # By simulation

directory = "Plots History"
def plot_pktID_vs_time(x_axis_data, y_axis_data, num_of_retransmissions, simulated_loss_rate, Transfer_Rate, isDynamicW = True, step = 1, cwnd = 1, timeout = 1, directory = "Plots History"):
    figure_width = 10
    figure_height = 5
    image_dpi = 640
    x_label = 'Time (msec)'
    y_label = 'Packet ID'
    plot_title = 'Packet ID vs Time'
    base_image_name = "Plot "
    matplotlib.pyplot.figure(figsize=(figure_width, figure_height))

    # Iterate over y_axis_data values and plot data points
    if step < 1:
        step = 1
    for i in range(0, len(y_axis_data), step):
        # Marking subsequent occurrences of the repeated value with red color
        matplotlib.pyplot.scatter(x_axis_data[i]*1000, abs(y_axis_data[i]), color = 'red' if y_axis_data[i] < 0 else 'blue')

    matplotlib.pyplot.xlabel(x_label)
    matplotlib.pyplot.ylabel(y_label)
    matplotlib.pyplot.title(plot_title)

    # Adjust spacing
    bottom_distance = 0.18
    left_distance = 0.075
    right_distance = 0.97
    top_distance = 0.93
    matplotlib.pyplot.subplots_adjust(bottom=bottom_distance, right=right_distance, left=left_distance, top=top_distance)

    # Show grid
    matplotlib.pyplot.grid(True)

    # Create empty lists for legend handles and labels
    legend_handles = []
    legend_labels = []
    # Add handles and labels to the legend lists
    legend_handles.append(matplotlib.pyplot.Line2D([], [], marker='o', color='red', linestyle='None'))
    legend_labels.append('Repeated')
    legend_handles.append(matplotlib.pyplot.Line2D([], [], marker='o', color='blue', linestyle='None'))
    legend_labels.append('Not Repeated')
    # Create the legend with the provided handles and labels
    matplotlib.pyplot.legend(legend_handles, legend_labels, loc='best', edgecolor='black', framealpha=1)


    # Add caption based on the case:
    if isDynamicW:
        caption1 = "This figure shows a plot of the received packet ID versus time with the following properties: cwnd is "
        caption2 = "dynamic"
        caption3 = ", Simulated Loss Rate = "
        caption4 = f"{simulated_loss_rate}%"
        caption5 = ", timeout is "
        caption6 = "variable"
        caption7 = "based on the network's condition"
        caption8 = ", Number of Retransmissions = "
        caption9 = f"{num_of_retransmissions:,}"
        caption10 = ", and Transfer Rate = "
        caption11 = f"{Transfer_Rate:,} bytes/sec"
        
        # First Line
        left_shift = 0.04
        matplotlib.pyplot.figtext(0.400 - left_shift, 0.06, caption1, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.780 - left_shift, 0.06, caption2, ha='center', fontsize=10, color='green')
        matplotlib.pyplot.figtext(0.895 - left_shift, 0.06, caption3, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.999 - left_shift, 0.06, caption4, ha='center', fontsize=10, color='green') 
        # Second Line
        left_shift = 0.08
        matplotlib.pyplot.figtext(0.140 - left_shift, 0.03, caption5, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.210 - left_shift, 0.03, caption6, ha='center', fontsize=10, color='green')
        matplotlib.pyplot.figtext(0.360 - left_shift, 0.03, caption7, ha='center', fontsize=10, color='blue')
        matplotlib.pyplot.figtext(0.585 - left_shift, 0.03, caption8, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.720 - left_shift, 0.03, caption9, ha='center', fontsize=10, color='green')
        matplotlib.pyplot.figtext(0.820 - left_shift, 0.03, caption10, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.970 - left_shift, 0.03, caption11, ha='center', fontsize=10, color='green')
    else:
        caption1 = "This figure shows a plot of the received packet ID versus time with the following properties: cwnd = "
        caption2 = f"{cwnd}"
        caption3 = ", Simulated Loss Rate = "
        caption4 = f"{simulated_loss_rate}%"
        caption5 = ", timeout = "
        caption6 = f"{round(timeout*1000)} msec"
        caption8 = ", Number of Retransmissions = "
        caption9 = f"{num_of_retransmissions:,}"
        caption10 = ", and Transfer Rate = "
        caption11 = f"{Transfer_Rate:,} bytes/sec"
        
        # First Line
        left_shift = 0.0
        matplotlib.pyplot.figtext(0.400 - left_shift, 0.06, caption1, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.760 - left_shift, 0.06, caption2, ha='center', fontsize=10, color='green')
        matplotlib.pyplot.figtext(0.853 - left_shift, 0.06, caption3, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.959 - left_shift, 0.06, caption4, ha='center', fontsize=10, color='green') 
        # Second Line
        left_shift = -0.05
        matplotlib.pyplot.figtext(0.140 - left_shift, 0.03, caption5, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.220 - left_shift, 0.03, caption6, ha='center', fontsize=10, color='green')
        matplotlib.pyplot.figtext(0.370 - left_shift, 0.03, caption8, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.505 - left_shift, 0.03, caption9, ha='center', fontsize=10, color='green')
        matplotlib.pyplot.figtext(0.608 - left_shift, 0.03, caption10, ha='center', fontsize=10)
        matplotlib.pyplot.figtext(0.753 - left_shift, 0.03, caption11, ha='center', fontsize=10, color='green')
    
    # Saving the figure to add it to the report
    # Create the directory if it doesn't exist
    if not os.path.exists(directory): os.makedirs(directory)
    plot_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H%M%S")
    image_name = base_image_name + plot_time + ".png"
    file_path = os.path.join(directory, image_name)
    matplotlib.pyplot.savefig(file_path, dpi = image_dpi)
    matplotlib.pyplot.show()

plot_time = []
plot_packet_id = []

# Read filename, receiver IP address and receiver port from command line interface args
if len(sys.argv) < arguments_number:
    print("\033[91mExpected Format: python3 sender.py <filename> <receiver_ip> <receiver_port>\033[0m")
    sys.exit(1)

file_name = sys.argv[1] #Availabe Files: {SmallFile.png, MediumFile.jpg, LargFile.jpg}
host = sys.argv[2]
port = int(sys.argv[3])

print(f"Private key is \033[92m{Key}\033[0m")

# read the contents of the key file
def get_key_file(fileName):
    with open(fileName, 'r') as f:
        key_file_data = f.read()
    # convert the string to bytes and generate the hash, finally get the key
    return hashlib.sha256(key_file_data.encode()).digest()
file_key = bar(function=get_key_file, string="Reading Key File", expectedDuration=time_to_read_key_file, args=(key_file_name, ))
print(f"\nFile key is \033[92m{file_key}\033[0m")
# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set the timeout value for waiting for acknowledgements
sock.settimeout(ack_timeout)
# Open the file to be sent
cumulative_packet_id = 0
cumulative_bytes_sent = 0
cumulative_retransmissions = 0
file_id = 0
timer = time.time()
ALPHA = 0.125
BETA = 0.25
timers = []
estimated_rtt = 1 # Initial Value
dev_rtt = 0.5 # Initial Value
#bytes_sent = 0
retransmitted_bytes = 0

while True:
    isLost = True
    num_of_retransmissions = 0
    if file_id % 2 == 0: #Sending Metadata first
        start_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%b-%d %I:%M:%S %p")
        start_time_seconds = time.time()
        file_size = os.stat(file_name).st_size
        encoded_file_name = bytes(file_name, 'utf-8')
        bytes_sent = 0
        bytes_sent += file_size + file_size_bytes + len(file_key) + len(encoded_file_name) #For the Random1MB file: 1,000,000 + 8 + 32 + 9 = 1,000,049 Bytes
        file_data = encoded_file_name + file_size.to_bytes(file_size_bytes, byteorder='big') + file_key
        print(f"\033[7m################################################ Sending Proces Started ################################################\033[0m")
    else:
        with open(file_name, "rb") as f:
            file_data = f.read()
    print(f"Sending file `\033[92m{file_name}\033[0m`...")
    # Convert bytes to integers
    file_data = [_ for _ in file_data]
    # Split the file into chunks
    temp_chunks = [file_data[i:i+MSS] for i in range(0, len(file_data), MSS)]
    # Encypting data
    chunks = bar(function=encryption, string="Encrypting File", expectedDuration=(time_to_encrypt_50MB_file*len(file_data))/50e6, args=(Key, temp_chunks))
    print("")
    # Send the packets
    last_sent_packet_id = -1
    base_packet_id = 0
    unacknowledged_packets = 0
    pbar = tqdm.tqdm(total=len(chunks), bar_format=f'{"Sending File"}:' + ' {percentage:.0f}% {bar}', position=0)
    ref_time = time.time()
    plot_time = []
    plot_packet_id = []
    while base_packet_id < len(chunks):
        # Setting a delay to visualize the progress bar, ONLY FOR DEMONSTRATION
        #time.sleep(0.1)
        # Send packets that are within the window and have not been sent before
        # Check if there is a space in the window, and there is still packets to be sent
        while unacknowledged_packets < cwnd and last_sent_packet_id < len(chunks) - 1:
            last_sent_packet_id += 1
            # Add the packet ID, file ID, chunk, and trailer to the packet
            packet_id = last_sent_packet_id + cumulative_packet_id
            chunk = chunks[last_sent_packet_id]
            # Converting list of bytes to bytes
            chunk = bytes(itertools.chain.from_iterable(chunk))
            try:
                packet = packet_id.to_bytes(packet_id_size, byteorder="big") + file_id.to_bytes(file_id_size, byteorder="big") + chunk + \
                    ((0x0000).to_bytes(trailer_size, byteorder="big") if last_sent_packet_id != len(chunks) - 1 else (0xFFFF).to_bytes(trailer_size, byteorder="big"))
            except OverflowError:
                print("\n\033[91mError: No more packets could be sent.\033[0m\U0001F614")
                print("Exiting Sender ... \U0001F44B")
                sys.exit()
            print(f"cwnd = {cwnd}\tssthresh = {ssthresh}\tdupACKcount = {dupACKcount}", end = '\t\t')
            print(f"Sending packet: {packet_id}")
            timers.append(time.time())
            sock.sendto(packet, (host, port))
            unacknowledged_packets += 1
        # Waiting for acknowledgements
        try:
            ack_packet, addr = sock.recvfrom(buffer_size)
            ack_packet_id, ack_file_id = int.from_bytes(ack_packet[:packet_id_size], byteorder="big"), \
                int.from_bytes(ack_packet[file_id_size:packet_id_size+file_id_size], byteorder="big")
            if ack_file_id == file_id:
                if ack_packet_id - cumulative_packet_id >= base_packet_id:
                    unacknowledged_packets -= ack_packet_id - cumulative_packet_id - base_packet_id + 1
                    if unacknowledged_packets < 0:
                        unacknowledged_packets = 0
                    base_packet_id = ack_packet_id - cumulative_packet_id + 1
                    if ack_packet_id < 10: # For priting purposes
                        print(f"Successfully received acknowledgement {ack_packet_id}", end = '\t')
                    else:
                        print(f"Successfully received acknowledgement {ack_packet_id}", end = '\t\t')
                    print("Number of unacknowledged packets", unacknowledged_packets, end = '\t')
                    cumulative_timeout = 0
                    isLost = False
                    dupACKcount = 0
                    cwnd = min(cwnd * 2, ssthresh) if cwnd < ssthresh else cwnd + 1 if cwnd < Max_cwnd else Max_cwnd
                    try:
                        sample_rtt = time.time() - timers[0]
                        timers.pop(0)
                    except IndexError:
                        print("\nTimers List is empty!")
                    estimated_rtt = (1 - ALPHA) * estimated_rtt + ALPHA * sample_rtt
                    dev_rtt = (1 - BETA) * dev_rtt + BETA * abs(sample_rtt - estimated_rtt)
                    timeout_interval = estimated_rtt + 4 * dev_rtt
                    sock.settimeout(timeout_interval)
                    print(f'Timeout interval {round(timeout_interval,4)} seconds')
                    plot_packet_id.append(ack_packet_id)
                    plot_time.append(time.time() - ref_time)
                else:
                    dupACKcount += 1
                    plot_packet_id.append(-ack_packet_id)
                    plot_time.append(time.time() - ref_time)
                    if dupACKcount == 3:
                        print("\033[44mFast retransmission occurs ...\033[0m")
                        isLost = True
                        ssthresh = max(cwnd//2,1)
                        cwnd = ssthresh
                        #dupACKcount = 0 # To allow more than one fast retransmission during the timeout
                        print(f"Retransmitting packets from {base_packet_id + cumulative_packet_id} to {base_packet_id + cumulative_packet_id + min(unacknowledged_packets, cwnd) - 1}")
                        for pkt_id in range(base_packet_id, base_packet_id + min(unacknowledged_packets, cwnd)):
                            packet_id = pkt_id + cumulative_packet_id
                            chunk = chunks[pkt_id]
                            # Converting list of bytes to bytes
                            chunk = bytes(itertools.chain.from_iterable(chunk))
                            # The following line handles the case when sender disconnects, and then reconnect again.
                            last_sent_packet_id = pkt_id
                            try:
                                packet = packet_id.to_bytes(packet_id_size, byteorder="big") + file_id.to_bytes(file_id_size, byteorder="big") + chunk + \
                                    ((0x0000).to_bytes(trailer_size, byteorder="big") if packet_id != len(chunks) - 1 else (0xFFFF).to_bytes(trailer_size, byteorder="big"))
                            except OverflowError:
                                print("\n\033[91mError: No more packets could be sent.\033[0m\U0001F614")
                                print("Exiting Sender ... \U0001F44B")
                                sys.exit()
                            print(f"cwnd = {cwnd}\tssthresh = {ssthresh}\tdupACKcount = {dupACKcount}", end = '\t\t')
                            print(f"Resending packet: {packet_id} ...")
                            num_of_retransmissions += 1
                            sock.sendto(packet, (host, port))
                            timers.clear()
                            timers.append(time.time())
                            retransmitted_bytes += len(packet)
                        unacknowledged_packets = min(unacknowledged_packets, cwnd) # It handles the case when unacknowledged_packets > cwnd
                    print(f"\033[91mError: Duplicate packet {ack_packet_id}, Note: duplicate packet is discarded\033[0m")
            elif ack_file_id > file_id:
                    file_id = ack_file_id
                    print("\033[91mError: Received duplicate file id packet. Note: this packet is discarded, and the file id is updated\033[0m")
                    cumulative_packet_id = read_cumulative_packet_id()
                    print(f"Cumulative Packet ID is retrieved from the save file, its value is: {cumulative_packet_id}")
                    isLost = True
                    break
            else:
                print(f"\033[91mError: Expected File ID is {file_id} but Received is {ack_file_id}\033[0m")
                print("Number of Retransmissions = ", num_of_retransmissions, end = '\t')
        except socket.timeout:
            isLost = True
            dupACKcount = 0
            ssthresh = max(cwnd//2,1)
            cwnd = 1
            # Resend unacknowledged packets
            cumulative_timeout += 1
            # Resetting Timeout Interval
            sock.settimeout(ack_timeout)
            if cumulative_timeout > max_timeout:
                print("Connection Timeout. Try to connect later")
                connection_timeout = True
                sys.exit()
            print("\n\033[91mTimeout\033[0m")
            print(f"Retransmitting packets from {base_packet_id + cumulative_packet_id} to {base_packet_id + cumulative_packet_id + min(unacknowledged_packets, cwnd) - 1}")
            for pkt_id in range(base_packet_id, base_packet_id + min(unacknowledged_packets, cwnd)):
                packet_id = pkt_id + cumulative_packet_id
                chunk = chunks[pkt_id]
                # Converting list of bytes to bytes
                chunk = bytes(itertools.chain.from_iterable(chunk))
                # The following line handles the case when sender disconnects, and then reconnect again.
                last_sent_packet_id = pkt_id
                try:
                    packet = packet_id.to_bytes(packet_id_size, byteorder="big") + file_id.to_bytes(file_id_size, byteorder="big") + chunk + \
                        ((0x0000).to_bytes(trailer_size, byteorder="big") if packet_id != len(chunks) - 1 else (0xFFFF).to_bytes(trailer_size, byteorder="big"))
                except OverflowError:
                    print("\n\033[91mError: No more packets could be sent.\033[0m\U0001F614")
                    print("Exiting Sender ... \U0001F44B")
                    sys.exit()
                print(f"cwnd = {cwnd}\tssthresh = {ssthresh}\tdupACKcount = {dupACKcount}", end = '\t\t')
                print(f"Resending packet: {packet_id} ...")
                num_of_retransmissions += 1
                sock.sendto(packet, (host, port))
                timers.clear()
                timers.append(time.time())
                retransmitted_bytes += len(packet)
            unacknowledged_packets = min(unacknowledged_packets, cwnd) # It handles the case when unacknowledged_packets > cwnd
        if pbar.total != 0:
            pbar.update(base_packet_id - pbar.n) # = I
            pbar.refresh()
            if base_packet_id < pbar.total/3:
                pbar.colour = "red"
            elif base_packet_id < (pbar.total*2)/3:
                pbar.colour = 'yellow'
            else:
                pbar.colour = 'green'
            pbar.set_postfix(progress=base_packet_id)
    if pbar.total != 0:
        pbar.update(pbar.total - pbar.n)
        pbar.colour = 'green'
    pbar.close()
    print("unacknowledged_packets",unacknowledged_packets)
    if not connection_timeout and isLost == False:
        prev_cumulative_packet_id = cumulative_packet_id
        cumulative_packet_id += base_packet_id
        save_cumulative_packet_id(cumulative_packet_id)
        if file_id % 2 == 0:
            file_id += 1
            print("cumulative_packet_id", cumulative_packet_id)
        else:
            cumulative_bytes_sent += bytes_sent
            cumulative_retransmissions += num_of_retransmissions
            print("File has been sent successfully \U0001f600")
            print(f'\033[42mNetwork Performance Metrics at the sender:\033[0m')
            print(f'Start Time:\033[92m {start_time}\033[0m')
            end_time = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y-%b-%d %I:%M:%S %p")
            print(f'End Time:\033[92m {end_time}\033[0m')
            elapsed_seconds = time.time() - start_time_seconds
            print(f"Elapsed Time:\033[92m {int(elapsed_seconds // 3600)} Hours, {int((elapsed_seconds % 3600) // 60)} Minutes, {round((elapsed_seconds % 3600) % 60,2)} Seconds\033[0m")
            print(f"Number of Packets sent for this file:\033[92m {base_packet_id + 1} Packets\033[0m")
            print(f"Total Number of Packets sent for all files:\033[92m {base_packet_id + prev_cumulative_packet_id} Packets\033[0m")
            print(f"Number of Bytes sent for this file \033[4mWITHOUT Header and Trailer\033[0m:\033[92m {bytes_sent:,} Bytes\033[0m")
            print(f"Number of Bytes sent for this file \033[4mWITH Header and Trailer\033[0m:\033[92m {bytes_sent + (base_packet_id + 1) * (packet_id_size + file_id_size + trailer_size):,} Bytes\033[0m")
            print(f"Total Number of Bytes sent for all files \033[4mWITHOUT Header and Trailer\033[0m:\033[92m {cumulative_bytes_sent:,} Bytes\033[0m")
            print(f"Total Number of Bytes sent for all files \033[4mWITH Header and Trailer\033[0m:\033[92m {cumulative_bytes_sent + (base_packet_id + prev_cumulative_packet_id) * (packet_id_size + file_id_size + trailer_size):,} Bytes\033[0m")
            print(f"Number of Retransmissions for this file: \033[92m{num_of_retransmissions:,}\033[0m")
            print(f"Total Number of Retransmissions for all files: \033[92m{cumulative_retransmissions:,}\033[0m")
            avg_loss_rate_packets_sec = num_of_retransmissions / elapsed_seconds
            avg_loss_rate_bytes_sec = retransmitted_bytes / elapsed_seconds
            # sending rate = loss rate + transfer rate
            avg_sending_rate_packets_sec = (num_of_retransmissions + base_packet_id + 1) / elapsed_seconds
            avg_sending_rate_bytes_sec = (retransmitted_bytes + bytes_sent + (base_packet_id + 1) * (packet_id_size + file_id_size + trailer_size)) / elapsed_seconds
            print(f"Average Sending Rate: \033[92m{round(avg_sending_rate_packets_sec,2):,} packets/sec\033[0m")
            print(f"Average Sending Rate: \033[92m{round(avg_sending_rate_bytes_sec,2):,} bytes/sec\033[0m")
            print(f"Average Loss Rate: \033[92m{round(avg_loss_rate_packets_sec,2):,} packets/sec\033[0m")
            print(f"Average Loss Rate: \033[92m{round(avg_loss_rate_bytes_sec,2):,} bytes/sec\033[0m")
            print(f"Average Transfer Rate: \033[92m{round(avg_sending_rate_packets_sec - avg_loss_rate_packets_sec,2):,} packets/sec\033[0m")
            print(f"Average Transfer Rate: \033[92m{round(avg_sending_rate_bytes_sec - avg_loss_rate_bytes_sec,2):,} bytes/sec\033[0m")
            print(f"Average Simulated Loss: \033[92m{round(num_of_retransmissions*100/(num_of_retransmissions + base_packet_id + 1),2)}%\033[0m")
            retransmitted_bytes = 0
            plot_pktID_vs_time(x_axis_data = plot_time,
                               y_axis_data = plot_packet_id,
                               isDynamicW = True,
                               step = 5,
                               num_of_retransmissions = num_of_retransmissions,
                               simulated_loss_rate = round(num_of_retransmissions*100/(num_of_retransmissions + base_packet_id + 1),1),
                               Transfer_Rate = round(avg_sending_rate_bytes_sec - avg_loss_rate_bytes_sec,1),
                               cwnd = cwnd,
                               timeout = timeout_interval
                               )
            print("Directory = ", directory)
            try:
                os.startfile(directory)
            except:
                print("\033[91mCould not open the `Plots History` Folder\033[0m")
            def waitingFunc():
                i = 0
                while (i < int(file_size/1e6) + int(file_size/1e6 > int(file_size/1e6))):
                    i += 1 # Assuming each 1MB is processed in 1 second
                    time.sleep(1)
            bar(function=waitingFunc, string="Waiting for the receiver to process the sent file", expectedDuration=(int(file_size/1e6) + int(file_size/1e6 > int(file_size/1e6))), args=None)
            # Ask user if he/she want to send another file, it yes > script will be restarted, else the sender will exit
            while True:
                print("\nDo you want to send another file? (Y/N) ", end="", flush=True)
                send_another_file, _, _ = select.select([sys.stdin], [], [], input_timeout)
                if send_another_file:
                # read the input from the user
                    user_choice = sys.stdin.readline().strip()
                    if user_choice.upper() == 'Y':
                        print("Enter the filename: ", end="", flush=True)
                        another_file_name, _, _ = select.select([sys.stdin], [], [], input_timeout)
                        if another_file_name:
                            file_name = sys.stdin.readline().strip()
                            print("The file you have chosen is:", file_name)
                            file_id += 1
                            break
                        else:
                            print("\n\033[91mNo input received within the timeout period.\033[0m")
                            print("\033[91mExiting Sender ... \033[0m\U0001F44B")
                            sys.exit()
                    elif user_choice.upper() == 'N':
                        print("Exiting Sender ... \U0001F44B")
                        sys.exit()
                    else:
                        print("\033[91mInvalid input. Please enter 'Y' or 'N'.\033[0m")
                else:
                # handle the case when no input is received within the timeout
                    print("\033[91mNo input received within the timeout period.\033[0m")
                    print("\033[91mExiting Sender ... \033[0m\U0001F44B")
                    sys.exit()