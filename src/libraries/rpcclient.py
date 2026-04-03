'''
rpcclient.py - Python port of the Kano kano2-shared-lib device-bus:
  - channels/serial.js  -> SerialChannel
  - client.js           -> RPCClient
  - event-stream.js     -> EventStream
'''

import json
import serial
import threading
import time
import uuid
from collections import deque

RETRY_DELAY  = 0.1
CALL_TIMEOUT = 30.0


# --- SerialChannel ------------------------------------------------------------

class SerialChannel:

    def __init__(self, device, opts=None):
        opts = opts or {}
        self.device     = device
        self.roles      = {}
        self.plugged    = True
        self.pad_length = opts.get('padLength', None)

        self._port      = None
        self._q         = deque()
        self._q_lock    = threading.Lock()
        self._q_sem     = threading.Semaphore(0)
        self._ready     = threading.Event()

        threading.Thread(target=self._open_and_dispatch,
                         args=(device, opts), daemon=True).start()

    def _open_port(self, device, opts):
        attempts = 0
        while True:
            try:
                return serial.Serial(
                    device,
                    baudrate=opts.get('baudRate', 115200),
                    xonxoff=opts.get('xon', False) or opts.get('xonxoff', False),
                    timeout=1
                )
            except Exception as e:
                if attempts < 5:
                    attempts += 1
                    time.sleep(RETRY_DELAY * attempts)
                else:
                    raise RuntimeError(
                        f'Could not open port {device} after 5 attempts') from e

    def _open_and_dispatch(self, device, opts):
        self._port = self._open_port(device, opts)
        self._ready.set()

        threading.Thread(target=self._read_loop, daemon=True).start()

        while True:
            self._q_sem.acquire()
            with self._q_lock:
                if not self._q:
                    continue
                req = self._q.popleft()
            content = req['content']
            cb      = req['callback']
            if content['type'] == 'brk':
                if self.plugged:
                    self._dispatch_break(content['length'], cb)
                else:
                    if cb:
                        cb(None)
            elif content['type'] == 'string':
                payload = content['value'] + '\r\n'
                if self.pad_length and len(payload) % self.pad_length > 0:
                    payload += '\x00' * (self.pad_length - (len(payload) % self.pad_length))
                if self.plugged:
                    try:
                        self._port.write(payload.encode())
                        self._port.flush()
                        if cb:
                            cb(None)
                    except Exception as e:
                        if cb:
                            cb(e)
                else:
                    if cb:
                        cb(None)

    def _dispatch_break(self, length_ms, callback):
        try:
            self._port.break_condition = True
            time.sleep(length_ms / 1000.0)
            self._port.break_condition = False
            self._port.write(b'U')
            self._port.flush()
            if callback:
                callback(None)
        except Exception as e:
            if callback:
                callback(e)

    def _read_loop(self):
        buf = b''
        while True:
            try:
                byte = self._port.read(1)
                if not byte:
                    continue
                buf += byte
                if buf.endswith(b'\r\n'):
                    line = buf.rstrip(b'\r\n\x00').decode('utf-8', errors='ignore').strip()
                    buf = b''
                    if not line:
                        continue
                    try:
                        message = json.loads(line)
                    except Exception:
                        continue
                    if not message:
                        continue
                    msg_type = message.get('type')
                    if msg_type == 'rpc-request':
                        if 'server' in self.roles:
                            self.roles['server'](message)
                    elif msg_type == 'rpc-response':
                        if 'client' in self.roles:
                            self.roles['client'](message)
                    elif msg_type in ('event', 'device-info'):
                        if 'event' in self.roles:
                            self.roles['event'](message)
            except Exception:
                pass

    def wait_ready(self):
        self._ready.wait()

    def send(self, msg_type, message, callback=None):
        message['type'] = msg_type
        with self._q_lock:
            self._q.append({
                'content':  {'type': 'string', 'value': json.dumps(message)},
                'callback': callback
            })
        self._q_sem.release()

    def send_break(self, length_ms, callback=None):
        with self._q_lock:
            self._q.append({
                'content':  {'type': 'brk', 'length': length_ms},
                'callback': callback
            })
        self._q_sem.release()

    def set_plugged(self, plugged):
        self.plugged = plugged

    def listen(self, role, callback):
        self.roles[role] = callback

    def close(self, callback=None):
        try:
            self._port.close()
            if callback:
                callback(None)
        except Exception as e:
            if callback:
                callback(e)


# --- RPCClient ----------------------------------------------------------------

class RPCClient:

    def __init__(self, channel):
        self.channel = channel
        self._calls  = {}
        self._lock   = threading.Lock()

        channel.listen('client', self._on_response)
        threading.Thread(target=self._reaper, daemon=True).start()

    def _on_response(self, response):
        call_id = response.get('id')
        with self._lock:
            entry = self._calls.pop(call_id, None)
        if entry:
            entry['cb'](response.get('err'), response.get('value'))

    def _reaper(self):
        while True:
            time.sleep(1.0)
            now = time.monotonic()
            expired = []
            with self._lock:
                for call_id, entry in list(self._calls.items()):
                    if now >= entry['expires']:
                        expired.append(entry['cb'])
                        del self._calls[call_id]
            for cb in expired:
                cb('Request timed out', None)

    def call(self, method, params=None, callback=None, timeout=None):
        if callback is None and callable(params):
            callback = params
            params   = []
        params   = params   or []
        callback = callback or (lambda err, val: None)
        timeout  = timeout  or CALL_TIMEOUT

        request = {
            'id':     str(uuid.uuid4()),
            'method': method,
            'params': list(params)
        }

        with self._lock:
            self._calls[request['id']] = {
                'cb':      callback,
                'expires': time.monotonic() + timeout
            }

        def _on_send_err(err):
            if err:
                with self._lock:
                    self._calls.pop(request['id'], None)
                callback(err, None)

        self.channel.send('rpc-request', request, _on_send_err)
        return self


# --- EventStream --------------------------------------------------------------

class EventStream:

    def __init__(self, channel):
        self._handlers = {}
        self._lock     = threading.Lock()
        self._queue    = deque()
        self._q_sem    = threading.Semaphore(0)

        channel.listen('event', self._enqueue)
        threading.Thread(target=self._dispatcher, daemon=True).start()

    def _enqueue(self, message):
        if message.get('type') == 'event':
            self._queue.append((message.get('name'), message.get('detail', {})))
            self._q_sem.release()

    def _dispatcher(self):
        while True:
            self._q_sem.acquire()
            try:
                name, detail = self._queue.popleft()
            except IndexError:
                continue
            with self._lock:
                handlers = list(self._handlers.get(name, []))
            for cb in handlers:
                try:
                    cb(detail)
                except Exception:
                    pass

    def on(self, event, callback):
        with self._lock:
            self._handlers.setdefault(event, []).append(callback)

    def remove_listener(self, event, callback):
        with self._lock:
            handlers = self._handlers.get(event, [])
            if callback in handlers:
                handlers.remove(callback)

    def remove_all_listeners(self, event=None):
        with self._lock:
            if event:
                self._handlers.pop(event, None)
            else:
                self._handlers.clear()

    def stop(self, callback=None):
        self.channel.close(callback)
