'''
pixelkit.py - Linux Pixel Kit library that is backwards-compatible with the CircuitPython version
for the Kano Pixel Kit running on BananaPi R40 / Armbian.

Usage:
    import pixelkit as kit
    kit.connect()
    kit.set_background((255, 0, 0))
    kit.render()

Key differences from CircuitPython:
  - connect() must be called before anything else
  - connect(microphone=True) to enable mic input
  - beep() is non-blocking
  - render() blocks until the previous frame is sent
  - dial returns 0-4 mapped from mode name strings
  - on_microphone(value) fires when mic level changes (0-255)
  - on_beat() fires when a beat/clap is detected
  - start_microphone() / stop_microphone() for manual mic control
'''

import base64
import struct
import threading
import time
from rpcclient import SerialChannel, RPCClient, EventStream

# --- Constants ----------------------------------------------------------------

WIDTH  = 16
HEIGHT = 8
_NPIX  = WIDTH * HEIGHT

_MODE_MAP = {
    'offline-1': 0,
    'offline-2': 1,
    'online-p1': 2,
    'online-p2': 3,
    'online-p3': 4,
}

_PORT_DEFAULT = '/dev/ttyS2'

# --- Internal state -----------------------------------------------------------

_channel        = None
_client         = None
_events         = None
_pixels         = [(0, 0, 0)] * _NPIX
_render_event   = threading.Event()
_render_event.set()
_render_pending = False

# Public sensor state
dial_value       = 0
microphone_value = 0

is_pressing_up    = False
is_pressing_down  = False
is_pressing_left  = False
is_pressing_right = False
is_pressing_click = False
is_pressing_a     = False
is_pressing_b     = False
is_pressing_reset = False

_pending_events = []
_events_lock    = threading.Lock()

# Cached module reference for _fire()
_self_module = None

# --- Callbacks ----------------------------------------------------------------

on_joystick_up    = None
on_joystick_down  = None
on_joystick_left  = None
on_joystick_right = None
on_joystick_click = None
on_button_a       = None
on_button_b       = None
on_button_reset   = None
on_dial           = None
on_microphone     = None
on_beat           = None

# --- connect ------------------------------------------------------------------

def connect(port=_PORT_DEFAULT, connect_timeout=10.0, microphone=False,
            mic_device=None, mic_threshold=5):
    '''
    Open serial connection to the MCU and stop the rainbow animation.

    Args:
        port:            serial device path (default /dev/ttyS2)
        connect_timeout: seconds to wait for port to open
        microphone:      if True, start reading the microphone immediately
        mic_device:      sounddevice device index or name (None = system default)
        mic_threshold:   minimum level change to trigger on_microphone callback
    '''
    global _channel, _client, _events, _self_module

    import pixelkit as _mod
    _self_module = _mod

    _channel = SerialChannel(port, {
        'baudRate':  115200,
        'xon':       True,
        'xoff':      True,
        'padLength': 227,
    })

    _channel.wait_ready()
    time.sleep(0.5)

    _client = RPCClient(_channel)
    _events = EventStream(_channel)

    done = threading.Event()
    _channel.send_break(5, lambda err: done.set())
    done.wait(timeout=5.0)
    time.sleep(2.0)

    _stop_animation()
    time.sleep(1.0)
    _stop_animation()
    time.sleep(1.0)

    def _queue(name, detail={}):
        with _events_lock:
            _pending_events.append((name, detail))

    _events.on('button-down', lambda d: _queue('button-down', d))
    _events.on('button-up',   lambda d: _queue('button-up',   d))
    _events.on('mode-change', lambda d: _queue('mode-change', d))

    if microphone:
        start_microphone(device=mic_device, threshold=mic_threshold)


def _stop_animation(callback=None):
    if _client:
        _client.call('start-anim-control', [{'blackout-incr': 8}], callback)


# --- Interrupt ----------------------------------------------------------------

def interrupt():
    '''Clear display and raise KeyboardInterrupt.'''
    clear()
    render()
    raise KeyboardInterrupt


# --- Control polling ----------------------------------------------------------

def check_controls():
    '''Poll all controls and fire callbacks. Call once per loop iteration.'''
    _dispatch_events()


