import threading
import time
from collections import defaultdict
from scapy.all import sniff, IP, TCP, UDP
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import load_model
from .helpers import send_email
import joblib
import logging
import asyncio
from ecom.models import BannedIP


# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')




# Load the trained LSTM model and scaler
MODEL_PATH = './model/model.h5'
SCALER_PATH = './model/scaler.pkl'
try:
    model = load_model(MODEL_PATH, compile=False)
    logging.info("Model loaded successfully")
except TypeError as e:
    logging.warning(f"Error loading model: {e}. Attempting workaround...")
    from tensorflow.keras.layers import Input
    model = load_model(
        MODEL_PATH,
        custom_objects={
            'InputLayer': lambda **kwargs: Input(
                **{k: v for k, v in kwargs.items() if k != 'batch_shape'}
            )
        },
        compile=False
    )

scaler = joblib.load(SCALER_PATH)
logging.info("Scaler loaded successfully")

# Global variables
flows = defaultdict(list)
flow_sequences = defaultdict(list)
monitored_ips = set()

# Features (33 features, excluding Label, assuming this matches your retrained model and scaler)
FEATURES = [
    ' Source IP', ' Source Port', ' Destination IP', ' Destination Port', ' Protocol',
    'Total Length of Fwd Packets', ' Fwd Packet Length Min', ' Bwd Packet Length Min',
    ' Flow IAT Min', 'Bwd IAT Total', ' Bwd IAT Mean', ' Bwd Header Length', 'Fwd Packets/s',
    ' Bwd Packets/s', ' Min Packet Length', ' Packet Length Mean', 'FIN Flag Count',
    ' SYN Flag Count', ' PSH Flag Count', ' ACK Flag Count', ' URG Flag Count',
    ' ECE Flag Count', ' Down/Up Ratio', ' Avg Fwd Segment Size', ' Avg Bwd Segment Size',
    'Init_Win_bytes_forward', ' Init_Win_bytes_backward', ' act_data_pkt_fwd',
    ' min_seg_size_forward', ' Active Std', ' Active Min', ' Idle Std', ' Idle Min'
]
FEATURE_NAMES = FEATURES  # 33 features

def compute_features(flow_packets, flow_key):
    """Compute LSTM features for a flow based on packet list."""
    stats = {f: 0 for f in FEATURES}  # Initialize all features to 0
    stats.update({
        ' Source IP': flow_key[0],
        ' Source Port': flow_key[1],
        ' Destination IP': flow_key[2],
        ' Destination Port': flow_key[3]
    })

    try:
        fwd_packets = [p for p in flow_packets if p['IP'].src == flow_key[0]]
        bwd_packets = [p for p in flow_packets if p['IP'].dst == flow_key[0]]

        if flow_packets:
            stats[' Protocol'] = flow_packets[0]['IP'].proto

        fwd_lengths = [len(p) for p in fwd_packets] if fwd_packets else [0]
        bwd_lengths = [len(p) for p in bwd_packets] if bwd_packets else [0]
        stats['Total Length of Fwd Packets'] = sum(fwd_lengths)
        stats[' Fwd Packet Length Min'] = min(fwd_lengths) if fwd_lengths else 0
        stats[' Bwd Packet Length Min'] = min(bwd_lengths) if bwd_lengths else 0
        stats[' Min Packet Length'] = min(fwd_lengths + bwd_lengths) if fwd_lengths + bwd_lengths else 0
        stats[' Packet Length Mean'] = np.mean(fwd_lengths + bwd_lengths) if fwd_lengths + bwd_lengths else 0

        timestamps = [p.time for p in flow_packets]
        iat = np.diff(timestamps) if len(timestamps) > 1 else np.array([])
        bwd_timestamps = [p.time for p in bwd_packets]
        bwd_iat = np.diff(bwd_timestamps) if len(bwd_timestamps) > 1 else np.array([])
        stats[' Flow IAT Min'] = min(iat) if iat.size > 0 else 0
        stats['Bwd IAT Total'] = sum(bwd_iat) if bwd_iat.size > 0 else 0
        stats[' Bwd IAT Mean'] = np.mean(bwd_iat) if bwd_iat.size > 0 else 0

        duration = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 1e-6
        if duration <= 0:
            duration = 1e-6
        stats['Fwd Packets/s'] = len(fwd_packets) / duration
        stats[' Bwd Packets/s'] = len(bwd_packets) / duration

        stats[' Bwd Header Length'] = sum(40 if 'TCP' in p else 28 for p in bwd_packets)
        stats[' min_seg_size_forward'] = min([20] * len(fwd_packets)) if fwd_packets else 20

        tcp_flags = [p['TCP'].flags if 'TCP' in p else 0 for p in flow_packets]
        stats['FIN Flag Count'] = sum(1 for f in tcp_flags if f & 0x01)
        stats[' SYN Flag Count'] = sum(1 for f in tcp_flags if f & 0x02)
        stats[' PSH Flag Count'] = sum(1 for f in tcp_flags if f & 0x08)
        stats[' ACK Flag Count'] = sum(1 for f in tcp_flags if f & 0x10)
        stats[' URG Flag Count'] = sum(1 for f in tcp_flags if f & 0x20)
        stats[' ECE Flag Count'] = sum(1 for f in tcp_flags if f & 0x40)

        stats[' Down/Up Ratio'] = len(bwd_packets) / len(fwd_packets) if fwd_packets else 0
        stats[' Avg Fwd Segment Size'] = np.mean(fwd_lengths) if fwd_lengths else 0
        stats[' Avg Bwd Segment Size'] = np.mean(bwd_lengths) if bwd_lengths else 0
        stats[' act_data_pkt_fwd'] = sum(1 for p in fwd_packets if len(p) > 40)

        stats['Init_Win_bytes_forward'] = fwd_packets[0]['TCP'].window if fwd_packets and 'TCP' in fwd_packets[0] else 0
        stats[' Init_Win_bytes_backward'] = bwd_packets[0]['TCP'].window if bwd_packets and 'TCP' in bwd_packets[0] else 0

        active_periods = [duration] if duration > 1e-6 else [0]
        idle_periods = [0 if len(iat) == 0 else max(0, duration - sum(iat))]
        stats[' Active Std'] = np.std(active_periods) if active_periods else 0
        stats[' Active Min'] = min(active_periods) if active_periods else 0
        stats[' Idle Std'] = np.std(idle_periods) if idle_periods else 0
        stats[' Idle Min'] = min(idle_periods) if idle_periods else 0

    except Exception as e:
        logging.error(f"Error in compute_features for flow {flow_key}: {str(e)}")

    return stats

