
import paho.mqtt.client as mqtt
import sqlite3
import json
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

mqttc=mqtt.Client()
mqttc.connect("localhost",1883,60)
mqttc.loop_start()

# # Create a dictionary called pins to store the pin number, name, and pin state:
pins = {
   2 : {'name' : 'Tầng 2', 'board' : 'esp8266', 'topic' : 'esp8266/2', 'state' : 'Mở'},
   14 : {'name' : 'Tầng 2', 'board' : 'esp8266', 'topic' : 'esp8266/14', 'state' : 'Mở'},
   12 : {'name' : 'Tầng 1', 'board' : 'esp8266', 'topic' : 'esp8266/12', 'state' : 'Mở'},
   13 : {'name' : 'Tầng 1', 'board' : 'esp8266', 'topic' : 'esp8266/13', 'state' : 'Mở'},
   16 : {'name' : 'GPIO 16', 'board' : 'esp8266', 'topic' : 'esp8266/16', 'state' : 'Mở'},
   5 : {'name' : 'GPIO 5', 'board' : 'esp8266', 'topic' : 'esp8266/5', 'state' : 'Mở'},
   4 : {'name' : 'GPIO 4', 'board' : 'esp8266', 'topic' : 'esp8266/4', 'state' : 'Mở'},
   0 : {'name' : 'GPIO 0', 'board' : 'esp8266', 'topic' : 'esp8266/0', 'state' : 'Mở'}   
   }

# Put the pin dictionary into the template data dictionary:
templateData = {
   'pins' : pins
   }

def process_intent_slots(intent_slots): 
    intent_slots_dict = {}
    for item in intent_slots.split(', '):
        key, value = item.split(' : ')
        intent_slots_dict[key.strip()] = value.strip().strip("', {}")
    return intent_slots_dict
    last_intent = None

def on_message(client, userdata, message):
    global last_intent
    last_intent = message.payload.decode('utf-8')
    mqttc.on_message = on_message
    mqttc.subscribe("picovoice/intent", qos=1)


last_intent = None  # Initialize last_intent as None@app.route("/get_last_intent")
@app.route("/get_last_intent")
def get_last_intent():
        global last_intent
        intent = last_intent
        return jsonify({"intent": intent})


@app.route("/")
def main():
    # Lấy trạng thái từ cơ sở dữ liệu SQLite
    conn = sqlite3.connect('/home/pi/picovoice/database/ConnectLukatoWeb.db')
    cursor = conn.cursor()
    cursor.execute("SELECT pin_number, status FROM LightControl")
    db_data = cursor.fetchall()
    conn.close()

    # Cập nhật trạng thái từ cơ sở dữ liệu vào pins dictionary
    for row in db_data:
        pin_number, status = row
        pins[pin_number]['state'] = 'Mở' if status == 1 else 'Tắt'

    # truyền dữ liệu vào templateData trả về giao diện index.html
    return render_template('index.html', **templateData)


@app.route("/getdata", methods=["GET"])
def get_data():
    # Lấy trạng thái từ cơ sở dữ liệu SQLite
    conn = sqlite3.connect('/home/pi/picovoice/database/ConnectLukatoWeb.db')
    cursor = conn.cursor()
    cursor.execute("SELECT pin_number, status FROM LightControl")
    db_data = cursor.fetchall()
    conn.close()

    # Cập nhật trạng thái từ cơ sở dữ liệu vào pins dictionary
    for row in db_data:
        pin_number, status = row
        pins[pin_number]['state'] = 'Mở' if status == 1 else 'Tắt'

    # Trả về dữ liệ cập nhật vào pins
    return jsonify({"pins": pins})

# The function below is executed when someone requests a URL with the pin number and action in it:
@app.route("/<board>/<changePin>/<action>")

def action(board, changePin, action):
   # Convert the pin from the URL into an integer:
   changePin = int(changePin)
   # Get the device name for the pin being changed:
   devicePin = pins[changePin]['name']

   if action in ["0", "1"]:
       new_status = 0 if action == "1" else 1
       conn = sqlite3.connect('/home/pi/picovoice/database/ConnectLukatoWeb.db')
       cursor = conn.cursor()
       cursor.execute("UPDATE LightControl SET status = ? WHERE pin_number = ? ;", (new_status, changePin))
       conn.commit()
       conn.close()

   # If the action part of the URL is "on," execute the code indented below:
   if action == "1" and board == 'esp8266':
      mqttc.publish(pins[changePin]['topic'],"1")
      pins[changePin]['state'] = 'Tắt'  

   if action == "0" and board == 'esp8266':
      mqttc.publish(pins[changePin]['topic'],"0")
      pins[changePin]['state'] = 'Mở'

   # Along with the pin dictionary, put the message into the template data dictionary:
   templateData = {
      'pins' : pins
   }

   return render_template('index.html', **templateData)



if __name__ == "__main__":
   app.run(host='0.0.0.0', port=8181, debug=True)