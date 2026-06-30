# ZYNQ7020 Smart Controller

基於 MYIR Z-Turn Board（Zynq-7020）的網絡智能控制系統。通過瀏覽器遠程控制開發板上的 LED 燈和蜂鳴器。

## 架構

```
瀏覽器 → 開發板 (192.168.1.100:8080) 直接
  ↓
web_server.py (Python 2.7 HTTP 後端)
  ↓
tone3 (C 蜂鳴器驅動) → GPIO 117
LED sysfs → /sys/class/leds/*
```

## 硬件

- **開發板**：MYIR Z-Turn（Zynq-7020, ARM Cortex-A9, Ubuntu 12.04）
- **蜂鳴器**：無源壓電蜂鳴器，PL 側 GPIO 117 驅動
- **LED**：5 個（usr_led1, usr_led2, led_r/led_g/led_b）
- **網絡**：通過 PC 共享 WiFi 上網

## 文件說明

### 開發板（部署到 `/root/project/`）

| 文件 | 說明 |
|------|------|
| `web_server.py` | HTTP 後端（Python 2.7），提供 REST API + 靜態頁面 |
| `tone3` | 編譯後的蜂鳴器程序（C，gcc 4.6.3） |
| `tone3.c` | tone3 源碼，含 60 個音階查找表 |
| `index.html` | 控制頁面（靜態 HTML，從瀏覽器直接訪問） |
| `song.txt` | 旋律數據（`freq duration_ms` 格式） |

### 電腦端

| 文件 | 說明 |
|------|------|
| `extract_notes.py` | 旋律提取工具（basic-pitch / librosa） |
| `requirements-audio.txt` | Python 音頻依賴 |
| `share_wifi.sh` | PC 網絡共享腳本（dnsmasq + iptables NAT） |
| `Music/` | 音頻素材（mp3, mp4, aac） |

## 快速開始

### 1. 啟動網絡共享（PC）

```bash
sudo bash share_wifi.sh on
```

### 2. 開啟開發板服務

```bash
ssh root@192.168.1.100
/etc/init.d/zynq-controller start
```

### 3. 瀏覽器訪問

打開 **http://192.168.1.100:8080**

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/` | 控制頁面 |
| GET | `/health` | 健康檢查 |
| GET | `/state` | LED 和播放狀態 |
| POST | `/led` | LED 控制（`{"name":"usr_led1","value":1}`） |
| POST | `/buzzer` | 蜂鳴器單音（`{"freq":440,"duration":300}`） |
| POST | `/play_song` | 播放歌曲 |
| POST | `/stop_song` | 停止播放 |

## 旋律提取

```bash
# 從 MIDI 提取
python3 extract_notes.py song.mid --text-output song.txt

# 從音頻提取（精度較低）
python3 extract_notes.py audio.mp3 --text-output song.txt
```

## 部署

```bash
# 同步文件到開發板
cat tone3.c | ssh root@192.168.1.100 'cat > /root/project/tone3.c'
cat web_server.py | ssh root@192.168.1.100 'cat > /root/project/web_server.py'
cat index.html | ssh root@192.168.1.100 'cat > /root/project/index.html'
cat song.txt | ssh root@192.168.1.100 'cat > /root/project/song.txt'

# 在開發板編譯 tone3
ssh root@192.168.1.100 'cd /root/project && gcc -std=gnu99 -Wall -O2 -o tone3 tone3.c -lrt'

# 重啟服務
ssh root@192.168.1.100 '/etc/init.d/zynq-controller restart'
```

## 技術細節

### 蜂鳴器驅動

- 無源壓電蜂鳴器，PL 側 FPGA GPIO 驅動
- `clock_nanosleep` 絕對時間定時，頻率精度 0%
- 60 個標準音階查找表（C1-B5, 33-988Hz）
- 最大頻率 2000Hz
- 啟動時自動校準 GPIO write 延遲

### GPIO 映射

| 功能 | GPIO | 路徑 |
|------|------|------|
| usr_led1 | 0 | `/sys/class/leds/usr_led1/brightness` |
| usr_led2 | 9 | `/sys/class/leds/usr_led2/brightness` |
| led_r（物理綠色）| 114 | `/sys/class/leds/led_r/brightness` |
| led_g（物理藍色）| 115 | `/sys/class/leds/led_g/brightness` |
| led_b（物理紅色）| 116 | `/sys/class/leds/led_b/brightness` |
| 蜂鳴器 | 117 | `/sys/class/gpio/gpio117/value` |

**注意**：設備樹 LED 顏色標籤是錯的（r=物理綠，g=藍，b=紅）。

### 旋律格式（song.txt）

```
# freq_hz duration_ms
440 300
0 50        ← 休止
523 300
```

### 開發板環境

- Python 2.7（無 Python 3）
- GCC 4.6.3（用 `-std=gnu99 -lrt`）
- SysV init（無 systemd）
- SSH 免密登入（PermitEmptyPasswords yes + UsePAM no）
- DNS 自動配置（rc.local 寫入 resolv.conf）
