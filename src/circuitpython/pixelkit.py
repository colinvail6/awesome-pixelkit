import board
import analogio, digitalio, pwmio
import colorsys
import neopixel
from scroll_letters import letters
from scroll_numbers import numbers
from scroll_symbols import symbols
from time import sleep

# Hardware info
# In CircuitPython, ESP32 pins are labeled with a D,
# unlike other languages that reference the GPIO number.
pixel_pin = board.D4
WIDTH = 16
HEIGHT = 8
dial_pin = board.VP # In CircuitPython, GPIO 36 is board.VP
microphone_pin = board.VN # In CircuitPython, GPIO 39 is board.VN
joystick_up_pin = board.D35
joystick_down_pin = board.D34
joystick_left_pin = board.D26
joystick_right_pin = board.D25
joystick_click_pin = board.D27
button_b_pin = board.D18
button_a_pin = board.D23
button_reset_pin = board.D5
buzzer_pin = board.D22

# Hardware Instances
# Objects representing the available hardware on the Pixel Kit
# Keep in mind that the Pixel Kit's matrix is NOT serpentine, meaning alternating CANNOT be true unless you are using a custom board
np = neopixel.NeoPixel(pixel_pin, WIDTH * HEIGHT, brightness=0.05, auto_write=False)
# Directions of digital pins must be set with var.direction = digitalio.Direction.INPUT or OUTPUT
joystick_up = digitalio.DigitalInOut(joystick_up_pin)
joystick_up.direction = digitalio.Direction.INPUT
joystick_down = digitalio.DigitalInOut(joystick_down_pin)
joystick_down.direction = digitalio.Direction.INPUT
joystick_left = digitalio.DigitalInOut(joystick_left_pin)
joystick_left.direction = digitalio.Direction.INPUT
joystick_right = digitalio.DigitalInOut(joystick_right_pin)
joystick_right.direction = digitalio.Direction.INPUT
joystick_click = digitalio.DigitalInOut(joystick_click_pin)
joystick_click.direction = digitalio.Direction.INPUT
button_a = digitalio.DigitalInOut(button_a_pin)
button_a.direction = digitalio.Direction.INPUT
button_b = digitalio.DigitalInOut(button_b_pin)
button_b.direction = digitalio.Direction.INPUT
button_reset = digitalio.DigitalInOut(button_reset_pin)
button_reset.direction = digitalio.Direction.INPUT

dial = analogio.AnalogIn(dial_pin)

microphone = analogio.AnalogIn(microphone_pin)

buzzer = pwmio.PWMOut(buzzer_pin, duty_cycle=0, frequency=400, variable_frequency=True)

# Hardware Values
# Values based on available hardware
dial_value = dial.value
microphone_value = microphone.value
is_pressing_up = False
is_pressing_down = False
is_pressing_left = False
is_pressing_right = False
is_pressing_click = False
is_pressing_a = False
is_pressing_b = False
is_pressing_reset = False

# Scrolling text variables
charset = {}
charset.update(letters)
charset.update(numbers)
charset.update(symbols)

# Control-related functions
# This helps interrupt the Pixel Kit during a running program
def interrupt():
    clear()
    render()
    print("Returing to REPL...")
    raise KeyboardInterrupt

# Group all other function together to check hardware
def check_controls():
    check_joystick()
    check_buttons()
    check_dial()
    check_microphone()

def check_joystick():
    global is_pressing_up
    global is_pressing_down
    global is_pressing_left
    global is_pressing_right
    global is_pressing_click
    if joystick_up.value == 0 and not is_pressing_up:
        is_pressing_up = True
        on_joystick_up()
    if joystick_up.value != 0 and is_pressing_up:
        is_pressing_up = False

    if joystick_down.value == 0 and not is_pressing_down:
        is_pressing_down = True
        on_joystick_down()
    if joystick_down.value != 0 and is_pressing_down:
        is_pressing_down = False

    if joystick_left.value == 0 and not is_pressing_left:
        is_pressing_left = True
        on_joystick_left()
    if joystick_left.value != 0 and is_pressing_left:
        is_pressing_left = False

    if joystick_right.value == 0 and not is_pressing_right:
        is_pressing_right = True
        on_joystick_right()
    if joystick_right.value != 0 and is_pressing_right:
        is_pressing_right = False

    if joystick_click.value == 0 and not is_pressing_click:
        is_pressing_click = True
        on_joystick_click()
    if joystick_click.value != 0 and is_pressing_click:
        is_pressing_click = False

