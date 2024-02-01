from datetime import datetime
import time
import socketio
from bleak import BleakScanner, BleakClient
import asyncio

MODEL_NUMBER_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
HR_GOAL = 120
HR_GOAL_TIME_SEC = 20

socket = socketio.Client() 
socket.connect('http://127.0.0.1:7777')

bleak_client = None
hrGoalTime = HR_GOAL_TIME_SEC
goal_start_time = 0
print_time = time.time()
payout = False

def hr_capture(sender, data):
   global hrGoalTime
   global goal_start_time
   global print_time
   global payout

   hrFormat = data[0] & 0x01
   hrValue = 0
   if hrFormat == 1:
      hrValue = (data[1] & 0xFF) + (data[2] << 8)
   else:
      hrValue = data[1] & (0x0000FFFF if hrFormat == 1 else 0x000000FF)

   if hrValue >= HR_GOAL and goal_start_time == 0:
      goal_start_time = time.time()
   elif hrValue >= HR_GOAL:
      hrGoalTime = HR_GOAL_TIME_SEC - (time.time() - goal_start_time)
   elif hrValue < HR_GOAL:
      goal_start_time = 0
      hrGoalTime = HR_GOAL_TIME_SEC

   if hrGoalTime <= 0:
      payout = True
      hrGoalTime = HR_GOAL_TIME_SEC
      goal_start_time = time.time()

   if (time.time() - print_time) >= 1:
      print_time = time.time()
      print("HR {}, Countdown {:.2f}, Goal HR {}, Goal Time {}".format(hrValue, hrGoalTime, HR_GOAL, HR_GOAL_TIME_SEC))

async def capture():
   global payout

   discovered_devices = await BleakScanner.discover()
   bleak_client = None

   for device in discovered_devices:
      print (device.name)
      if device.name is not None and "Polar" in device.name:
         bleak_client = BleakClient(device)
         await bleak_client.connect()
      if bleak_client != None:
         break

   if bleak_client == None:
      print("No devices found")
      quit()

   print(await bleak_client.read_gatt_char(MODEL_NUMBER_UUID))

   await bleak_client.start_notify(HR_MEASUREMENT_UUID, hr_capture)

   print ("Collecting...")
   while True:
      if payout == True:
         payout = False
         print("Payout time")
         socket.emit('make_payment', { 'message': "well done" })
      await asyncio.sleep(1)

   await bleak_client.disconnect()

asyncio.run(capture())