from flask import Flask
from flask_mqtt import Mqtt
from flask_sqlalchemy import SQLAlchemy
import os, datetime, time

app = Flask(__name__)

base_dir = os.path.abspath(os.path.dirname(__file__))
postgres_local_base = 'postgresql://postgres:openpgpwd@localhost/'
database_name = 'autocam'

app.config['DEBUG'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MQTT_CLIENT_ID'] = 'Akshay'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', postgres_local_base + database_name)
app.config['MQTT_BROKER_URL'] = '172.16.73.4'  # use the free broker from HIVEMQ
app.config['MQTT_BROKER_PORT'] = 1883  # default port for non-tls connection
app.config['MQTT_USERNAME'] = ''  # set the username here if you need authentication for the broker
app.config['MQTT_PASSWORD'] = ''  # set the password here if the broker demands authentication
app.config['MQTT_KEEPALIVE'] = 5  # set the time interval for sending a ping to the broker to 5 seconds
app.config['MQTT_TLS_ENABLED'] = False  # set TLS to disabled for testing purposes

mqtt = Mqtt(app)
db = SQLAlchemy(app)


class intrusion_entry(db.Model):
    __tablename__ = "intrusion_entry"
    c = 0
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    detect_area = db.Column(db.Integer, nullable=False)
    time_in = db.Column(db.String(255), nullable=False)

    def __init__(self, detect_area):
        self.detect_area = detect_area
        timenow = datetime.datetime.now()
        timenow = str(timenow.date()) + ' ' + str(timenow.hour) + ':' + str(timenow.minute)
        self.time_in = timenow

    def save_data(self):
        db.session.add(self)
        db.session.commit()


db.create_all()

flag = 0
c = 1


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(
        topic=message.topic.decode(),
        payload=message.payload.decode()
    )
    topic = str(data['topic'])
    message = str(data['payload'])
    if topic == 'home/autocam/recieve':
        print('Data Recieved by device: ' + message)
        global flag,c
        flag = 1
        c = 0
        time.sleep(2)
        mqtt.unsubscribe('home/autocam/start')
        mqtt.unsubscribe('home/autocam/recieve')
    elif topic == 'home/autocam' and c==0:
        print('Notification sent')
        mqtt.publish('home/autocam/notify',"Intrusion detected, Goto link 172.16.73.4 to see the live video")
        c = 1
        intrusion_entry(message).save_data()
        print('Intrusion Detected at Area: ' + message)
    elif topic == 'home/autocam' and c == 1:
        intrusion_entry(message).save_data()
        print('Intrusion Detected at Area: ' + message)
    elif topic == 'home/autocam/start' and flag==0:
        last_area = intrusion_entry.query.order_by(intrusion_entry.id.desc()).first()
        mqtt.publish('home/autocam/start', last_area.detect_area, qos=1)
        print('Publishing Data')
        time.sleep(2)


@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    print('MQTT Connected')
    mqtt.subscribe('home/autocam/start')
    mqtt.subscribe('home/autocam/recieve')
    last_area = intrusion_entry.query.order_by(intrusion_entry.id.desc()).first()
    mqtt.publish('home/autocam/start',last_area.detect_area)
    mqtt.subscribe('home/autocam')
    time.sleep(1)


if __name__ == '__main__':
    app.run(port=5555,debug=True, use_reloader = False)

