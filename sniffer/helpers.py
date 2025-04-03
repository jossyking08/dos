# # Helper function to get the protocol value based on the protocol name
import httpx
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

async def send_email(recipient_email, subject, body):
    # Create the email
    msg = MIMEMultipart()
    msg['From'] = "alert@medfestcareng.com"
    msg['To'] = recipient_email
    msg['Subject'] = subject

    # Attach the email body
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the Yahoo SMTP server
        with smtplib.SMTP('mail.medfestcareng.com', 587) as server:
            server.starttls()  # Upgrade the connection to secure
            server.login("alert@medfestcareng.com", "u7O2ECBB2n}F")
            server.send_message(msg)
            print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")



async def Intrusion_Detector(packet_data, user_data):
    url = "http://127.0.0.1:3003/predict/is_attack"
    # Prepare the payload with packet and user data
    payload = {
        "src_port": int(packet_data.get("src_port", 0)),
        "dst_port": int(packet_data.get("dst_port", 0)),
        "proto": int(packet_data.get("proto", 0)),
        "duration": int(packet_data.get("duration", 0)),
        "src_bytes": int(packet_data.get("src_bytes", 0)),
        "dst_bytes": int(packet_data.get("dst_bytes", 0)),
        "conn_state": int(packet_data.get("conn_state", 0)) if packet_data.get("conn_state") is not None else 0,
        "src_pkts": int(packet_data.get("src_pkts", 0)),
        "src_ip_bytes": int(packet_data.get("src_ip_bytes", 0)),
        "dst_pkts": int(packet_data.get("dst_pkts", 0)),
        "dst_ip_bytes": int(packet_data.get("dst_ip_bytes", 0)),
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)

        # Check if the response was successful
        if response.status_code == 200:
            return response.json()  # or response.text, depending on your needs
    except Exception as err:
        print(err)
        return {'isAttack': ''}
        


def get_protocol_value(proto_name):
    protocols = [
        { "label": "TCP", "value": 6 },
        { "label": "UDP", "value": 17 },
        { "label": "IGMP", "value": 2 },
        { "label": "ICMP", "value": 1 },
        { "label": "ICMPv6", "value": 58 },
    ]
    for proto in protocols:
        if proto["label"] == proto_name:
            return proto["value"]
    return 0  # Return None if the protocol is not found

# Helper function to get the connection state value based on flags
def get_conn_state_value(tcp_flags):
    conn_states = [
        { "label": "OTH", "value": 0 },
        { "label": "REJ", "value": 1 },
        { "label": "RSTO", "value": 2 },
        { "label": "RSTOS0", "value": 3 },
        { "label": "RSTR", "value": 4 },
        { "label": "RSTRH", "value": 5 },
        { "label": "S0", "value": 6 },
        { "label": "S1", "value": 7 },
        { "label": "S2", "value": 8 },
        { "label": "S3", "value": 9 },
        { "label": "SF", "value": 10 },
        { "label": "SH", "value": 11 },
        { "label": "SHR", "value": 12 },
    ]
    
    # Simplified example based on flags for TCP
    if tcp_flags.S and not tcp_flags.A:  # SYN flag set but not ACK
        return 6  # "S0" state
    elif tcp_flags.S and tcp_flags.A:    # SYN and ACK both set
        return 7  # "S1" state
    elif tcp_flags.R and not tcp_flags.A:  # Reset without ACK
        return 1  # "REJ" state
    elif tcp_flags.F and tcp_flags.A:    # Finish flag with ACK
        return 10  # "SF" state
    else:
        return 0  # Default to "OTH"