def _dispatch_events():
    global dial_value
    global is_pressing_up, is_pressing_down, is_pressing_left
    global is_pressing_right, is_pressing_click
    global is_pressing_a, is_pressing_b, is_pressing_reset

    with _events_lock:
        events = list(_pending_events)
        _pending_events.clear()

    for name, detail in events:
        if name == 'button-down':
            btn = detail.get('button-id', '')
            if   btn == 'js-up'     and not is_pressing_up:
                is_pressing_up    = True;  _fire('on_joystick_up')
            elif btn == 'js-down'   and not is_pressing_down:
                is_pressing_down  = True;  _fire('on_joystick_down')
            elif btn == 'js-left'   and not is_pressing_left:
                is_pressing_left  = True;  _fire('on_joystick_left')
            elif btn == 'js-right'  and not is_pressing_right:
                is_pressing_right = True;  _fire('on_joystick_right')
            elif btn == 'js-click'  and not is_pressing_click:
                is_pressing_click = True;  _fire('on_joystick_click')
            elif btn == 'btn-A'     and not is_pressing_a:
                is_pressing_a     = True;  _fire('on_button_a')
            elif btn == 'btn-B'     and not is_pressing_b:
                is_pressing_b     = True;  _fire('on_button_b')
            elif btn == 'btn-reset' and not is_pressing_reset:
                is_pressing_reset = True;  _fire('on_button_reset')

        elif name == 'button-up':
            btn = detail.get('button-id', '')
            if   btn == 'js-up':     is_pressing_up    = False
            elif btn == 'js-down':   is_pressing_down  = False
            elif btn == 'js-left':   is_pressing_left  = False
            elif btn == 'js-right':  is_pressing_right = False
            elif btn == 'js-click':  is_pressing_click = False
            elif btn == 'btn-A':     is_pressing_a     = False
            elif btn == 'btn-B':     is_pressing_b     = False
            elif btn == 'btn-reset': is_pressing_reset = False

        elif name == 'mode-change':
            new_val = _MODE_MAP.get(detail.get('mode', ''), dial_value)
            if new_val != dial_value:
                dial_value = new_val
                _fire('on_dial', dial_value)


def _fire(handler_name, *args):
    '''Call a module-level callback if it is set to a callable.'''
    handler = getattr(_self_module, handler_name, None)
    if callable(handler):
        try:
            handler(*args)
        except Exception as e:
            pass


# --- Buzzer -------------------------------------------------------------------

def beep(frequency, duration):
    '''
    Play a tone. Non-blocking — returns immediately.

    Args:
        frequency: Hz (int)
        duration:  seconds (float)
    '''
    def _play():
        if _client:
            _client.call('play-tone', [{
                'freq':     int(frequency),
                'duration': int(duration * 1000),
            }])
    threading.Thread(target=_play, daemon=True).start()


# --- Microphone ---------------------------------------------------------------

_mic_running  = False
_mic_thread   = None
_mic_lock     = threading.Lock()
_beat_history = []

def start_microphone(device=None, samplerate=44100, blocksize=512,
                     threshold=5, scale=2000, beat_ratio=1.5,
                     beat_min_rms=0.01):
    '''
    Start reading the microphone in a background thread.

    microphone_value is updated continuously (0-255 RMS level).
    on_microphone(value) fires when level changes by more than threshold.
    on_beat() fires when a sudden volume spike is detected.

    Args:
        device:       sounddevice device index or name (None = system default)
        samplerate:   sample rate in Hz (default 44100)
        blocksize:    samples per audio block — lower = more responsive
        threshold:    minimum change in level (0-255) to fire on_microphone
        scale:        multiplier to convert RMS (0.0-1.0) to 0-255 range.
                      Increase if mic seems quiet, decrease if always maxed.
        beat_ratio:   how much louder than average a block must be to count
                      as a beat (default 1.5 = 50% louder than rolling avg)
        beat_min_rms: minimum raw RMS to consider as a beat — filters silence
    '''
    global _mic_running, _mic_thread

    if _mic_running:
        return

    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        print('Microphone requires sounddevice and numpy:')
        print('  pip install sounddevice')
        print('  (numpy should already be present in the venv)')
        return

    _mic_running = True

    def _audio_thread():
        global microphone_value, _mic_running
        last_reported = 0

        def _callback(indata, frames, cb_time, status):
            global microphone_value
            rms = float(np.sqrt(np.mean(indata ** 2)))
            val = min(255, int(rms * scale))
            with _mic_lock:
                microphone_value = val
                _beat_history.append(rms)
                if len(_beat_history) > 30:
                    _beat_history.pop(0)

        with sd.InputStream(device=device,
                            channels=1,
                            samplerate=samplerate,
                            blocksize=blocksize,
                            callback=_callback):
            while _mic_running:
                time.sleep(0.02)

                with _mic_lock:
                    val     = microphone_value
                    history = list(_beat_history)

                # Fire on_microphone if level changed enough
                if abs(val - last_reported) >= threshold:
                    last_reported = val
                    _fire('on_microphone', val)

                # Beat detection: current RMS vs rolling average
                if len(history) >= 5:
                    avg = sum(history[:-1]) / len(history[:-1])
                    cur = history[-1]
                    if cur > avg * beat_ratio and cur > beat_min_rms:
                        _fire('on_beat')

    _mic_thread = threading.Thread(target=_audio_thread, daemon=True)
    _mic_thread.start()


