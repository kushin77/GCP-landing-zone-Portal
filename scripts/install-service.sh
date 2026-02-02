#!/bin/bash
# Install GCP Landing Zone Portal as a permanent systemd service
# Run with: sudo bash install-service.sh

set -e

PORTAL_HOME="/home/akushnir/GCP-landing-zone-Portal"
SERVICE_FILE="$PORTAL_HOME/scripts/lz-portal.service"
SERVICE_NAME="lz-portal"

echo "🔧 Installing $SERVICE_NAME as a systemd service..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run with sudo"
   exit 1
fi

# Copy service file to systemd directory
echo "📝 Copying service file..."
cp "$SERVICE_FILE" "/etc/systemd/system/$SERVICE_NAME.service"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service to start on boot
echo "✅ Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME.service"

# Start the service
echo "🚀 Starting service..."
systemctl start "$SERVICE_NAME.service"

# Check status
sleep 2
echo ""
echo "📊 Service Status:"
systemctl status "$SERVICE_NAME.service" || true

echo ""
echo "✅ Installation complete!"
echo ""
echo "📌 Useful commands:"
echo "   Start:    sudo systemctl start $SERVICE_NAME"
echo "   Stop:     sudo systemctl stop $SERVICE_NAME"
echo "   Status:   sudo systemctl status $SERVICE_NAME"
echo "   Logs:     sudo journalctl -u $SERVICE_NAME -f"
echo "   Restart:  sudo systemctl restart $SERVICE_NAME"
echo ""
echo "🌐 Access the portal at:"
echo "   http://192.168.168.42:5173"
