#!/bin/bash

# Check if the decryption key is provided
if [ -z "$DECRYPTION_KEY" ]; then
  echo "DECRYPTION_KEY is not set"
  exit 1
fi

# Decrypt the configuration file
openssl enc -aes-256-cbc -d -in /usr/src/app/mcimageprocessing/config/config.enc -out /usr/src/app/mcimageprocessing/config/config.yaml -k "$DECRYPTION_KEY"

# Check if decryption was successful
if [ $? -ne 0 ]; then
  echo "Decryption failed"
  exit 1
fi

# Execute the main command
exec "$@"

