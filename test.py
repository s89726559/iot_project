import paho.mqtt.client as mqtt
import random
import json  
import datetime 
import time

import seeed_si114x
import signal

import RPi.GPIO as GPIO

import threading


GPIO.setup(18, GPIO.OUT, initial=GPIO.HIGH)
SI1145 = seeed_si114x.grove_si114x()
clientForceEnable="off"
clientForce="off"
example="none"
autoSwitchEnable="off"
timeSwitchEnable="off"
startTime=datetime
endTime=datetime

# 設置日期時間的格式
ISOTIMEFORMAT = '%m/%d %H:%M:%S'

# 連線設定
# 初始化地端程式
client = mqtt.Client()

# 設定連線資訊(IP, Port, 連線時間)
client.connect("test.mosquitto.org", 1883, 60)

#連線後訂閱client端會發佈的主題
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("00757136clientForce")
    print("ok1")
    client.subscribe("00757136example")
    print("ok2")
    client.subscribe("00757136autoSwitch")
    print("ok3")
    client.subscribe("00757136timeSwitch")
    print("ok4")
    client.subscribe("00757136startTime")
    print("ok5")
    client.subscribe("00757136endTime")
    print("ok6")
    client.subscribe("00757136clientRefresh")
    print("ok7")
    client.subscribe("00757136clientForceEnable")
    print("ok8")

# 設定連線的動作
client.on_connect = on_connect

#發佈目前的狀態給用戶
def refresh_pub():
    if GPIO.input(18) == GPIO.HIGH:
        client.publish("00757136testOnOff", "off")
        print("pub 00757136testOnOff off")
    if GPIO.input(18)== GPIO.LOW:
        client.publish("00757136testOnOff", "on")
        print("pub 00757136testOnOff on")
    client.publish("00757136testVis", str(SI1145.ReadVisible))
    print("pub 00757136testVis %s"%(str(SI1145.ReadVisible)))


def handler(signalnum, handler):
    print("Please use Ctrl C to quit")
    
    
#確認是否開啟自動判斷
def autoCheck():
    global autoSwitchEnable
    
    print("auto check")
    threshold=262 #auto的閥值
    if autoSwitchEnable == "on":
        print("autoSwitchEnable: on")
        GPIO.output(18,GPIO.HIGH)
        if SI1145.ReadVisible>=threshold:
            GPIO.output(18,GPIO.HIGH)
        elif SI1145.ReadVisible<threshold:
            GPIO.output(18,GPIO.LOW)
    elif autoSwitchEnable=="off":
        print("autoSwitchEnable: off")
        GPIO.output(18,GPIO.HIGH)
    
    
#確認是否開啟定時
def timeCheck():
    global timeSwitchEnable
    global startTime
    global endTime

    print("time check")
    if timeSwitchEnable == "on":
        print("timeSwitchEnable: on")
        try:
            now=datetime.datetime.now()
            if endTime.time() < startTime.time():
                print("m1")   #設定的時間段有經過半夜十二點
                if now.time()>=startTime.time() and now.time()<=datetime.time.max:
                    print("已到設定的時間-開燈")
                    GPIO.output(18,GPIO.LOW)
                elif now.time()>=datetime.time.min and now.time()<=endTime.time():
                    print("已到設定的時間-開燈")
                    GPIO.output(18,GPIO.LOW)
                else:
                    print("不在設定的時間範圍內-關燈")
                    GPIO.output(18,GPIO.HIGH)
                    autoCheck()
            elif endTime.time() > startTime.time():
                print("m2")   #設定的時間段沒經過半夜12點
                if now.time()>=startTime.time() and now.time()<=endTime.time():
                    print("已到設定的時間-開燈")
                    GPIO.output(18,GPIO.LOW)
                else:
                    print("不在設定的時間範圍內-關燈")
                    GPIO.output(18,GPIO.HIGH)
                    autoCheck()
        except Exception as e:
            print("%s"%(e))
        
    elif timeSwitchEnable == "off":
        print("timeSwitchEnable: off")
        autoCheck()
    
