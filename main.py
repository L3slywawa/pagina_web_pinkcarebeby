
# =============================
# ESP32 + MAX30102 + MLX90614 + Web + LCD 16x2
# =============================
import network
import socket
import machine
import time
import math
from machine import SoftI2C, I2C, Pin

# -----------------------------
# Configuración Wi‑Fi
# -----------------------------
SSID = "PANIFICADORA SANTA CRUZ ZAC"
PASSWORD = "SantacruzZac19"

# -----------------------------
# Buzzer (PWM en GPIO 27)
# -----------------------------
buzzer = machine.PWM(machine.Pin(27), freq=1000, duty=0)

def play_tone(freq, duration):
    buzzer.freq(freq)
    buzzer.duty(512)
    time.sleep(duration)
    buzzer.duty(0)

def play_melody(melody):
    for freq, dur in melody:
        buzzer.freq(freq)
        buzzer.duty(512)
        time.sleep(dur)
        buzzer.duty(0)
        time.sleep(0.05)

alarm_melody     = [(1000, 0.3), (800, 0.3), (1000, 0.3)]
christmas_melody = [(523, 0.3), (587, 0.3), (659, 0.3), (523, 0.3)]
police_melody    = [(1000, 0.2), (1500, 0.2)] * 5

# -----------------------------
# LCD 16x2 - Pines y clase
# -----------------------------
LCD_RS = Pin(15, Pin.OUT)
LCD_EN = Pin(2,  Pin.OUT)
LCD_D4 = Pin(4,  Pin.OUT)
LCD_D5 = Pin(18, Pin.OUT)
LCD_D6 = Pin(19, Pin.OUT)
LCD_D7 = Pin(5,  Pin.OUT)

class LCD1602:
    def __init__(self, rs, en, d4, d5, d6, d7):
        self.rs = rs; self.en = en
        self.data_pins = [d4, d5, d6, d7]
        self._init_pins()
        time.sleep_ms(50)
        self._init_lcd()

    def _init_pins(self):
        self.rs.init(Pin.OUT); self.en.init(Pin.OUT)
        for p in self.data_pins: p.init(Pin.OUT)

    def _pulse(self):
        self.en.value(0); time.sleep_us(1)
        self.en.value(1); time.sleep_us(1)
        self.en.value(0); time.sleep_us(100)

    def _nibble(self, d):
        # Enviar 4 bits, LSB->MSB a los pines D4..D7
        for i, p in enumerate(self.data_pins):
            p.value((d >> i) & 1)
        self._pulse()

    def _byte(self, d, mode):
        # mode=0 comando, mode=1 datos
        self.rs.value(mode)
        self._nibble(d >> 4)
        self._nibble(d & 0x0F)

    def _init_lcd(self):
        self.rs.value(0)
        for _ in range(3):
            self._nibble(0x03)
            time.sleep_ms(5)
        self._nibble(0x02)            # 4-bit
        self._byte(0x28, 0)           # 2 líneas, 5x8
        self._byte(0x0C, 0)           # Display ON
        self._byte(0x06, 0)           # Cursor inc
        self.clear()

    def clear(self):
        self._byte(0x01, 0)
        time.sleep_ms(2)

    def set_cursor(self, col, row):
        addr = 0x80 + (row * 0x40) + col
        self._byte(addr, 0)

    def print_str(self, s):
        # Enviar exactamente lo que llega (máx 16 caracteres por línea)
        for ch in s[:16]:
            self._byte(ord(ch), 1)

lcd = LCD1602(LCD_RS, LCD_EN, LCD_D4, LCD_D5, LCD_D6, LCD_D7)

# ---------- Helper para rellenar/recortar a 16 chars (sin str.ljust) ----------
def pad(s, length=16):
    """Rellena con espacios o recorta a 'length' caracteres (compat. MicroPython)."""
    if s is None:
        s = ""
    L = len(s)
    if L < length:
        return s + (" " * (length - L))
    else:
        return s[:length]

