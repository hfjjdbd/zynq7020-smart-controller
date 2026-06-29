# AGENTS.md

## Project: ZYNQ7020 Network Smart Controller

### Hardware
- **Board**: MYIR Z-Turn Board (Zynq-7020, dual-core ARM Cortex-A9, 1GB DDR3)
- **System**: Ubuntu 12.04, Linux 3.15.0, Python 2.7.3
- **SSH**: `ssh root@192.168.1.100`, password: `114514`

### GPIO Mapping (DO NOT GUESS)
| Function | GPIO | Control Interface |
|----------|------|-------------------|
| usr_led1 | 0 | `/sys/class/leds/usr_led1/brightness` (0/255) |
| usr_led2 | 9 | `/sys/class/leds/usr_led2/brightness` (0/255) |
| led_r (Green) | 114 | `/sys/class/leds/led_r/brightness` |
| led_g (Blue) | 115 | `/sys/class/leds/led_g/brightness` |
| led_b (Red) | 116 | `/sys/class/leds/led_b/brightness` |
| Buzzer | 117 | `/sys/class/gpio/gpio117/value` (must unbind gpio-beeper first) |
| Button K1 (BROKEN) | 50 | GPIO 50 — interrupt registered but never fires, value always 1. Button feature REMOVED. |

### Known Gotchas
- **LED colors in device tree are WRONG**: `led_r` is physically GREEN, `led_g` is BLUE, `led_b` is RED
- **LED trigger reset**: After reboot, `led_r` defaults to `heartbeat` mode (blinking). Write `none` to trigger at startup.
- **Buzzer frequency**: `gpio-beeper` driver only supports on/off. Must unbind driver (`echo gpio-beep.3 > /sys/bus/platform/drivers/gpio-beeper/unbind`) then use sysfs GPIO control for tone generation.
- **RGB LED brightness**: Must write `255` not `1` — value of 1 is too dim to see.
- **Python 2.7 only**: No Python 3 on the dev board. Use `print 'text'` syntax, `BaseHTTPServer` module.
- **CSS `%` conflict**: Python `%` string formatting conflicts with CSS `100%`. Use string concatenation instead of `%` template substitution.

### File Locations
- `/root/project/web_server.py` — Main web server (Python 2.7)
- `/root/project/tone3` — Buzzer frequency control (compiled C)
- `/root/project/tone3.c` — Buzzer source code
- PC: `~/下载/mimotest/share_wifi.sh` — Network sharing script
- PC: `~/下载/mimotest/web_server.py` — Web server source (sync to dev board)

### Commands
```bash
# Start web server on dev board
cd /root/project && nohup python web_server.py > web.log 2>&1 &

# Network sharing (PC)
sudo bash ~/下载/mimotest/share_wifi.sh on

# Compile tone3 (dev board)
gcc -o /root/project/tone3 /root/project/tone3.c
```
