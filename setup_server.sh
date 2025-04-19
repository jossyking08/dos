#!/bin/bash

# Exit on error
set -e

echo "Setting up environment for Django application with network analysis tools..."

# Avoid prompts from apt
export DEBIAN_FRONTEND=noninteractive

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    software-properties-common \
    libpcap-dev \
    wireshark \
    tshark \
    tcpdump \
    git \
    wget \
    curl \
    sudo

# Add deadsnakes PPA and install Python 3.11
echo "Installing Python 3.11..."
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-dev python3.11-distutils

# Install pip for Python 3.11
echo "Installing pip..."
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python3.11 get-pip.py
rm get-pip.py

# Create symbolic links (optional, use with caution)
# sudo ln -sf /usr/bin/python3.11 /usr/bin/python3
# sudo ln -sf /usr/bin/python3.11 /usr/bin/python

# Create wireshark group if it doesn't exist
echo "Setting up wireshark group..."
sudo groupadd -f wireshark
sudo usermod -aG wireshark $USER

# Allow non-root capture with tcpdump
echo "Setting capabilities for tcpdump..."
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump

# Create test12 superadmin user if needed
echo "Setting up superadmin user..."
if ! id -u test12 &>/dev/null; then
    sudo useradd -m -s /bin/bash test12
    echo "test12:test@123456" | sudo chpasswd
    echo "test12 ALL=(ALL) ALL" | sudo tee -a /etc/sudoers
fi

# Create project directory if it doesn't exist
echo "Setting up project directory..."
mkdir -p ~/django_app
cd ~/django_app

# Copy your requirements.txt here or create it
# touch requirements.txt  # Uncomment and modify as needed

# Install Python dependencies
echo "Installing Python dependencies..."
if [ -f requirements.txt ]; then
    python3.11 -m pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Please create it and install dependencies manually."
fi

# Create startup script
echo "Creating startup script..."
cat > ~/django_app/startup.sh << 'EOF'
#!/bin/bash

# Run database migrations first
echo "Running database migrations..."
python3.11 manage.py makemigrations
python3.11 manage.py migrate

# Create superuser
echo "Creating superuser..."
python3.11 manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser(\"test12\", \"admin@example.com\", \"test@123456\") if not User.objects.filter(username=\"test12\").exists() else None"

# Start the server
echo "Starting server..."
python3.11 manage.py runserver 0.0.0.0:8000
EOF

chmod +x ~/django_app/startup.sh

echo "Setup complete!"
echo "Copy your Django project files to ~/django_app/ and run ./startup.sh to start the application."
echo "To run packet sniffing tools, you may need to use sudo or log out and log back in for group changes to take effect."