# ---------- Mostrar HR, SpO2 y Temp en LCD ----------
def display_vitals(bpm, spo2, temp_c, alarm_active):
    """
    Línea 1: HR y SpO2  (ej. 'HR:75 SpO2:97%')
    Línea 2: Temp y estado (ej. 'Temp:36.8C Normal')
    Si alarma: pantalla de alerta.
    """
    lcd.clear()

    if alarm_active:
        lcd.set_cursor(0, 0); lcd.print_str(pad("  ALARMA ACTIVA ", 16))
        lcd.set_cursor(0, 1); lcd.print_str(pad("  REVISE AL BEBE", 16))
        return

    # Formateo seguro
    hr_txt = "--"   if bpm    is None else "{:0.0f}".format(bpm)
    sp_txt = "--"   if spo2   is None else "{:0.0f}".format(spo2)
    tp_txt = "--.-" if temp_c is None else "{:0.1f}".format(temp_c)

    # Línea 1 (máx 16)
    line1 = "{}bpm SpO2:{}%".format(hr_txt, sp_txt)
    lcd.set_cursor(0, 0); lcd.print_str(pad(line1, 16))

    # Clasificación breve de temperatura
    temp_cat_short = latest_temp_cat
    if temp_cat_short == "sin dato": temp_cat_short = "Sin dato"
    elif temp_cat_short == "normal": temp_cat_short = "Normal"
    elif temp_cat_short == "baja":   temp_cat_short = "Baja"
    elif temp_cat_short == "alta":   temp_cat_short = "Alta"

    # Línea 2 (máx 16)
    line2 = "Temp:{}C {}".format(tp_txt, temp_cat_short)
    lcd.set_cursor(0, 1); lcd.print_str(pad(line2, 16))

# -----------------------------
# MAX30102 (HR/SpO2) en SoftI2C (GPIO 21/22)
# -----------------------------
i2c_hr = SoftI2C(sda=Pin(21), scl=Pin(22), freq=100000)
MAX30102_ADDR = 0x57

REG_INTR_STATUS_1 = 0x00
REG_INTR_STATUS_2 = 0x01
REG_INTR_ENABLE_1 = 0x02
REG_INTR_ENABLE_2 = 0x03
REG_FIFO_WR_PTR   = 0x04
REG_FIFO_OVF_CNT  = 0x05
REG_FIFO_RD_PTR   = 0x06
REG_FIFO_DATA     = 0x07
REG_FIFO_CONFIG   = 0x08
REG_MODE_CONFIG   = 0x09
REG_SPO2_CONFIG   = 0x0A
REG_LED1_PA       = 0x0C
REG_LED2_PA       = 0x0D

def _w(reg, val): i2c_hr.writeto_mem(MAX30102_ADDR, reg, bytes([val]))
def _r(reg, n=1): return i2c_hr.readfrom_mem(MAX30102_ADDR, reg, n)

def max30102_init():
    _w(REG_MODE_CONFIG, 0x40); time.sleep_ms(100)
    _w(REG_FIFO_WR_PTR, 0x00); _w(REG_FIFO_RD_PTR, 0x00); _w(REG_FIFO_OVF_CNT, 0x00)
    _w(REG_INTR_ENABLE_1, 0xC0); _w(REG_INTR_ENABLE_2, 0x00)
    _w(REG_FIFO_CONFIG, 0x4F)     # avg=4, rollover=1, afull=15
    _w(REG_SPO2_CONFIG, 0x27)     # ADC 2048, SR=100Hz, PW=411us
    _w(REG_LED1_PA, 0x24); _w(REG_LED2_PA, 0x24)
    _w(REG_MODE_CONFIG, 0x03)     # modo SpO2
    time.sleep_ms(50)

def read_sample_pair():
    data = _r(REG_FIFO_DATA, 6)
    red = ((data[0] << 16) | (data[1] << 8) | data[2]) & 0x3FFFF
    ir  = ((data[3] << 16) | (data[4] << 8) | data[5]) & 0x3FFFF
    return red, ir

# -----------------------------
# MLX90614 (Temperatura bebé) en I2C(0) (GPIO 33/32)
# -----------------------------
mlx_i2c  = I2C(0, scl=Pin(33), sda=Pin(32), freq=100000)
MLX_ADDR = 0x5A

def mlx_read_temp_reg(reg):
    try:
        data = mlx_i2c.readfrom_mem(MLX_ADDR, reg, 3)
        raw  = data[0] | (data[1] << 8)
        if raw == 0xFFFF or raw == 0x0000:
            return None
        return (raw * 0.02) - 273.15
    except Exception:
        return None

def read_temp_obj(): return mlx_read_temp_reg(0x07)  # Objeto (piel)
def read_temp_amb(): return mlx_read_temp_reg(0x06)  # Ambiente (opcional)

# -----------------------------
# Umbrales temperatura (bebé)
# -----------------------------
TEMP_LOW_C      = 35.0
TEMP_NORMAL_MAX = 37.5
TEMP_HIGH_C     = 38.0

# -----------------------------
# Estado / buffers HR-SpO2
# -----------------------------
dc_red = None; dc_ir = None
SR = 100; WINDOW_SEC = 5; N = SR * WINDOW_SEC
red_ac_buf = []; ir_ac_buf  = []
last_peak_time = None; peak_times = []