def stop_microphone():
    '''Stop the microphone background thread.'''
    global _mic_running
    _mic_running = False


# --- Colour helpers -----------------------------------------------------------

def hsv_to_rgb(h, s, v):
    '''
    Convert HSV to RGB tuple (0-255 each).

    Args:
        h: hue        0.0-1.0
        s: saturation 0.0-1.0
        v: value      0.0-1.0
    '''
    if s == 0.0:
        c = int(v * 255)
        return (c, c, c)
    h_i = int(h * 6.0) % 6
    f   = (h * 6.0) - int(h * 6.0)
    p   = v * (1.0 - s)
    q   = v * (1.0 - s * f)
    t   = v * (1.0 - s * (1.0 - f))
    r, g, b = [
        (v, t, p), (q, v, p), (p, v, t),
        (p, q, v), (t, p, v), (v, p, q),
    ][h_i]
    return (int(r * 255), int(g * 255), int(b * 255))


# --- Coordinate helper --------------------------------------------------------

def get_index_from_coordinate(x, y):
    '''Return the flat pixel index for grid coordinate (x, y).'''
    return y * WIDTH + x


# --- Pixel functions ----------------------------------------------------------

def set_pixel(x, y, color=(0, 255, 0)):
    '''
    Set a single pixel colour.

    Args:
        x, y:  grid coordinates (0-15, 0-7)
        color: (r, g, b) tuple, each 0-255
    '''
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        _pixels[get_index_from_coordinate(x, y)] = (
            int(color[0]), int(color[1]), int(color[2])
        )


def set_pixel_hsv(x, y, hsv=(0.0, 1.0, 1.0)):
    '''Set a pixel using HSV values (h, s, v each 0.0-1.0).'''
    set_pixel(x, y, hsv_to_rgb(*hsv))


def set_background(rgb=(0, 0, 0)):
    '''Fill the entire display with one colour.'''
    c = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    for i in range(_NPIX):
        _pixels[i] = c


def clear():
    '''Turn all pixels off.'''
    set_background((0, 0, 0))


def fill_rect(x, y, w, h, color=(255, 255, 255)):
    '''Fill a rectangle with a colour.'''
    for dy in range(h):
        for dx in range(w):
            set_pixel(x + dx, y + dy, color)


def draw_rect(x, y, w, h, color=(255, 255, 255)):
    '''Draw a rectangle outline.'''
    for dx in range(w):
        xi = x + dx
        if 0 <= xi < WIDTH:
            if 0 <= y         < HEIGHT: set_pixel(xi, y,         color)
            if 0 <= y + h - 1 < HEIGHT: set_pixel(xi, y + h - 1, color)
    for dy in range(1, h - 1):
        yi = y + dy
        if 0 <= yi < HEIGHT:
            if 0 <= x         < WIDTH: set_pixel(x,         yi, color)
            if 0 <= x + w - 1 < WIDTH: set_pixel(x + w - 1, yi, color)


