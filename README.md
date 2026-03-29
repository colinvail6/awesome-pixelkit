<p align="center">
  <a href="https://awesome.re"><img src="https://awesome.re/badge.svg" alt="Awesome"></a>
</p>


# awesome-pixelkit - Kickstarter Pixel Kit
A branch of this repository that's all about the Kickstarter Kano Pixel Kit


## 🗂️ Contents
- [💾 Integrated Circuits](#integrated-circuits)
- [🐍 Programming Lanuages](#programming-languages)
- [🐧 Linux](#linux)


# Integrated Circuits
## Allwinner R40
1. Runs the helper that connects to Kano Code
2. Runs Linux
3. Contains an OpenGL ES 2.0 and 1.1 running Mali400 MP2 GPU
## AXP221S PMU
1. Manages power to all the compnents
## Ampak AP6212
1. Handles Wi-Fi 802.11 b/g/n (2.4GHz) & Bluetooth (4.0) on the Pixel Kit
## Samsung MCU (I don't know the model)
1. Handles the NeoPixel matrix, buttons, joystick, buzzer, and dial

# Programming Languages
## Python
The Pixel Kit can run Python using its built-in CPython installation.
## NodeJS
The Pixel Kit runs a NodeJS express app by default but can be changed to run other scripts by disabling the kano2-server-lightboard service and enabling a service that runs your script.


# Linux
## What Types?
### Armbian
The Pixel Kit can run both Armbian Debian (just the terminal) and Armbian Ubuntu (terminal & desktop).
## Upgrading
Upgrading the Pixel Kit is easy, it takes about an hour to set up.
First, install Armbian by downloading the Armbian imager to your Linux machine (Windows does not work):
1. Choose Banana Pi in the manufacturer options
2. Select Banana Pi M2 Ultra as the board (the Pixel Kit is a clone of it)
3. Select Debian as the operating system since the Pixel Kit does not have a screen
4. Select your storage device (it with be /dev/sd*)
5. Flash the image. If it warms you about the image being from the community, continue.


Next, configure WiFi for SSH:
1. Run `sudo nano /media/username/armbi_root/etc/systemd/network/10-wifi.network` and then type:
   ```ini
   [Match]
   Name=wlan0

   [Network]
   DHCP=yes

2. Run `sudo nano /media/username/armbi_root/etc/wpa_supplicant/wpa_supplicant-wlan0.conf` and then type:
   ```ini
   ctrl_interface=/run/wpa_supplicant
   update_config=1

   network={
       ssid="YOUR_WIFI_NAME"
       psk="YOUR_WIFI_PASSWORD"
   }
Replace username with your Linux username for your machine and replace YOUR_WIFIF_NAME and YOUR_WIFI_PASSWORD with your actual WiFi and password
3. Put the SD card into the Pixel Kit and turn it on, if you see rainbow, then it worked!
The rainbow means that the MCU is waiting for the Pixel Kit to tell the matrix to fade out
4. SSH into root@bananapim2ultra.local using an SSH app (PuTTY for Windows, Termius for all OSes, and Prompt 3 for iOS) and the root password you chose when creating your Armbian install.

Then, modify the device tree to detect the battery