latest_bpm       = None
latest_spo2      = None
latest_hr_cat    = "sin dato"
latest_spo2_cat  = "sin dato"
latest_temp_c    = None
latest_temp_cat  = "sin dato"

_last_print_ms   = time.ticks_ms()
_last_display_ms = time.ticks_ms()
alarm_active     = False

# -----------------------------
# Alarma
# -----------------------------
def trigger_alarm():
    global alarm_active
    if not alarm_active:
        alarm_active = True
        buzzer.freq(1000)
        buzzer.duty(512)

def clear_alarm():
    global alarm_active
    if alarm_active:
        buzzer.duty(0)
        alarm_active = False

# -----------------------------
# Procesamiento HR/SpO2
# -----------------------------
def update_dc_ac(red, ir, alpha=0.95):
    global dc_red, dc_ir
    if dc_red is None:
        dc_red, dc_ir = red, ir
    else:
        dc_red = alpha*dc_red + (1-alpha)*red
        dc_ir  = alpha*dc_ir  + (1-alpha)*ir
    return red - dc_red, ir - dc_ir, dc_red, dc_ir

def detect_peak(ac_val, thresh=500.0, refractory_ms=300):
    global last_peak_time
    now = time.ticks_ms()
    if abs(ac_val) > thresh:
        if last_peak_time is None or time.ticks_diff(now, last_peak_time) > refractory_ms:
            last_peak_time = now
            peak_times.append(now)
            if len(peak_times) > 10:
                del peak_times[0]

def estimate_bpm():
    if len(peak_times) < 2: return None
    intervals = []
    for i in range(1, len(peak_times)):
        dt = time.ticks_diff(peak_times[i], peak_times[i-1])
        if 300 <= dt <= 2000: intervals.append(dt)  # 30–200 BPM
    if not intervals: return None
    avg_ms = sum(intervals) / len(intervals)
    return 60000.0 / avg_ms

def _rms(values):
    if not values: return 0.0
    s = 0.0
    for v in values: s += v*v
    return math.sqrt(s/len(values))

def estimate_spo2(red_ac_buf, ir_ac_buf, dc_red, dc_ir):
    if not dc_red or not dc_ir: return None
    ac_red_rms = _rms(red_ac_buf); ac_ir_rms  = _rms(ir_ac_buf)
    if ac_red_rms <= 0 or ac_ir_rms <= 0: return None
    R = (ac_red_rms/dc_red) / (ac_ir_rms/dc_ir)
    spo2 = -45.060*(R**2) + 30.354*R + 94.845
    if spo2 < 70 or spo2 > 100.5: return None
    return spo2

# -----------------------------
# Clasificación (y alarma)
# -----------------------------
def classify_spo2(spo2):
    # Manteniendo tus límites:
    if spo2 is None:      return "sin dato"
    if spo2 <= 70:        trigger_alarm(); return "SpO2 baja"
    if spo2 >= 71:        clear_alarm();   return "normal"
    clear_alarm();        return "SpO2 alta"

def classify_hr(bpm):
    if bpm is None:       return "sin dato"
    if bpm < 60:          trigger_alarm(); return "bpm baja"
    elif bpm <= 160:      clear_alarm();   return "normal"
    else:                 trigger_alarm(); return "bpm alta"

def classify_temp(temp_c):
    if temp_c is None:    return "sin dato"
    if temp_c < TEMP_LOW_C:
        trigger_alarm();  return "baja"
    elif temp_c >= TEMP_HIGH_C:
        trigger_alarm();  return "alta"
    elif temp_c <= TEMP_NORMAL_MAX:
        clear_alarm();    return "normal"
    else:
        clear_alarm();    return "normal"  # subfebril

# -----------------------------
# Actualización de temperatura
# -----------------------------
def update_temperature():
    global latest_temp_c, latest_temp_cat
    t = read_temp_obj()           # MLX90614 objeto (piel)
    latest_temp_c   = t
    latest_temp_cat = classify_temp(t)

