#!/bin/bash

# Specify the desired swap file size (e.g., 2GB)
SWAPFILE_SIZE="2G"

# Check if the swap file exists
if [ -f /swapfile ]; then
  # Check the current swap file size
  CURRENT_SIZE=$(ls -lh /swapfile | awk '{print $5}')
  
  # Check if the current size matches the desired size
  if [ "$CURRENT_SIZE" = "$SWAPFILE_SIZE" ]; then
    echo "Swap file already exists and is the desired size. No further action needed."
    exit 0
  else
    echo "Swap file exists but does not match the desired size. Re-creating it..."
    sudo swapoff /swapfile
    sudo rm /swapfile
  fi
fi

# Create a new swap file
sudo fallocate -l $SWAPFILE_SIZE /swapfile

# Set permissions on the swap file
sudo chmod 600 /swapfile

# Format the swap file
sudo mkswap /swapfile
sudo swapon /swapfile
