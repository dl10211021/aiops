#!/bin/bash
# install_linux.sh
# Automated Prometheus Installation Script for Linux

set -e

# Configuration
PROMETHEUS_VERSION="2.45.0"
PROMETHEUS_USER="prometheus"
PROMETHEUS_GROUP="prometheus"
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/prometheus"
DATA_DIR="/var/lib/prometheus"

echo "Installing Prometheus v$PROMETHEUS_VERSION..."

# Download and Extract
cd /tmp
wget https://github.com/prometheus/prometheus/releases/download/v$PROMETHEUS_VERSION/prometheus-$PROMETHEUS_VERSION.linux-amd64.tar.gz
tar xvf prometheus-$PROMETHEUS_VERSION.linux-amd64.tar.gz

# Create User
sudo useradd --no-create-home --shell /bin/false $PROMETHEUS_USER

# Create Directories
sudo mkdir -p $CONFIG_DIR
sudo mkdir -p $DATA_DIR
sudo chown $PROMETHEUS_USER:$PROMETHEUS_GROUP $CONFIG_DIR $DATA_DIR

# Install Binaries
cd prometheus-$PROMETHEUS_VERSION.linux-amd64
sudo cp prometheus $INSTALL_DIR/
sudo cp promtool $INSTALL_DIR/
sudo chown $PROMETHEUS_USER:$PROMETHEUS_GROUP $INSTALL_DIR/prometheus $INSTALL_DIR/promtool

# Install Configuration
sudo cp -r consoles $CONFIG_DIR
sudo cp -r console_libraries $CONFIG_DIR
sudo cp prometheus.yml $CONFIG_DIR
sudo chown -R $PROMETHEUS_USER:$PROMETHEUS_GROUP $CONFIG_DIR/consoles $CONFIG_DIR/console_libraries $CONFIG_DIR/prometheus.yml

# Create Systemd Service
cat <<EOF | sudo tee /etc/systemd/system/prometheus.service
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=$PROMETHEUS_USER
Group=$PROMETHEUS_GROUP
Type=simple
ExecStart=$INSTALL_DIR/prometheus 
    --config.file $CONFIG_DIR/prometheus.yml 
    --storage.tsdb.path $DATA_DIR/ 
    --web.console.templates=$CONFIG_DIR/consoles 
    --web.console.libraries=$CONFIG_DIR/console_libraries

[Install]
WantedBy=multi-user.target
EOF

# Reload and Start Service
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus

echo "Prometheus installed and started successfully!"
