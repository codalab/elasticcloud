#!/bin/bash -x

echo "SUDO_USER =" $SUDO_USER
sleep 3.0
sudo -u bailey curl https://get.docker.com | sudo sh
sleep 3.0
sudo groupadd docker
sudo usermod -aG docker bailey
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
sudo -u bailey newgrp docker <<EOF

sudo -u bailey docker run -d -P --name web nginx
sudo -u bailey docker ps
EOF

