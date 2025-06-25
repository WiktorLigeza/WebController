import random
from flask import Flask, render_template
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import time
import json
import threading
import math
from typing import List, Tuple
from utm import from_latlon, to_latlon

class CarController:

    def __init__(self, app):
        """
        Initializes the CarController with the Flask app and MQTT configurations.
        """
        self.app = app
        self.app.config['SECRET_KEY'] = 'secret!'
        self.socketio = SocketIO(self.app)
        self.initial_x: float = 423447.1379357168
        self.initial_y: float = 5717226.386050694


        # MQTT Configuration
        self.MQTT_BROKER = 'localhost'
        self.MQTT_PORT = 1883
        self.MQTT_TOPIC = 'gnss/data'
        self.mqtt_client = self.connect_mqtt()
        self.mqtt_client.loop_start()

        # Car State
        self.car_x: float = self.initial_x
        self.car_y: float = self.initial_y
        self.base_speed: float = 2.0  # m/s
        self.turn_speed: float = 2.0  # m/s
        self.max_speed: float = 4.0  # m/s
        self.shift_speed: float = 6.0  # m/s
        self.heading: float = 0.0  # degrees
        self.last_keys_pressed: List[str] = []  # Store the last pressed keys
        self.speed: float = 0.0
        self.prev_x: float = 0.0
        self.prev_y: float = 0.0
        self.speed_timer: float = time.time()  # Add speed timer

        # from logs
        self.iter_count: int = 1
        self.log_data = {}
        self.load_logs()
        self.from_logs = False

        # Start the GPS publisher thread
        self.gps_thread = threading.Thread(target=self.gps_publisher)
        self.gps_thread.daemon = True
        self.gps_thread.start()
        

        self.register_routes()

    def load_logs(self):
        with open('logs/test-2025-01-29-14-37-26.json', 'r') as f:
            self.log_data = json.load(f)

    def connect_mqtt(self) -> mqtt.Client:
        """
        Connects to the MQTT broker.

        Returns:
            mqtt.Client: The MQTT client object.
        """
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print(f"Failed to connect, return code {rc}")
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_connect
        mqtt_client.connect(self.MQTT_BROKER, self.MQTT_PORT)
        return mqtt_client

    def calculate_new_position(self, keys: List[str]) -> None:
        """
        Calculates the new position of the car based on steps.

        Args:
            keys (List[str]): A list of keys currently pressed.

        Returns:
            Tuple[float, float, float, float]: The new x, y coordinates, heading, and speed.
        """
        # Define basic movement flags
        forward: bool = 'w' in keys
        backward: bool = 's' in keys
        turn_left: bool = 'a' in keys
        turn_right: bool = 'd' in keys
        shift: bool = 'Shift' in keys

        # Handle rotation
        if turn_left:
            self.heading += 0.2
        if turn_right:
            self.heading -= 0.2

        # Normalize heading to be within 0-360 degrees
        self.heading %= 360

        # Convert heading to radians
        heading_rad: float = math.radians(self.heading)

        # Determine step size
        step: float = 0.010  # default step
        if forward:
            if shift:
                step = 0.03  # increased step with shift

            # Apply step in current heading direction
            self.car_x += step * math.cos(heading_rad)
            self.car_y += step * math.sin(heading_rad)
        elif backward:
            # Backward movement always uses default step
            self.car_x -= 0.01 * math.cos(heading_rad)
            self.car_y -= 0.01 * math.sin(heading_rad)

    def calculate_speed(self) -> None:
        """
        Calculates the speed based on distance traveled over time.
        """
        current_time = time.time()
        time_delta = current_time - self.speed_timer
        distance = math.sqrt((self.car_x - self.prev_x)**2 + (self.car_y - self.prev_y)**2)
        
        # Calculate speed (distance/time)
        if time_delta > 0:
            self.speed = distance / time_delta
        
        # Update previous positions and timer
        self.prev_x = self.car_x
        self.prev_y = self.car_y
        self.speed_timer = current_time

    def get_lat_lon(self):
        lat, lon = to_latlon(self.car_x, self.car_y, 34, "U")
        return lat, lon

    def read_logs(self):
        if self.iter_count >= len(self.log_data.keys()):
            self.iter_count = 1
            print("++++++++++++++++++++++ Log iteration reset ++++++++++++++++++++++")
            time.sleep(3)
        
        key = list(self.log_data.keys())[self.iter_count]
        response = self.log_data[key]
        response["speed"] = response["speed"]/3.6
               
        if self.iter_count > 0:
            prev_key = list(self.log_data.keys())[self.iter_count-1]
            time_diff = abs(float(key) - float(prev_key))
            time.sleep(time_diff)
        
        self.iter_count += 1
        return True, response

    def gps_publisher(self):
        """
        A function to continuously publish GPS data to the MQTT broker.
        """
       
        while True:
            if self.from_logs:
                success, response = self.read_logs()
                if not success: continue
                data = json.dumps(response)
                self.mqtt_client.publish(self.MQTT_TOPIC, data)
            else:
                self.calculate_speed()
                lat, lon = self.get_lat_lon()
                data = json.dumps({"x": self.car_x, 
                                "y": self.car_y, 
                                "lat": lat,
                                "lon": lon,
                                "quality": random.randint(1, 6),
                                "heading": (self.heading*-1+180-90)%360, 
                                "speed": self.speed})
                self.mqtt_client.publish(self.MQTT_TOPIC, data)
                time.sleep(0.1)  # 10 Hz

    def register_routes(self):
        """
        Registers the Flask routes.
        """
        @self.app.route('/')
        def default_route():
            return render_template('xbox.html')

        @self.app.route('/wsad')
        def wsad():
            return render_template('wsad.html')

        @self.app.route('/xbox')
        def xbox():
            return render_template('xbox.html')
        
        @self.app.route('/update_from_logs/<value>')
        def update_from_logs(value):
            self.from_logs = value == 'true'
            return "OK"

        @self.socketio.on('keys_pressed')
        def handle_key_pressed(keys: List[str]):
            """
            Handles the 'keys_pressed' event from the client.
            """
            print(f"Keys pressed: {keys}")  # Debugging: Print the keys received
            self.last_keys_pressed = keys
            
            # Calculate the new position and speed
            self.calculate_new_position(keys)

        @self.socketio.on('xbox_input')
        def handle_xbox_input(data):
            """
            Handles the 'xbox_input' event from the client.
            """
            left_x = data['leftX']
            left_y = data['leftY']
            right_x = data['rightX']
            right_y = data['rightY']
            rt = data['rt']

           # print(f"Xbox Input: Left Stick=({left_x}, {left_y}), Right Stick=({right_x}, {right_y}), RT={rt}")

            self.calculate_new_position_xbox(left_x, left_y, right_x, right_y, rt)

    def calculate_new_position_xbox(self, left_x: float, left_y: float, right_x: float, right_y: float, rt: float) -> None:
        """
        Calculates the new position of the car based on Xbox controller input, filtering noise.

        Args:
            left_x (float): Left stick X axis value.
            left_y (float): Left stick Y axis value.
            right_x (float): Right stick X axis value.
            right_y (float): Right stick Y axis value.
            rt (float): Right trigger value.
        """
        # Noise threshold
        threshold: float = 0.1

        # Apply threshold to left stick (forward/backward movement)
        if abs(left_y) < threshold:
            left_y = 0.0
        if abs(left_x) < threshold:
            left_x = 0.0

        # Apply threshold to right stick (turning)
        if abs(right_y) < threshold:
            right_y = 0.0
        if abs(right_x) < threshold:
            right_x = 0.0

        # Movement
        max_forward_step: float = 0.1
        min_reverse_step: float = -0.03
        forward_step: float = left_y * (max_forward_step - min_reverse_step) + min_reverse_step
        if rt > 0:
            forward_step *= (1 + rt)  # Boost with RT

        if left_y == 0:
            forward_step = 0.0

        # Turning
        max_turn_heading_step: float = 0.3
        turn_heading_step: float = right_x * max_turn_heading_step

        # Update heading
        self.heading -= turn_heading_step

        # Normalize heading to be within 0-360 degrees
        self.heading %= 360

        # Convert heading to radians
        heading_rad: float = math.radians(self.heading)

        # Apply movement
        self.car_x += forward_step * math.cos(heading_rad)
        self.car_y += forward_step * math.sin(heading_rad)

if __name__ == '__main__':
    app = Flask(__name__)
    car_controller = CarController(app)
    car_controller.socketio.run(app, debug=False, host='0.0.0.0', port=2222, allow_unsafe_werkzeug=True)
