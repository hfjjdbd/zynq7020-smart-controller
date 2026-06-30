# AGENTS.md

## Project: ZYNQ7020 Smart Controller

Two environments: **PC** (Next.js frontend + Python tooling) and **dev board** (Python 2.7 backend + C buzzer). They communicate over HTTP.

### Dev Board

- **Board**: MYIR Z-Turn (Zynq-7020, armv7l, Ubuntu 12.04)
- **SSH**: `ssh root@192.168.1.100`, password `114514`
- **Python**: 2.7 only — no Python 3. Use `BaseHTTPServer`, `print 'text'`, no f-strings, no `**dict` unpacking, no `threading.Thread(daemon=True)`.
- **GCC**: 4.6.3 — no `-std=c11`. Use `-std=gnu99` and link with `-lrt` for `clock_nanosleep`/`clock_gettime`.
- **Init**: SysV init (`/etc/init.d/zynq-controller`), NOT systemd. `systemctl` does not exist.
- **Deploy**: Pipe files via `cat file | ssh root@192.168.1.100 'cat > /path'`. `scp` requires interactive password.

### GPIO Mapping (DO NOT GUESS)

| Function | GPIO | Path |
|----------|------|------|
| usr_led1 | 0 | `/sys/class/leds/usr_led1/brightness` |
| usr_led2 | 9 | `/sys/class/leds/usr_led2/brightness` |
| led_r (physically GREEN) | 114 | `/sys/class/leds/led_r/brightness` |
| led_g (physically BLUE) | 115 | `/sys/class/leds/led_g/brightness` |
| led_b (physically RED) | 116 | `/sys/class/leds/led_b/brightness` |
| Buzzer | 117 | `/sys/class/gpio/gpio117/value` (must unbind gpio-beeper first) |
| Button K1 (BROKEN) | 50 | Never fires. Feature removed. |

**Gotchas**:
- LED colors in device tree are WRONG (r=green, g=blue, b=red).
- LED brightness: write `255` not `1` — value of 1 is invisible.
- After reboot, `led_r` defaults to `heartbeat` trigger — write `none` to stop blinking.
- Buzzer: must unbind `gpio-beep.3` from `/sys/bus/platform/drivers/gpio-beeper/unbind` before using GPIO 117.
- `tone3.c` handles unbinding/export/init automatically.

### Architecture

```
Browser → Next.js (port 3000) → /api/board/* proxy → Dev board (port 8080)
```

- **Frontend** (`zynq-controller/`): Next.js 16, React 19. All board requests go through `/api/board/*` API routes (server-side proxy). Never fetch `192.168.1.100:8080` directly from client components.
- **Backend** (`web_server.py`): Python 2.7 HTTP server on port 8080. Endpoints: `/health`, `/state`, `/led`, `/buzzer`, `/play_song`, `/stop_song`. Single-process audio control via `tone3` binary.
- **Buzzer** (`tone3.c` → `tone3`): C program for GPIO 117 square-wave generation. Supports single tone and song file playback. Self-initializes GPIO.

### Commands

```bash
# === PC ===

# Frontend dev
cd zynq-controller && npm run dev      # http://localhost:3000
cd zynq-controller && npm run build     # production build

# Test board proxy (requires dev server running)
curl http://127.0.0.1:3000/api/board/health

# Test board directly
curl http://192.168.1.100:8080/health

# Compile tone3 locally (syntax check only, no GPIO)
gcc -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -o /tmp/tone3-check tone3.c

# Extract melody from audio (requires .venv with librosa)
. .venv/bin/activate
python extract_notes.py output.aac --text-output song.txt --json-output song.json

# === DEV BOARD ===

# Compile tone3 on board (must use -std=gnu99 -lrt)
gcc -std=gnu99 -Wall -Wextra -O2 -o tone3 tone3.c -lrt

# Service management
/etc/init.d/zynq-controller start|stop|restart|status

# Quick tone test
./tone3 440 150 && ./tone3 stop
```

### File Locations

| File | Purpose |
|------|---------|
| `web_server.py` | Board backend (Python 2.7) — deploys to `/root/project/` |
| `tone3.c` | Buzzer C source — compile on board, NOT cross-compile |
| `extract_notes.py` | Melody extraction (PC only, needs librosa) |
| `song.txt` | `freq duration_ms` format, `freq=0` = rest |
| `zynq-controller/` | Next.js frontend |
| `zynq-controller/lib/board.ts` | Server-side board fetch utility |
| `zynq-controller/app/api/board/*/route.ts` | API proxy routes |
| `share_wifi.sh` | PC network sharing script |

### Constraints

- Do NOT use `git add .` — stage files explicitly.
- Do NOT push without user approval.
- Do NOT write passwords to code, logs, or commit messages.
- Do NOT use Python 3 syntax in `web_server.py` (board has Python 2.7 only).
- Buzzer tests: max 1 second single tone, max 3 seconds song playback.
- `song.txt` must preserve `freq=0` rest events — do not compress rests.