# Checks the buttons, "debounce" the presses and calls the
# function related to which button was pressed
def check_buttons():
    global is_pressing_a
    global is_pressing_b
    global is_pressing_reset
    if button_a.value == 0 and not is_pressing_a:
        is_pressing_a = True
        on_button_a()
    if button_a.value != 0 and is_pressing_a:
        is_pressing_a = False
    if button_b.value == 0 and not is_pressing_b:
        is_pressing_b = True
        on_button_b()
    if button_b.value != 0 and is_pressing_b:
        is_pressing_b = False
    if button_reset.value == 0 and not is_pressing_reset:
        is_pressing_reset = True
        on_button_reset()
    if button_reset.value != 0 and is_pressing_reset:
        is_pressing_reset = False

# Checks the dial value and only set the hardware value and call the
# function related with the dial if the new value is different from the previous
def check_dial():
    global dial_value
    newValue = dial.value
    if newValue != dial_value:
        dial_value = dial.value
        on_dial(dial_value)

# Checks the microphone value and only set the hardware value and call the
# function related with the microphone if the new value is different from the previous
def check_microphone():
    global microphone_value
    newValue = microphone.value
    if newValue != microphone_value:
        microphone_value = microphone.value
        on_microphone(microphone_value)

# Called when those hardware change values
def on_joystick_up():
    return False
def on_joystick_down():
    return False
def on_joystick_left():
    return False
def on_joystick_right():
    return False
def on_joystick_click():
    return False
def on_button_a():
    return False
def on_button_b():
    return False
def on_button_reset():
    return False
def on_dial(dial_value):
    return False
def on_microphone(microphone_value):
    return False

# Buzzer functions
# The Pixel Kit has a buzzer, but it is very hard to hear
def beep(frequency, duration):
    buzzer.frequency = frequency
    buzzer.duty_cycle = 2 ** 15
    sleep(duration)
    buzzer.duty_cycle = 0

# LED functions
def get_index_from_coordinate(x, y):
    return ((y) * WIDTH) + (x)

def set_pixel(x, y, color=[0, 10, 0]):
    index = get_index_from_coordinate(x, y)
    np[index] = color
    
def set_pixel_hsv(x, y, hsv=(0, 1, 1)):
    # Set a pixel using HSV values.
    # hsv: tuple (hue 0-360, saturation 0-1, value 0-1)
    rgb = hsv_to_rgb(*hsv)
    set_pixel(x, y, rgb)

def set_background(rgb=(255, 255, 0)):
    np.fill(rgb)

def set_brightness(brightness=0.05): # Any number from 0 to 1
    np.brightness = brightness

def clear():
    set_background((0,0,0))

def draw_letter(x, y, l, c=[255, 255, 255]):
  if not str(l) in charset.keys():
    pass
  for ly, line in enumerate(charset[l]):
    for lx, value in enumerate(line):
      if value != 0:
        kit.set_pixel(x+lx, y+ly, c)

def buff_phrase(phrase='', offset=0, c=[255, 255, 255]):
  buff = [[0]*16, [0]*16, [0]*16,
          [0]*16, [0]*16]
  for l in phrase:
    if str(l) in charset.keys():
      for ly, line in enumerate(charset[l]):
        for value in line:
          buff[ly].append(value)
        buff[ly].append(0)
  return buff

def draw_buff(buff, o=0, c=[255, 255, 255]):
  for x in range(0, 16):
    for y in range(0, 5):
      try:
        if buff[y][o+x] != 0:
          set_pixel(x, 1+y, c)
      except Exception as e:
        pass

def scroll(p, color=[255, 255, 255], background=[0,0,0], interval=0.1):
  buff = buff_phrase(p)
  for i in range(0, len(buff[0])):
    set_background(background)
    draw_buff(buff, i, color)
    render()
    sleep(interval)

def render():
    np.write()
