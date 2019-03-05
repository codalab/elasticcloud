#!/usr/bin/env bash

echo "SUDO_USER =" $SUDO_USER

echo "Adding graphics drivers repo."
sudo add-apt-repository -y ppa:graphics-drivers/ppa
echo "apt update"
sudo apt -y update
echo "Installing nvidia drivers."
sudo apt-get -y install nvidia-384

echo "curl https://get.docker.com | sudo sh"
sudo -u $SUDO_USER curl https://get.docker.com | sudo sh
echo "Adding docker group."
sudo groupadd docker
echo "usermod -aG docker $SUDO_USER"
sudo usermod -aG docker $SUDO_USER
echo "newgrp docker"
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
sudo -u $SUDO_USER newgrp docker <<EOF
echo "docker run hello-world"
sudo -u $SUDO_USER docker run hello-world

echo "curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - distribution=$(. /etc/os-release;echo $ID$VERSION_ID)"
sudo -u $SUDO_USER curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | \
  sudo apt-key add -
echo "distribution = $distribution"
echo "curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list"
sudo -u $SUDO_USER curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
echo "apt-get -y update"
sudo apt-get -y update

echo "apt-get install -y nvidia-docker2"
sudo apt-get install -y nvidia-docker2
echo "pkill -SIGHUP dockerd"
sudo pkill -SIGHUP dockerd

echo "docker run --runtime=nvidia --rm nvidia/cuda:9.0-base nvidia-smi"
sudo -u $SUDO_USER docker run --runtime=nvidia --rm nvidia/cuda:9.0-base nvidia-smi
EOF

echo "END."
