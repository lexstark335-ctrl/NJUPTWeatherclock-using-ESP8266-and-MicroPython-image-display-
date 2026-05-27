import network
import urequests
import ujson
import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import framebuf

# --- 用户配置区 ---
WIFI_SSID = "REDMIK80"
WIFI_PASS = "12345678"
API_KEY = "SShQ33Sz64M3TwJmE"
LOCATION = "nanjing"

# --- 初始化 OLED (使用你测试成功的 14 和 2 引脚) ---
i2c = I2C(scl=Pin(14), sda=Pin(2), freq=100000)
display = SSD1306_I2C(128, 64, i2c)

# 获取 STA 模式的 WiFi 对象
wlan = network.WLAN(network.STA_IF)

# --- 8x8 精确天气图标点阵数据 ---
# 晴天图标 (太阳)
icon_sunny = bytearray([0x1c, 0x5d, 0x3e, 0x7f, 0x7f, 0x3e, 0xba, 0x38])

# 饱满小乌云图标 (用于 Cloudy / Overcast / Foggy / Haze)
icon_cloudy = bytearray([
    0x00,  # 00000000
    0x0c,  # 00001100
    0x1e,  # 00011110
    0x7f,  # 01111111
    0xff,  # 11111111
    0xff,  # 11111111
    0xfe,  # 11111110
    0x00   # 00000000
])

# 雨天图标 (雨滴)
icon_rain = bytearray([0x00, 0x1c, 0x3e, 0x3e, 0x7f, 0x22, 0x44, 0x00])

def draw_weather_icon(weather_str, x, y):
    """根据天气文本在指定位置 (x, y) 绘制并放大两倍图标"""
    w_lower = weather_str.lower()
    
    # 匹配天气关键词
    if "sun" in w_lower or "clear" in w_lower:
        bits = icon_sunny
    # 已加入 fog 和 haze 触发：当返回天气包含大雾或霾时，同样显示小乌云图标
    elif "cloud" in w_lower or "overcast" in w_lower or "fog" in w_lower or "haze" in w_lower:
        bits = icon_cloudy  
    elif "rain" in w_lower or "shower" in w_lower or "storm" in w_lower:
        bits = icon_rain
    else:
        # 默认未知天气显示一个小方块
        bits = bytearray([0xff, 0x81, 0x81, 0x81, 0x81, 0x81, 0x81, 0xff])
        
    # 将 bytearray 转换为图形缓存
    fb = framebuf.FrameBuffer(bits, 8, 8, framebuf.MONO_HLSB)
    
    # 放大两倍显示（8x8 变 16x16 像素）
    for i in range(8):
        for j in range(8):
            if fb.pixel(j, i):
                display.fill_rect(x + j*2, y + i*2, 2, 2, 1)

def connect_wifi():
    wlan.active(True)
    if not wlan.isconnected():
        display.fill(0)
        display.text('Connecting WiFi..', 0, 10)
        display.text(WIFI_SSID, 0, 30)
        display.show()
        print('Connecting to network...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            
    if wlan.isconnected():
        display.fill(0)
        display.text('WiFi Connected!', 0, 20)
        display.show()
        print('Network config:', wlan.ifconfig())
        time.sleep(1)
        return True
    else:
        print('WiFi connection timeout!')
        return False

def fetch_weather():
    if not wlan.isconnected():
        print("WiFi disconnected! Reconnecting...")
        if not connect_wifi():
            return "WiFi Error", "--"

    url = "http://api.seniverse.com/v3/weather/now.json?key=" + API_KEY + "&location=" + LOCATION + "&language=en&unit=c"
    response = None
    try:
        print("Fetching weather data...")
        response = urequests.get(url)
        parsed_data = ujson.loads(response.text)
        
        now = parsed_data['results'][0]['now']
        weather_text = now['text']
        temperature = now['temperature']
        
        response.close() 
        return weather_text, temperature
    except Exception as e:
        print("Error fetching data:", e)
        if response:
            try: response.close()
            except: pass
        return "Fetch Error", "--"

def update_display(weather, temp):
    w_str = str(weather)
    t_str = str(temp)
    
    display.fill(0) # 清屏
    
    # 顶部栏
    display.text("CITY: " + LOCATION.upper(), 0, 0)
    display.hline(0, 12, 128, 1) 
    
    # 左侧文字
    display.text("Weather:", 0, 22)
    display.text(w_str, 0, 34)
    display.text("Temp: " + t_str + " C", 0, 52)
    
    # 右侧图标位置 (x=96, y=24)
    if "Error" not in w_str:
        draw_weather_icon(w_str, 96, 24)
    
    display.show()
    print("[OLED] Display update complete.")

# --- 主逻辑 ---
def main():
    connect_wifi()
    
    while True:
        w_text, temp = fetch_weather()
        update_display(w_text, temp)
        
        if "Error" in w_text or temp == "--":
            print("Fetch failed. Retry in 5 seconds...")
            time.sleep(5)
        else:
            print("Success. Wait for 10 minutes...")
            time.sleep(600) 

if __name__ == '__main__':
    main()
