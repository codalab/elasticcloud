#!/bin/bash -x

USER_NAME=your_username

sudo add-apt-repository -y ppa:graphics-drivers/ppa
sudo apt -y update
sudo apt-get -y install nvidia-384

sudo -u $USER_NAME curl https://get.docker.com | sudo sh
sudo groupadd docker
sudo usermod -aG docker $USER_NAME
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
sudo -u $USER_NAME newgrp docker <<EOF

sudo -u $USER_NAME curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | \
  sudo apt-key add -
sudo -u $USER_NAME curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get -y update

sudo apt-get install -y nvidia-docker2
sudo pkill -SIGHUP dockerd

sudo -u $USER_NAME docker run --runtime=nvidia --rm nvidia/cuda:9.0-base nvidia-smi
EOF

