#!/usr/bin/python

from __future__ import print_function

import json
import os
import signal
import subprocess
import sys
import threading
import time
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from urlparse import parse_qs, urlparse

HOST = "0.0.0.0"
PORT = 8080

PROJECT_DIR = "/root/project"
TONE_BINARY = os.path.join(PROJECT_DIR, "tone3")
SONG_FILE = os.path.join(PROJECT_DIR, "song.txt")

LED_MAP = {
    "usr_led1": "/sys/class/leds/usr_led1/brightness",
    "usr_led2": "/sys/class/leds/usr_led2/brightness",
    "led_r": "/sys/class/leds/led_r/brightness",
    "led_g": "/sys/class/leds/led_g/brightness",
    "led_b": "/sys/class/leds/led_b/brightness",
}

MAX_FREQUENCY = 2000
MAX_TONE_DURATION_MS = 60000
MAX_SONG_DURATION_SEC = 120

process_lock = threading.RLock()
tone_process = None
tone_start_time = 0


def json_bytes(payload):
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def read_led(name):
    path = LED_MAP.get(name)
    if not path:
        return 0
    try:
        with open(path, "r") as f:
            return 1 if int(f.read().strip()) > 0 else 0
    except (OSError, ValueError):
        return 0


def set_led(name, value):
    if name not in LED_MAP:
        raise ValueError("Invalid LED name")
    if value not in (0, 1):
        raise ValueError("LED value must be 0 or 1")
    path = LED_MAP[name]
    with open(path, "w") as f:
        f.write("255" if value else "0")


def _wait_with_timeout(process, timeout_sec):
    deadline = time.time() + timeout_sec
    while process.poll() is None:
        if time.time() >= deadline:
            return False
        time.sleep(0.05)
    return True