def draw_line(x0, y0, x1, y1, color=(255, 255, 255)):
    '''Draw a line using Bresenham's algorithm.'''
    dx = abs(x1 - x0); dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        set_pixel(x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy: err -= dy; x0 += sx
        if e2 <  dx: err += dx; y0 += sy


def draw_circle(cx, cy, r, color=(255, 255, 255)):
    '''Draw a circle outline using Bresenham's circle algorithm.'''
    x   = r
    y   = 0
    err = 1 - r
    while x >= y:
        set_pixel(cx + x, cy + y, color)
        set_pixel(cx + y, cy + x, color)
        set_pixel(cx - y, cy + x, color)
        set_pixel(cx - x, cy + y, color)
        set_pixel(cx - x, cy - y, color)
        set_pixel(cx - y, cy - x, color)
        set_pixel(cx + y, cy - x, color)
        set_pixel(cx + x, cy - y, color)
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1


def fill_circle(cx, cy, r, color=(255, 255, 255)):
    '''Draw a filled circle.'''
    x   = r
    y   = 0
    err = 1 - r
    while x >= y:
        draw_line(cx - x, cy + y, cx + x, cy + y, color)
        draw_line(cx - x, cy - y, cx + x, cy - y, color)
        draw_line(cx - y, cy + x, cx + y, cy + x, color)
        draw_line(cx - y, cy - x, cx + y, cy - x, color)
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1


# --- Render -------------------------------------------------------------------

def render():
    '''
    Send the current pixel buffer to the hardware.
    Blocks until the previous frame has been confirmed sent.
    '''
    global _render_pending
    if not _client:
        return

    _render_event.wait()
    _render_event.clear()
    _render_pending = True

    buf = bytearray(_NPIX * 2)
    for i, (r, g, b) in enumerate(_pixels):
        v = (r & 0xF8) << 8 | (g & 0xFC) << 3 | (b & 0xF8) >> 3
        struct.pack_into('>H', buf, i * 2, v)

    frame = base64.b64encode(bytes(buf)).decode('ascii')

    def _done(err, val):
        global _render_pending
        _render_pending = False
        _render_event.set()

    _client.call('grid-bmp', [{'map': frame}], _done)


# --- Scrolling text -----------------------------------------------------------

try:
    from scroll_letters import letters
    from scroll_numbers import numbers
    from scroll_symbols  import symbols
    charset = {}
    charset.update(letters)
    charset.update(numbers)
    charset.update(symbols)
except ImportError:
    charset = {}


def draw_letter(x, y, l, c=(255, 255, 255)):
    '''Draw a single character at grid position (x, y).'''
    key = str(l)
    if key not in charset:
        return
    for ly, line in enumerate(charset[key]):
        for lx, val in enumerate(line):
            if val:
                set_pixel(x + lx, y + ly, c)


def buff_phrase(phrase='', offset=0, c=(255, 255, 255)):
    '''Build a scroll buffer for a text phrase.'''
    buff = [[0] * 16 for _ in range(5)]
    for ch in phrase:
        key = str(ch)
        if key not in charset:
            continue
        for ly, line in enumerate(charset[key]):
            buff[ly].extend(line)
            buff[ly].append(0)
    return buff


def draw_buff(buff, o=0, c=(255, 255, 255)):
    '''Draw a scroll buffer at horizontal offset o.'''
    c = (int(c[0]), int(c[1]), int(c[2]))
    for x in range(16):
        for y in range(5):
            try:
                if buff[y][o + x]:
                    set_pixel(x, 1 + y, c)
            except IndexError:
                pass


def scroll(p, color=(255, 255, 255), background=(0, 0, 0), interval=0.1):
    '''Scroll a text string across the display.'''
    buff = buff_phrase(p)
    for i in range(len(buff[0])):
        set_background(background)
        draw_buff(buff, i, color)
        render()
        time.sleep(interval)
    time.sleep(0.1)
    clear()
    render()


# --- run() convenience wrapper -----------------------------------------------

def run(update_fn, fps=20):
    '''
    Simple game loop helper.

    Calls check_controls() and update_fn() at the given fps, then renders.
    Equivalent to:
        while True:
            check_controls()
            update_fn()
            render()
            sleep(1/fps)

    Args:
        update_fn: callable called once per frame
        fps:       target frames per second (default 20)
    '''
    interval = 1.0 / fps
    while True:
        check_controls()
        update_fn()
        render()
        time.sleep(interval)