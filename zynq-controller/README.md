# ZYNQ7020 Smart Controller

Web 控制介面，用於控制 Zynq-7020 開發板上的 LED 燈和蜂鳴器。

## 系統架構

```
瀏覽器 → 開發板 (192.168.1.100:8080) 直接
  ↓ sysfs GPIO
LED: /sys/class/leds/*
蜂鳴器: tone3 → GPIO 117
```

前端是單個靜態 HTML 文件（`index.html`），直接調用開發板 API，無需 Node.js。

## 快速啟動

### 1. 確保開發板後端運行

```bash
ssh root@192.168.1.100 '/etc/init.d/zynq-controller start'
```

確認：
```bash
curl http://192.168.1.100:8080/health
# 應返回 {"ok":true,"tone_binary":true,"song_file":true,...}
```

### 2. 打開控制頁面

**方式 A：直接打開文件**
```bash
# 雙擊 index.html，或在瀏覽器中打開
file:///home/degenbrecher/App/mimotest/index.html
```

**方式 B：用 Python 起 HTTP 服務**
```bash
cd /home/degenbrecher/App/mimotest
python3 -m http.server 8000
# 瀏覽器打開 http://localhost:8000/index.html
```

不需要 npm、不需要 Node.js、不需要 build。

## 使用方式

### 瀏覽器操作

- **LED 控制**：點擊 ON/OFF 按鈕開關對應 LED
- **蜂鳴器**：點擊音符按鈕播放單音（300ms）
- **播放音樂**：點擊「Play Music」播放 song.txt 中的旋律
- **停止**：點擊「Stop」立即停止播放
- **主題切換**：右上角按鈕切換深色/淺色

### API 操作

```bash
# LED 控制
curl 'http://192.168.1.100:8080/led?name=usr_led1&val=1'   # 開
curl 'http://192.168.1.100:8080/led?name=usr_led1&val=0'   # 關

# 蜂鳴器 (頻率 Hz, 時長 ms)
curl 'http://192.168.1.100:8080/buzzer?freq=440&duration=150'

# 播放/停止歌曲
curl -X POST http://192.168.1.100:8080/play_song
curl -X POST http://192.168.1.100:8080/stop_song

# 查看狀態
curl http://192.168.1.100:8080/state
```

可用 LED 名稱：`usr_led1`, `usr_led2`, `led_r`, `led_g`, `led_b`

## 部署更新

### 後端更新

```bash
cat web_server.py | ssh root@192.168.1.100 'cat > /root/project/web_server.py'
cat tone3.c | ssh root@192.168.1.100 'cat > /root/project/tone3.c'
ssh root@192.168.1.100 'cd /root/project && gcc -std=gnu99 -Wall -Wextra -O2 -o tone3 tone3.c -lrt'
ssh root@192.168.1.100 '/etc/init.d/zynq-controller restart'
```

### 前端更新

直接修改 `index.html`，刷新瀏覽器即可。無需 build。

### 歌曲更新

```bash
. .venv/bin/activate
python extract_notes.py output.aac --text-output song.txt --json-output song.json
cat song.txt | ssh root@192.168.1.100 'cat > /root/project/song.txt'
```

## 服務管理

```bash
# 開發板
ssh root@192.168.1.100 '/etc/init.d/zynq-controller start|stop|restart|status'
```

## 故障排查

```bash
# 板端日誌
ssh root@192.168.1.100 'cat /var/log/zynq-controller.log'

# 檢查蜂鳴器殘留進程
ssh root@192.168.1.100 'ps aux | grep tone3 | grep -v grep'

# 強制停止蜂鳴器
ssh root@192.168.1.100 '/root/project/tone3 stop'

# 查看 LED 狀態
curl http://192.168.1.100:8080/state | python3 -m json.tool
```

## GPIO 注意事項

| LED | 實體顏色 | 設備樹名稱 | 路徑 |
|-----|---------|-----------|------|
| usr_led1 | 綠 | usr_led1 | `/sys/class/leds/usr_led1/brightness` |
| usr_led2 | 綠 | usr_led2 | `/sys/class/leds/usr_led2/brightness` |
| led_r | **綠色** | led_r | `/sys/class/leds/led_r/brightness` |
| led_g | **藍色** | led_g | `/sys/class/leds/led_g/brightness` |
| led_b | **紅色** | led_b | `/sys/class/leds/led_b/brightness` |
| 蜂鳴器 | - | - | `/sys/class/gpio/gpio117/value` |

**重要**：設備樹中 RGB LED 顏色標籤是**錯誤**的（r=物理綠，g=藍，b=紅）。亮度寫 `255` 不是 `1`。

## 技術棧

- **前端**：靜態 HTML/CSS/JavaScript（無框架）
- **後端**：Python 2.7 (BaseHTTPServer)
- **蜂鳴器**：C (GCC 4.6.3, `-std=gnu99`)
- **開發板**：MYIR Z-Turn (Zynq-7020, ARM Cortex-A9, Ubuntu 12.04)