# -----------------------------
# Loop de actualización (HR/SpO2/Temp + LCD)
# -----------------------------
def update_vitals():
    global latest_bpm, latest_spo2, latest_hr_cat, latest_spo2_cat, _last_print_ms, _last_display_ms
    try:
        # HR/SpO2 (llenar buffers)
        for _ in range(5):
            red, ir = read_sample_pair()
            red_ac, ir_ac, cur_dc_red, cur_dc_ir = update_dc_ac(red, ir, alpha=0.95)
            red_ac_buf.append(red_ac); ir_ac_buf.append(ir_ac)
            if len(red_ac_buf) > N: del red_ac_buf[0]
            if len(ir_ac_buf)  > N: del ir_ac_buf[0]
            detect_peak(ir_ac, thresh=500.0)

        # Temperatura
        update_temperature()

        # Reporte cada ~1 s
        now = time.ticks_ms()
        if time.ticks_diff(now, _last_print_ms) >= 1000:
            bpm  = estimate_bpm()
            spo2 = estimate_spo2(red_ac_buf, ir_ac_buf, cur_dc_red, cur_dc_ir)
            latest_bpm      = bpm
            latest_spo2     = spo2
            latest_hr_cat   = classify_hr(bpm)
            latest_spo2_cat = classify_spo2(spo2)

            bstr = "--" if bpm  is None else f"{bpm:5.1f}"
            sstr = "--" if spo2 is None else f"{spo2:5.1f}"
            tstr = "--" if latest_temp_c is None else f"{latest_temp_c:4.2f}"
            print(f"HR: {bstr} bpm ({latest_hr_cat}) | SpO2: {sstr}% ({latest_spo2_cat}) | Temp: {tstr} °C ({latest_temp_cat})")
            _last_print_ms = now

        # Actualiza LCD cada ~1 s
        if time.ticks_diff(now, _last_display_ms) >= 1000:
            display_vitals(latest_bpm, latest_spo2, latest_temp_c, alarm_active)
            _last_display_ms = now

    except OSError as e:
        print("Error I2C:", e, "→ Reinicializando MAX30102")
        max30102_init()
        time.sleep_ms(50)

# -----------------------------
# JSON para /vitals (incluye temp)
# -----------------------------
def vitals_json():
    b = "null" if latest_bpm  is None else f"{latest_bpm:.1f}"
    s = "null" if latest_spo2 is None else f"{latest_spo2:.1f}"
    t = "null" if latest_temp_c is None else f"{latest_temp_c:.2f}"
    return ('{"hr":' + b +
            ',"hr_cat":"' + latest_hr_cat +
            '","spo2":' + s +
            ',"spo2_cat":"' + latest_spo2_cat +
            '","temp":' + t +
            ',"temp_cat":"' + latest_temp_cat + '"}')

# -----------------------------
# Conexión Wi‑Fi
# -----------------------------
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando a WiFi...")
    while not wlan.isconnected():
        time.sleep(0.5)
    print("Conectado:", wlan.ifconfig())
    # Mostrar IP en LCD (opcional)
    ip = wlan.ifconfig()[0]
    lcd.clear(); lcd.set_cursor(0, 0); lcd.print_str(pad("WiFi Conectado", 16))
    lcd.set_cursor(0, 1); lcd.print_str(pad(ip[:16], 16))
    time.sleep(2)
    return ip

# -----------------------------
# Servidor HTTP (CORS)
# -----------------------------
def start_server(ip):
    max30102_init()
    lcd.clear(); lcd.set_cursor(0, 0); lcd.print_str(pad("Servidor Activo", 16))
    lcd.set_cursor(0, 1); lcd.print_str(pad("Esperando datos", 16))
    time.sleep(1)

    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.bind(addr); s.listen(1); s.settimeout(0.1)
    print("Servidor escuchando en http://{}:80".format(ip))

    while True:
        update_vitals()

        try:
            cl, addr = s.accept()
        except OSError:
            continue

        try:
            request = cl.recv(1024).decode()

            if "GET /buzzer" in request:
                if "state=on1" in request:   play_melody(alarm_melody)
                elif "state=on2" in request: play_melody(christmas_melody)
                elif "state=on3" in request: play_melody(police_melody)
                elif "state=stop" in request: buzzer.duty(0); clear_alarm()
                cl.send("HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/plain\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "Cache-Control: no-store\r\n"
                        "\r\nOK")

            elif "GET /vitals" in request:
                payload = vitals_json()
                cl.send("HTTP/1.1 200 OK\r\n"
                        "Content-Type: application/json\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "Cache-Control: no-store\r\n"
                        "\r\n" + payload)

            else:
                cl.send("HTTP/1.1 404 Not Found\r\n"
                        "Access-Control-Allow-Origin: *\r\n"
                        "\r\n")
        finally:
            cl.close()

# -----------------------------
# Ejecuta
# -----------------------------
try:
    ip = connect_wifi()
    start_server(ip)
except Exception as e:
    print("Error crítico:", e)
    lcd.clear(); lcd.set_cursor(0, 0); lcd.print_str(pad("Error del sist.", 16))
    lcd.set_cursor(0, 1); lcd.print_str(pad("Reinicie", 16))
