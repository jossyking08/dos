# Dockerfile for Django application with network analysis tools
FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies and clean up in the same layer
RUN apt-get update && apt-get install -y \
    software-properties-common \
    libpcap-dev \
    wireshark \
    tshark \
    tcpdump \
    git \
    wget \
    curl \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python 3.11 from deadsnakes PPA and clean up in the same layer
RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.11 python3.11-dev python3.11-distutils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.11 get-pip.py && \
    rm get-pip.py && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.11 /usr/bin/python

# Create groups and users
RUN groupadd -f wireshark && \
    useradd -m -s /bin/bash appuser && \
    usermod -aG wireshark appuser && \
    echo "appuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    useradd -m -s /bin/bash test12 && \
    echo "test12:test@123456" | chpasswd && \
    echo "test12 ALL=(ALL) ALL" >> /etc/sudoers

# Allow non-root capture with tcpdump
RUN setcap cap_net_raw,cap_net_admin=eip /usr/bin/tcpdump

# Set up working directory
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with cleanup in same layer
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 cache purge && \
    rm -rf ~/.cache/pip

# Copy project files
COPY . .

# Create startup script and set permissions
RUN echo '#!/bin/bash\n\
# Run database migrations first\n\
echo "Running database migrations..."\n\
python3 manage.py makemigrations\n\
python3 manage.py migrate\n\
\n\
# Create superuser\n\
echo "Creating superuser..."\n\
python3 manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser(\"test12\", \"admin@example.com\", \"test@123456\") if not User.objects.filter(username=\"test12\").exists() else None"\n\
\n\
# Start the server\n\
echo "Starting server..."\n\
python3 manage.py runserver 0.0.0.0:8000\n\
' > /app/startup.sh && \
    chmod +x /app/startup.sh && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the Django port
EXPOSE 8000

# Command to run the application
CMD ["/app/startup.sh"]