#判斷是否套用範本 範本設定為菊花，根據一些資料得知在台灣實施菊花照光會選在晚上十點開始，照光三到四小時
def exampleCheck():
    global example
    global startTime
    global endTime
    
    print("example check")
    if example=="none":
        timeCheck()
    elif example=="example1":
        print("using example1")
        #設定晚上十點至凌晨二點，照光四小時
        try:
            startTime=datetime.datetime.strptime("22-00","%H-%M")
            print("start= %s"%(startTime))
            endTime=datetime.datetime.strptime("2-00","%H-%M")
            print("end= %s"%(endTime))
            timeCheck()
        except Exception as e:
            print("%s"%(e))
    
    
#確認是否強制開關
def forceCheck():    
    global clientForceEnable
    global clientForce
    
    print("force check")
    if clientForceEnable == "on":
        if clientForce=="on":
            GPIO.output(18,GPIO.LOW)
        elif clientForce=="off":
            GPIO.output(18,GPIO.HIGH)
    elif clientForceEnable == "off":  
        exampleCheck()
    
    
#主程式基本流程 判斷強制不強制->是否套用預設範本->定時不定時->自動不自動  結束後更新資訊(refresh_pub())
def main():
    #signal.signal(signal.SIGTSTP, handler) # Ctrl-z
    #signal.signal(signal.SIGQUIT, handler) # Ctrl-\
    print("main check")
    forceCheck()
    refresh_pub()
    #GPIO.cleanup()


#重複執行用
class TimerClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.event = threading.Event()

    def run(self):
        while not self.event.is_set():
            main()
            self.event.wait( 5 )  #每隔幾秒執行一次

    def stop(self):
        self.event.set()

tmr = TimerClass()
tmr.start()
#time.sleep( 10 )
#tmr.stop()


#收到訊息時的動作
def on_message(client, userdata, msg):
    msg.payload = msg.payload.decode("utf-8") #一定要先decode才能正常操作，否則會出錯 https://stackoverflow.com/questions/40922542/python-why-is-my-paho-mqtt-message-different-than-when-i-sent-it
    #debug
    print(msg.topic+" "+ msg.payload)
    global clientForceEnable
    global clientForce
    global example
    global autoSwitchEnable
    global timeSwitchEnable
    global startTime
    global endTime
    
    if msg.topic == "00757136clientRefresh":
        refresh_pub()
        
    if msg.topic == "00757136clientForceEnable":
        if str(msg.payload) == "on":
            clientForceEnable = "on"
            autoSwitchEnable="off"
            print("clientForceEnable %s"%(clientForceEnable))
        if str(msg.payload) == "off":
            clientForceEnable = "off"
            print("clientForceEnable %s"%(clientForceEnable))
            
    if msg.topic == "00757136clientForce":
        if str(msg.payload) == "on":
            clientForce="on"
        if str(msg.payload) == "off":
            clientForce="off"

    if msg.topic == "00757136example":
        if str(msg.payload) == "none":
            example="none"
        if str(msg.payload) == "example1":    
            example="example1"
            
    if clientForceEnable == "off":        
        if msg.topic == "00757136autoSwitch":
            if str(msg.payload) == "on":
                autoSwitchEnable="on"
            if str(msg.payload) == "off":
                autoSwitchEnable="off"
                
        if msg.topic == "00757136timeSwitch":
            if str(msg.payload) == "on":
                timeSwitchEnable="on"
            if str(msg.payload) == "off":
                timeSwitchEnable="off"
        if msg.topic == "00757136startTime":
            try:
                startTime=datetime.datetime.strptime(str(msg.payload),"%H-%M")
                print("start= %s"%(startTime))
            except Exception as e:
                print("%s"%(e))
        if msg.topic == "00757136endTime":
            try:
                endTime=datetime.datetime.strptime(str(msg.payload),"%H-%M")
                print("end= %s"%(endTime))
            except Exception as e:
                print("%s"%(e))
    
    main()
    refresh_pub()


# 設定接收訊息的動作
client.on_message = on_message
    
# 開始連線，執行設定的動作和處理重新連線問題
client.loop_forever()

#
if __name__  == '__main__':
    main()

#測試用 mosquitto_sub -h test.mosquitto.org -t 00757136testOnOff