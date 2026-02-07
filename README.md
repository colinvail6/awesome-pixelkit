<p align="center">
  <a href="https://awesome.re"><img src="https://awesome.re/badge.svg" alt="Awesome"></a>
</p>


# awesome-pixelkit
A repository with everything about the Kano Pixel Kit


## 🗂️ Contents
- [📌 Pinout](#pinout)
- [💾 Integrated Circuits](#integrated-circuits)
- [🐍 Programming Lanuages](#programming-languages)


# Pinout
- NeoPixel LEDs 💡 = GPIO4
- Buzzer 🔊 = GPIO22
- Dial/Potentiometer 🎛️ = GPIO36/VP
- MEMS microphone 🎙️ = GPIO39/VN
- Joystick up 🕹️ = GPIO35
- Joystick down 🕹️ = GPIO34
- Joystick left 🕹️ = GPIO26
- Joystick right 🕹️ = GPIO25
- Joystick click 🕹️ = GPIO27
- Button B 🎛️ = GPIO18
- Button A 🎛️ = GPIO23
- Reset Button 🎛️ = GPIO5


# Integrated Circuits
## FTDI FT231XS USB-to-UART converter
1. The FT231XS on the Pixel Kit is used to connect to its ESP-WROOM-32 microntroller
2. It is also used to make serial devices for the USB devies connected to the USB-A ports

## Terminus FE1.1S USB 2.0 port hub
1. Connects all the USB-A ports on the top of the Pixel Kit into one unified port
2. It routes its output into the FT231XS


# Programming Languages
## MicroPython
The Pixel Kit can run MicroPython using [Pixel32](https://github.com/murilopolese/kano-pixel-kit-pixel32), a library that allows you to code your Pixel Kit using a browser
## CircuitPython
The Pixel Kit can run CircuitPython using [this installation](https://circuitpython.org/board/doit_esp32_devkit_v1/) and [my helper libraries](https://github.com/colinvail6/awesome-pixelkit/tree/main/src/circuitpython)
## Arduino
Install the ESP32 boards package and select "ESP32 Dev Module", then set "Flash Mode" to DIO. I am currently working on a helper library for Arduino and the Pixel Kit