def packet_callback(packet):
    try:
        if IP not in packet:
            # logging.info("Packet does not have an IP layer")
            return

        flow_key = (
            packet[IP].src,
            packet[TCP].sport if TCP in packet else packet[UDP].sport if UDP in packet else 0,
            packet[IP].dst,
            packet[TCP].dport if TCP in packet else packet[UDP].dport if UDP in packet else 0
        )

        flows[flow_key].append(packet)
        

        stats = compute_features(flows[flow_key], flow_key)

        # Convert IPs to numerical representation
        def ip_to_int(ip):
            parts = ip.split('.')
            return int(parts[0]) * 256**3 + int(parts[1]) * 256**2 + int(parts[2]) * 256 + int(parts[3])
        
        stats[' Source IP'] = ip_to_int(stats[' Source IP'])
        stats[' Destination IP'] = ip_to_int(stats[' Destination IP'])

        feature_vector = [stats[f] for f in FEATURE_NAMES]
        flow_sequences[flow_key].append(feature_vector)

        if len(flow_sequences[flow_key]) >= 10:
            sequence = np.array(flow_sequences[flow_key][-10:])
            if sequence.shape[1] != len(FEATURE_NAMES):
                logging.error(f"Feature mismatch: Expected {len(FEATURE_NAMES)}, got {sequence.shape[1]}")
                return

            sequence_df = pd.DataFrame(sequence, columns=FEATURE_NAMES)
            sequence_scaled = scaler.transform(sequence_df).reshape(1, 10, len(FEATURE_NAMES))

            prediction = model.predict(sequence_scaled, verbose=0)
            binary_pred = (prediction > 0.5).astype(int)[0][0]
            probability = float(prediction[0][0])

            result = f"Flow {flow_key}: {'DDoS' if binary_pred else 'Benign'} (Probability: {probability:.4f})"
            # print(result)
            # logging.info(result)

            if binary_pred and packet[IP].src not in monitored_ips:
                logging.warning(f"Potential DDoS from {flow_key[0]}. Consider banning.")
                BannedIP.objects.get_or_create(ip_address={flow_key[0]}, defaults={'reason': 'Volumetric DDos Attack Detected'})
                subject = 'Potential VOLUMETRIC DDOS ATTACK PATTERN DETECTED'
                body = 'We have detected a volumetric ddos attack on ip address {}, ip address has being banned'.format(flow_key[0])
                asyncio.run(send_email(recipient_email="Jossyking17@gmail.com",subject=subject, body=body))
                monitored_ips.add(packet[IP].src)

            flow_sequences[flow_key] = flow_sequences[flow_key][-9:]

    except Exception as e:
        logging.error(f"Error in packet_callback for packet: {str(e)}")

def start_sniffer():
    print("Sniffer started! Listening for packets...")
    try:
        sniff(iface='ens5', prn=packet_callback, store=0)
    except Exception as e:
        logging.error(f"Error in sniffer: {str(e)}")
        time.sleep(1)
        start_sniffer()

def run_sniffer_in_thread():
    thread = threading.Thread(target=start_sniffer, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    sniffer_thread = run_sniffer_in_thread()
    print("Sniffer thread started. Running in background...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping sniffer...")