def stop_tone_locked():
    global tone_process

    process = tone_process
    tone_process = None

    if process is not None and process.poll() is None:
        try:
            process.terminate()
        except Exception:
            pass
        if not _wait_with_timeout(process, 2.0):
            try:
                process.kill()
                _wait_with_timeout(process, 1.0)
            except Exception:
                pass

    if os.path.isfile(TONE_BINARY):
        try:
            proc = subprocess.Popen(
                [TONE_BINARY, "stop"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
            _wait_with_timeout(proc, 3.0)
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass
        except Exception:
            pass


def stop_tone():
    with process_lock:
        stop_tone_locked()


def reap_process(process):
    global tone_process
    try:
        _wait_with_timeout(process, MAX_SONG_DURATION_SEC)
        if process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass
    finally:
        with process_lock:
            if tone_process is process:
                tone_process = None


def start_process(args):
    global tone_process, tone_start_time

    with process_lock:
        stop_tone_locked()

        process = subprocess.Popen(
            args,
            cwd=PROJECT_DIR,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )

        tone_process = process
        tone_start_time = time.time()

        thread = threading.Thread(
            target=reap_process,
            args=(process,),
        )
        thread.daemon = True
        thread.start()

        return process.pid


def start_tone(freq, duration_ms):
    if not 0 <= freq <= MAX_FREQUENCY:
        raise ValueError("Frequency must be 0-5000 Hz")
    if not 10 <= duration_ms <= MAX_TONE_DURATION_MS:
        raise ValueError("Duration must be 10-1000 ms")
    if not os.path.isfile(TONE_BINARY):
        raise RuntimeError("tone3 binary not found")

    return start_process([TONE_BINARY, str(freq), str(duration_ms)])


def start_song():
    if not os.path.isfile(TONE_BINARY):
        raise RuntimeError("tone3 binary not found")
    if not os.path.isfile(SONG_FILE):
        raise RuntimeError("song.txt not found")

    return start_process([TONE_BINARY, "song", SONG_FILE])


def playback_state():
    with process_lock:
        process = tone_process
        is_playing = process is not None and process.poll() is None
        return {
            "playing": is_playing,
            "pid": process.pid if is_playing else None,
        }


def initialize_leds():
    for path_str in LED_MAP.values():
        trigger = os.path.join(os.path.dirname(path_str), "trigger")
        try:
            if os.path.exists(trigger):
                with open(trigger, "w") as f:
                    f.write("none")
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    server_version = "ZynqController/2.0"

    def send_json(self, status, payload):
        body = json_bytes(payload)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def parse_body(self):
        content_length = self.headers.get("Content-Length", "0")
        try:
            length = int(content_length)
        except ValueError:
            raise ValueError("Invalid Content-Length")

        if length <= 0:
            return {}
        if length > 65536:
            raise ValueError("Request body too large")

        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("Invalid JSON body")

        if not isinstance(body, dict):
            raise ValueError("JSON body must be an object")
        return body

    def query(self):
        return parse_qs(urlparse(self.path).query, keep_blank_values=True)

    def route_path(self):
        return urlparse(self.path).path

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_GET(self):
        try:
            path = self.route_path()

            if path == "/" or path == "/index.html":
                index_file = os.path.join(PROJECT_DIR, "index.html")
                if os.path.isfile(index_file):
                    with open(index_file, "rb") as f:
                        body = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_json(404, {"ok": False, "error": "index.html not found"})
                return

            if path == "/health":
                data = {
                    "ok": True,
                    "service": "zynq-controller",
                    "time": time.time(),
                    "tone_binary": os.path.isfile(TONE_BINARY),
                    "song_file": os.path.isfile(SONG_FILE),
                }
                data.update(playback_state())
                self.send_json(200, data)
                return

            if path == "/state":
                data = {
                    "ok": True,
                    "leds": {name: read_led(name) for name in LED_MAP},
                }
                data.update(playback_state())
                self.send_json(200, data)
                return

            if path == "/led":
                q = self.query()
                name = q.get("name", [""])[0]
                raw_value = q.get("val", [""])[0]
                try:
                    value = int(raw_value)
                except ValueError:
                    raise ValueError("LED value must be an integer")
                set_led(name, value)
                self.send_json(200, {"ok": True, "name": name, "value": value})
                return

            if path == "/buzzer":
                q = self.query()
                try:
                    freq = int(q.get("freq", [""])[0])
                    duration_ms = int(q.get("duration", ["300"])[0])
                except ValueError:
                    raise ValueError("Frequency and duration must be integers")
                pid = start_tone(freq, duration_ms)
                self.send_json(200, {
                    "ok": True, "pid": pid, "freq": freq, "duration": duration_ms,
                })
                return

            if path == "/play_song":
                pid = start_song()
                self.send_json(200, {"ok": True, "playing": True, "pid": pid})
                return

            if path == "/stop_song":
                stop_tone()
                self.send_json(200, {"ok": True, "playing": False})
                return

            self.send_json(404, {"ok": False, "error": "Not found"})
        except ValueError as error:
            self.send_json(400, {"ok": False, "error": str(error)})
        except Exception as error:
            self.send_json(500, {"ok": False, "error": str(error)})

    def do_POST(self):
        try:
            path = self.route_path()
            body = self.parse_body()

            if path == "/led":
                name = str(body.get("name", ""))
                value = int(body.get("value"))
                set_led(name, value)
                self.send_json(200, {"ok": True, "name": name, "value": value})
                return

            if path == "/buzzer":
                freq = int(body.get("freq"))
                duration_ms = int(body.get("duration", 300))
                pid = start_tone(freq, duration_ms)
                self.send_json(200, {
                    "ok": True, "pid": pid, "freq": freq, "duration": duration_ms,
                })
                return

            if path == "/play_song":
                pid = start_song()
                self.send_json(200, {"ok": True, "playing": True, "pid": pid})
                return

            if path == "/stop_song":
                stop_tone()
                self.send_json(200, {"ok": True, "playing": False})
                return

            self.send_json(404, {"ok": False, "error": "Not found"})
        except (TypeError, ValueError) as error:
            self.send_json(400, {"ok": False, "error": str(error)})
        except Exception as error:
            self.send_json(500, {"ok": False, "error": str(error)})

    def log_message(self, format_string, *args):
        message = format_string % args
        sys.stdout.write(
            "%s [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), message)
        )
        sys.stdout.flush()


def handle_shutdown(signum, frame):
    stop_tone()
    raise KeyboardInterrupt


def watchdog_loop():
    while True:
        time.sleep(10)
        with process_lock:
            process = tone_process
            if process is not None and process.poll() is None:
                elapsed = time.time() - tone_start_time
                if elapsed > MAX_SONG_DURATION_SEC:
                    sys.stdout.write(
                        "watchdog: killing stuck process (pid=%d, elapsed=%.0fs)\n"
                        % (process.pid, elapsed)
                    )
                    sys.stdout.flush()
                    try:
                        process.kill()
                    except Exception:
                        pass


def main():
    if os.geteuid() != 0:
        sys.exit("This service must run as root")

    if not os.path.isfile(TONE_BINARY):
        sys.exit("Missing binary: %s" % TONE_BINARY)

    initialize_leds()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    watchdog = threading.Thread(target=watchdog_loop)
    watchdog.daemon = True
    watchdog.start()

    server = HTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True

    print("Listening on http://%s:%d" % (HOST, PORT))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        stop_tone()


if __name__ == "__main__":
    main()
