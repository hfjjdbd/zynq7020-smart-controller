#!/usr/bin/python
import BaseHTTPServer
import os
import struct

PORT = 8080

LED_MAP = {
    'usr_led1': '/sys/class/leds/usr_led1/brightness',
    'usr_led2': '/sys/class/leds/usr_led2/brightness',
    'led_r': '/sys/class/leds/led_r/brightness',
    'led_g': '/sys/class/leds/led_g/brightness',
    'led_b': '/sys/class/leds/led_b/brightness',
}

def set_led(name, value):
    path = LED_MAP.get(name)
    if path:
        try:
            with open(path, 'w') as f:
                f.write('255' if value else '0')
            return True
        except:
            return False
    return False

def get_led(name):
    path = LED_MAP.get(name)
    if path:
        try:
            with open(path, 'r') as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def set_buzzer(freq):
    try:
        if freq == 0:
            os.system('/root/project/tone3 0')
        else:
            os.system('/root/project/tone3 ' + str(freq) + ' 500')
        return True
    except:
        return False

def build_html(led_cards, ip, port):
    buzzers = [
        ('262', 'C4 (262Hz)', '#a29bfe', 'white'),
        ('294', 'D4 (294Hz)', '#74b9ff', '#333'),
        ('330', 'E4 (330Hz)', '#55efc4', '#333'),
        ('349', 'F4 (349Hz)', '#ffeaa7', '#333'),
        ('392', 'G4 (392Hz)', '#fab1a0', '#333'),
        ('440', 'A4 (440Hz)', '#fdcb6e', '#333'),
        ('494', 'B4 (494Hz)', '#e17055', '#333'),
        ('523', 'C5 (523Hz)', '#d63031', 'white'),
        ('880', 'A5 (880Hz)', '#00b894', 'white'),
    ]
    buzzer_html = ''
    for freq, label, bg, fg in buzzers:
        buzzer_html += '<div style="margin-top:10px"><a onclick="cmd(\'/buzzer?freq=' + freq + '\');return false;" href="#" class="btn btn-buzz" style="background:' + bg + ';color:' + fg + '">' + label + '</a></div>'
    buzzer_html += '<div style="margin-top:10px"><a onclick="cmd(\'/buzzer?freq=0\');return false;" href="#" class="btn btn-buzz" style="background:#636e72;color:white">STOP</a></div>'

    return '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ZYNQ7020 Smart Controller</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Arial,sans-serif;background:#1a1a2e;color:#eee;min-height:100vh;padding:20px}h1{text-align:center;margin-bottom:30px;color:#00d4ff;font-size:24px}.section{background:#16213e;border-radius:12px;padding:20px;margin-bottom:20px}.section h2{color:#00d4ff;margin-bottom:15px;font-size:18px}.led-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px}.led-card{background:#0f3460;border-radius:10px;padding:15px;text-align:center}.led-card .name{font-size:14px;margin-bottom:8px}.led-card .dot{width:40px;height:40px;border-radius:50%;margin:0 auto 10px;border:2px solid #333;transition:all .3s}.led-card .dot.on{box-shadow:0 0 20px currentColor}.btn{padding:10px 20px;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:bold;transition:all .2s;display:inline-block;text-decoration:none}.btn:active{transform:scale(.95)}.btn-on{background:#00b894;color:white}.btn-off{background:#d63031;color:white}.btn-buzz{background:#fdcb6e;color:#333;width:100%;padding:15px;font-size:16px;text-align:center}.auto-refresh{text-align:center;margin-top:10px;color:#666;font-size:12px}</style><script>var colors={"usr_led1":"#44ff44","usr_led2":"#44ff44","led_r":"#44ff44","led_g":"#4444ff","led_b":"#ff4444"};function cmd(url){var x=new XMLHttpRequest();x.open("GET",url,true);x.send()}function toggleLed(name,val){var dot=document.getElementById("dot-"+name);if(val=="1"){dot.style.background=colors[name];dot.style.color=colors[name];dot.className="dot on"}else{dot.style.background="#333";dot.className="dot"}}</script></head><body><h1>ZYNQ7020 Smart Controller</h1><div class="section"><h2>LED Control</h2><div class="led-grid">' + led_cards + '</div></div><div class="section"><h2>Buzzer Control</h2>' + buzzer_html + '</div><div class="auto-refresh">IP: ' + ip + ':' + str(port) + '</div></body></html>'

class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            led_cards = ''
            colors = {'usr_led1': '#44ff44', 'usr_led2': '#44ff44', 'led_r': '#44ff44', 'led_g': '#4444ff', 'led_b': '#ff4444'}
            labels = {'usr_led1': 'LED1', 'usr_led2': 'LED2', 'led_r': 'Green', 'led_g': 'Blue', 'led_b': 'Red'}
            for name in LED_MAP:
                state = get_led(name)
                color = colors.get(name, '#fff')
                on_class = 'on' if state else ''
                bg = color if state else '#333'
                led_cards += '<div class="led-card"><div class="name">' + labels.get(name, name) + '</div><div class="dot ' + on_class + '" id="dot-' + name + '" style="background:' + bg + ';color:' + color + '"></div><div class="btn-group"><a onclick="cmd(\'/led?name=' + name + '&val=1\');toggleLed(\'' + name + '\',\'1\');return false;" href="#" class="btn btn-on">ON</a><a onclick="cmd(\'/led?name=' + name + '&val=0\');toggleLed(\'' + name + '\',\'0\');return false;" href="#" class="btn btn-off">OFF</a></div></div>'
            html = build_html(led_cards, self.client_address[0], PORT)
            self.wfile.write(html)
        elif self.path.startswith('/led?'):
            params = self.path.split('?')[1]
            d = dict(p.split('=') for p in params.split('&'))
            name = d.get('name', '')
            val = int(d.get('val', 0))
            set_led(name, val)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write('{"ok":true}')
        elif self.path.startswith('/buzzer?'):
            params = self.path.split('?')[1]
            d = dict(p.split('=') for p in params.split('&'))
            freq = int(d.get('freq', 0))
            set_buzzer(freq)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write('{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

print 'Starting server on port ' + str(PORT) + '...'

try:
    f = open('/sys/bus/platform/drivers/gpio-beeper/unbind', 'w')
    f.write('gpio-beep.3')
    f.close()
    print 'gpio-beeper driver unbound'
except:
    print 'gpio-beeper already unbound'

try:
    f = open('/sys/class/gpio/export', 'w')
    f.write('117')
    f.close()
except:
    pass
try:
    f = open('/sys/class/gpio/gpio117/direction', 'w')
    f.write('out')
    f.close()
except:
    pass

for name in LED_MAP:
    try:
        f = open('/sys/class/leds/' + name + '/trigger', 'w')
        f.write('none')
        f.close()
    except:
        pass

print 'Open http://192.168.1.100:' + str(PORT) + ' in browser'
server = BaseHTTPServer.HTTPServer(('0.0.0.0', PORT), Handler)
server.serve_forever()
