import logging
import json
import os
import time
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from tkinter import Toplevel

# Custom logger that writes to both console and UI
class UILogger:
    def __init__(self, text_widget=None):
        self.text_widget = text_widget
        self.console_logger = logging.getLogger("console_logger")
        self.console_logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.console_logger.addHandler(console_handler)
    
    def set_text_widget(self, text_widget):
        self.text_widget = text_widget
    
    def _log_to_ui(self, message, tag=None):
        if self.text_widget:
            self.text_widget.configure(state='normal')
            if tag:
                self.text_widget.insert(tk.END, message + "\n", tag)
            else:
                self.text_widget.insert(tk.END, message + "\n")
            self.text_widget.configure(state='disabled')
            self.text_widget.see(tk.END)  # Auto-scroll to end
    
    def info(self, message):
        self.console_logger.info(message)
        self._log_to_ui(f"INFO: {message}", "info")
    
    def warning(self, message):
        self.console_logger.warning(message)
        self._log_to_ui(f"WARNING: {message}", "warning")
    
    def error(self, message):
        self.console_logger.error(message)
        self._log_to_ui(f"ERROR: {message}", "error")

# Initialize logger
logger = UILogger()

# AWS IoT Endpoint and Certificate Paths
IOT_ENDPOINT = "a7vb9a42tnjyo-ats.iot.us-east-1.amazonaws.com"
CLAIM_CERTIFICATE_PATH = "claim-certificate.pem"
CLAIM_PRIVATE_KEY_PATH = "claim-private-key.pem"
ROOT_CA_PATH = "AmazonRootCA1.pem"

# Device Information
DEVICE_ID = ""
THING_NAME = ""  # Based on your provisioning response

# Topics
PROVISIONING_TEMPLATE = "ClaimCertProvisioningTemplate"
PROVISIONING_TOPIC = f"$aws/provisioning-templates/{PROVISIONING_TEMPLATE}/provision/json"
PROVISIONING_ACCEPTED_TOPIC = f"{PROVISIONING_TOPIC}/accepted"
PROVISIONING_REJECTED_TOPIC = f"{PROVISIONING_TOPIC}/rejected"
CERTIFICATE_CREATE_ACCEPTED = "$aws/certificates/create/json/accepted"
CERTIFICATE_CREATE_REJECTED = "$aws/certificates/create/json/rejected"

# Heartbeat Topic
# HEARTBEAT_TOPIC = f"devices/{THING_NAME}/heartbeat"

# Global variables
ownership_token = None
provisioning_complete = False
provisioned_thing_name = None
stop_heartbeat = True
heartbeat_active = False
device_client = None
heartbeat_thread = None

class HeartbeatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AWS IoT Heartbeat Publisher")
        self.root.geometry("800x600")
        self.setup_ui()
        
        # Set the logger's text widget
        logger.set_text_widget(self.log_text)
        
        # Initialize device state
        self.device_provisioned = False
        self.is_publishing = False

    def setup_ui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Device ID configuration frame
        device_frame = ttk.LabelFrame(main_frame, text="Device Configuration", padding="10")
        device_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(device_frame, text="Device ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.device_id_entry = ttk.Entry(device_frame, width=20)
        self.device_id_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.device_id_entry.insert(0, "DevId")  # Default value
                
        ttk.Label(device_frame, text="Thing Name Prefix:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.thing_prefix_entry = ttk.Entry(device_frame, width=20)
        self.thing_prefix_entry.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.thing_prefix_entry.insert(0, "Onsyte_")  # Default value

        # Bind the event to update Thing Name Prefix when Device ID changes
        self.device_id_entry.bind("<KeyRelease>", self.update_thing_prefix)

        self.apply_config_button = ttk.Button(device_frame, text="Apply", command=self.apply_device_config)
        self.apply_config_button.grid(row=1, column=2, padx=5, pady=2)

        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Device Status", padding="10")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Device ID label
        ttk.Label(status_frame, text=f"Device ID: {DEVICE_ID}").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(status_frame, text=f"Thing Name: {THING_NAME}").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Status indicators
        self.provision_status = ttk.Label(status_frame, text="Not Provisioned", foreground="red")
        self.provision_status.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.connection_status = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.connection_status.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        self.heartbeat_status = ttk.Label(status_frame, text="Heartbeat: Inactive", foreground="red")
        self.heartbeat_status.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # Heartbeat counter
        self.heartbeat_counter = ttk.Label(status_frame, text="Count: 0")
        self.heartbeat_counter.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Button frame
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Onboarding button
        self.onboard_button = ttk.Button(button_frame, text="Onboard Device", command=self.start_onboarding)
        self.onboard_button.pack(side=tk.LEFT, padx=5)
        
        # Start/Stop heartbeat buttons
        self.start_button = ttk.Button(button_frame, text="Start Heartbeat", command=self.start_heartbeat, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Heartbeat", command=self.stop_heartbeat, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Publish single heartbeat button
        self.publish_button = ttk.Button(button_frame, text="Publish Single Heartbeat", command=self.publish_single_heartbeat, state=tk.DISABLED)
        self.publish_button.pack(side=tk.LEFT, padx=5)

        # Custom topic publish section
        topic_frame = ttk.LabelFrame(main_frame, text="Publish Custom Message", padding="10")
        topic_frame.pack(fill=tk.X, padx=5, pady=5)

        # Device Status Frame
        self.status_frame = ttk.LabelFrame(main_frame, text="Device Status", padding="10")
        self.status_frame.pack(fill=tk.X, padx=5, pady=5)

        # Alarm Topic
        ttk.Label(topic_frame, text="Topic:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.alarm_topic_entry = ttk.Entry(topic_frame, width=40)
        self.alarm_topic_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.alarm_topic_entry.insert(0, f"devices/{THING_NAME}/AlarmLog")

        ttk.Label(topic_frame, text="Message:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.alarm_message_text = tk.Text(topic_frame, height=4, width=40)
        self.alarm_message_text.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.alarm_message_text.insert(tk.END, '{"message": "Custom payload", "timestamp": 0}')

        self.alarm_publish_button = ttk.Button(
            topic_frame,
            text="Publish",
            command=lambda: self.publish_custom_message(self.alarm_topic_entry, self.alarm_message_text),
            state=tk.DISABLED)

        self.alarm_publish_button.grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)

        # Station Log Topic
        ttk.Label(topic_frame, text="Topic:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.station_topic_entry = ttk.Entry(topic_frame, width=40)
        self.station_topic_entry.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.station_topic_entry.insert(0, f"devices/{THING_NAME}/StationLog")

        ttk.Label(topic_frame, text="Message:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.station_message_text = tk.Text(topic_frame, height=4, width=40)
        self.station_message_text.grid(row=4, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.station_message_text.insert(tk.END, '{"message": "Custom payload", "timestamp": 0}')

        self.station_publish_button = ttk.Button(
            topic_frame,
            text="Publish",
            command=lambda: self.publish_custom_message(self.station_topic_entry, self.station_message_text),
            state=tk.DISABLED
        )

        self.station_publish_button.grid(row=5, column=1, sticky=tk.E, padx=5, pady=5)

        # Custom Topic
        ttk.Label(topic_frame, text="Topic:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        self.custom_topic_entry = ttk.Entry(topic_frame, width=40)
        self.custom_topic_entry.grid(row=6, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.custom_topic_entry.insert(0, f"devices/{THING_NAME}/custom")

        ttk.Label(topic_frame, text="Message:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
        self.custom_message_text = tk.Text(topic_frame, height=4, width=40)
        self.custom_message_text.grid(row=7, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        self.custom_message_text.insert(tk.END, '{"message": "Custom payload", "timestamp": 0}')

        self.custom_publish_button = ttk.Button(
            topic_frame,
            text="Publish",
            command=lambda: self.publish_custom_message(self.custom_topic_entry, self.custom_message_text),
            state=tk.DISABLED
        )

        self.custom_publish_button.grid(row=8, column=1, sticky=tk.E, padx=5, pady=5)

        # # Custom topic publish section
        # topic_frame = ttk.LabelFrame(main_frame, text="Publish Custom Message", padding="10")
        # topic_frame.pack(fill=tk.X, padx=5, pady=5)
        

        # # Status frame
        # self.status_frame = ttk.LabelFrame(main_frame, text="Device Status", padding="10")
        # self.status_frame.pack(fill=tk.X, padx=5, pady=5)

        # # Make columns expandable for resizing
        # topic_frame.columnconfigure(1, weight=1)

        # # 🔹 ALARM TOPIC
        # ttk.Label(topic_frame, text="Alarm Topic:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        # alarm_entry = ttk.Entry(topic_frame, width=40)
        # alarm_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        # alarm_entry.insert(0,  f"devices/{THING_NAME}/AlarmLog")

        # ttk.Label(topic_frame, text="Message:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        # alarm_text = tk.Text(topic_frame, height=4, width=40)
        # alarm_text.grid(row=1, column=1, sticky="nsew", padx=5, pady=2)
        # alarm_text.insert(tk.END, '{"message": "Custom payload", "timestamp": 0}')

        # publish_alarm_button = ttk.Button(topic_frame, text="Publish", command=lambda: self.publish_custom_message(alarm_entry, alarm_text))
        # publish_alarm_button.grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)

        # # 🔹 STATION LOG TOPIC
        # ttk.Label(topic_frame, text="Station Log Topic:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        # station_entry = ttk.Entry(topic_frame, width=40)
        # station_entry.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        # station_entry.insert(0,  f"devices/{THING_NAME}/StationLog")

        # ttk.Label(topic_frame, text="Message:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        # station_text = tk.Text(topic_frame, height=4, width=40)
        # station_text.grid(row=4, column=1, sticky="nsew", padx=5, pady=2)
        # station_text.insert(tk.END, '{"message": "Custom payload", "timestamp": 0}')

        # publish_station_button = ttk.Button(topic_frame, text="Publish", command=lambda: self.publish_custom_message(station_entry, station_text))
        # publish_station_button.grid(row=5, column=1, sticky=tk.E, padx=5, pady=5)

        # # 🔹 CUSTOM TOPIC
        # ttk.Label(topic_frame, text="Custom Topic:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        # custom_entry = ttk.Entry(topic_frame, width=40)
        # custom_entry.grid(row=6, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        # custom_entry.insert(0,  f"devices/{THING_NAME}/custom")

        # ttk.Label(topic_frame, text="Message:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
        # custom_text = tk.Text(topic_frame, height=4, width=40)
        # custom_text.grid(row=7, column=1, sticky="nsew", padx=5, pady=2)
        # custom_text.insert(tk.END, '{"message": "Custom payload", "timestamp": 0}')

        # publish_custom_button = ttk.Button(topic_frame, text="Publish", command=lambda: self.publish_custom_message(custom_entry, custom_text))
        # publish_custom_button.grid(row=8, column=1, sticky=tk.E, padx=5, pady=5)


        # #Custom Topic
        # ttk.Label(topic_frame, text="Topic:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        # self.topic_entry = ttk.Entry(topic_frame, width=40)
        # self.topic_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        # self.topic_entry.insert(0, f"devices/{THING_NAME}/custom")
        
        # ttk.Label(topic_frame, text="Message:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        # self.message_text = tk.Text(topic_frame, height=4, width=40)
        # self.message_text.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        # self.message_text.insert(tk.END, '{"message": "Custom payload", "timestamp": 0}')
        
        # self.publish_custom_button = ttk.Button(topic_frame, text="Publish", command=self.publish_custom_message, state=tk.DISABLED)
        # self.publish_custom_button.grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


        # Add a "View Fullscreen Log" Button Below Log Frame
        self.view_logs_button = ttk.Button(log_frame, text="View Fullscreen Logs", command=self.open_fullscreen_log)
        self.view_logs_button.pack(pady=5)    

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state='disabled')
        
        # Configure tags for different log levels
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")

        # Add a "View Fullscreen Log" Button Below Log Frame
        self.view_logs_button = ttk.Button(log_frame, text="View Fullscreen Logs", command=self.open_fullscreen_log)
        self.view_logs_button.pack(pady=5)

        # Add exit button at bottom
        exit_button = ttk.Button(main_frame, text="Exit", command=self.on_exit)
        exit_button.pack(side=tk.RIGHT, padx=5, pady=5)

    def open_fullscreen_log(self):
        """Open a fullscreen window to view logs."""
        log_window = Toplevel(self.root)
        log_window.title("Fullscreen Log Viewer")
        # log_window.attributes('-fullscreen', True)  # Enable fullscreen mode

        # Set a fixed size (e.g., 800x600) and center it
        log_window.geometry("800x600")
        log_window.transient(self.root)  # Keep it on top of the main window
        log_window.grab_set()  # Make it modal (disable interactions with main window)
        log_window.resizable(True, True)  # Allow resizing
        # Log Text Area
        fullscreen_log_text = scrolledtext.ScrolledText(log_window, height=30)
        fullscreen_log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configure same log colors
        fullscreen_log_text.tag_configure("info", foreground="blue")
        fullscreen_log_text.tag_configure("warning", foreground="orange")
        fullscreen_log_text.tag_configure("error", foreground="red")

        # Copy logs from main log area
        fullscreen_log_text.insert(tk.END, self.log_text.get("1.0", tk.END))
        fullscreen_log_text.configure(state='disabled')

        # Exit Fullscreen Button
        close_button = ttk.Button(log_window, text="Exit Fullscreen", command=log_window.destroy)
        close_button.pack(pady=10)

    def update_thing_prefix(self, event):
        """Update Thing Name Prefix when Device ID changes."""
        new_device_id = self.device_id_entry.get()  # Get the updated Device ID
        self.thing_prefix_entry.delete(0, tk.END)  # Clear the existing text
        self.thing_prefix_entry.insert(0, f"Onsyte_{new_device_id}")  # Insert updated value


    def start_onboarding(self):
        self.onboard_button.configure(state=tk.DISABLED)
        
        # Start onboarding in a separate thread to keep UI responsive
        threading.Thread(target=self.onboard_device_thread, daemon=True).start()

    def apply_device_config(self):
        global DEVICE_ID, THING_NAME
        
        logger.info(f"apply_device_config: {DEVICE_ID}")       
        logger.info(f"apply_device_config: {THING_NAME}")       
        new_device_id = self.device_id_entry.get().strip()
        prefix = self.thing_prefix_entry.get().strip()
        
        if not new_device_id:
            logger.error("Device ID cannot be empty")
            return
        
        # Update the global variables
        DEVICE_ID = new_device_id
        # THING_NAME = f"{prefix}{DEVICE_ID}"
        THING_NAME = f"{prefix}"
        
        logger.info(f"apply_device_config: {DEVICE_ID}")       
        logger.info(f"apply_device_config: {THING_NAME}")      
        # Update UI elements
        ttk.Label(self.status_frame, text=f"Device ID: {DEVICE_ID}").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(self.status_frame, text=f"Thing Name: {THING_NAME}").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        
        # Update topic fields
        # self.topic_entry.delete(0, tk.END)
        # self.topic_entry.insert(0, f"devices/{THING_NAME}/custom")
        # Update Alarm Topic
        self.alarm_topic_entry.delete(0, tk.END)
        self.alarm_topic_entry.insert(0, f"devices/{THING_NAME}/AlarmLog")

        # Update Station Log Topic
        self.station_topic_entry.delete(0, tk.END)
        self.station_topic_entry.insert(0, f"devices/{THING_NAME}/StationLog")

        # Update Custom Topic
        self.custom_topic_entry.delete(0, tk.END)
        self.custom_topic_entry.insert(0, f"devices/{THING_NAME}/custom")        
        
        self.topic_entry.delete(0, tk.END)
        self.topic_entry.insert(0, f"devices/{THING_NAME}/status")
        
        logger.info(f"✅ Configuration updated: Device ID: {DEVICE_ID}, Thing Name: {THING_NAME}")

    def onboard_device_thread(self):
        global provisioning_complete, provisioned_thing_name, device_client
        
        try:
            logger.info("🔄 Starting device onboarding process...")
            
            # Initialize MQTT client with claim certificate
            claim_client = self.initialize_mqtt_client(
                "ClaimCertificateClient", 
                CLAIM_CERTIFICATE_PATH, 
                CLAIM_PRIVATE_KEY_PATH
            )
            
            if claim_client is None:
                logger.error("❌ Failed to initialize claim certificate client")
                self.root.after(0, lambda: self.onboard_button.configure(state=tk.NORMAL))
                return
            
            # Connect to AWS IoT using claim certificate
            if not self.connect_mqtt_client(claim_client):
                self.root.after(0, lambda: self.onboard_button.configure(state=tk.NORMAL))
                return
            
            # Request certificate ownership token
            token = self.request_certificate_ownership_token(claim_client)
            if token is None:
                claim_client.disconnect()
                self.root.after(0, lambda: self.onboard_button.configure(state=tk.NORMAL))
                return
            
            # Request device provisioning
            if not self.request_device_provisioning(claim_client, token):
                claim_client.disconnect()
                self.root.after(0, lambda: self.onboard_button.configure(state=tk.NORMAL))
                return
            
            # Disconnect claim certificate client
            claim_client.disconnect()
            logger.info("Disconnected claim certificate client")
            
            # For this specific setup, we'll use the claim certificate for publishing heartbeats
            logger.info("Using claim certificate for heartbeat publishing")
            device_client = self.initialize_mqtt_client(
                THING_NAME, 
                CLAIM_CERTIFICATE_PATH, 
                CLAIM_PRIVATE_KEY_PATH
            )
            
            if device_client is None:
                logger.error("❌ Failed to initialize device client")
                self.root.after(0, lambda: self.onboard_button.configure(state=tk.NORMAL))
                return
            
            # Connect to AWS IoT using claim certificate
            if not self.connect_mqtt_client(device_client):
                self.root.after(0, lambda: self.onboard_button.configure(state=tk.NORMAL))
                return
            
            # Update UI
            self.root.after(0, self.update_ui_after_provisioning)
            logger.info(f"✅ Device {provisioned_thing_name or THING_NAME} connected and ready to send heartbeats")
            
        except Exception as e:
            logger.error(f"❌ Error during device onboarding: {e}")
            self.root.after(0, lambda: self.onboard_button.configure(state=tk.NORMAL))

    def update_ui_after_provisioning(self):
        # Enable buttons
        self.start_button.configure(state=tk.NORMAL)
        self.publish_button.configure(state=tk.NORMAL)
        self.station_publish_button.configure(state=tk.NORMAL)
        self.alarm_publish_button.configure(state=tk.NORMAL)
        self.custom_publish_button.configure(state=tk.NORMAL)
        
        # Update status labels
        self.provision_status.configure(text="Provisioned", foreground="green")
        self.connection_status.configure(text="Connected", foreground="green")
        
        # Disable onboarding button
        self.onboard_button.configure(state=tk.DISABLED)
        
        # Update device state
        self.device_provisioned = True

    def start_heartbeat(self):
        global stop_heartbeat, heartbeat_active, heartbeat_thread
        
        if not self.device_provisioned:
            logger.error("Cannot start heartbeat: Device not provisioned")
            return
        
        stop_heartbeat = False
        heartbeat_active = True
        
        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=self.publish_heartbeat_thread, daemon=True)
        heartbeat_thread.start()
        
        # Update UI
        self.heartbeat_status.configure(text="Heartbeat: Active", foreground="green")
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)

    def stop_heartbeat(self):
        global stop_heartbeat, heartbeat_active
        
        stop_heartbeat = True
        heartbeat_active = False
        
        # Update UI
        self.heartbeat_status.configure(text="Heartbeat: Inactive", foreground="red")
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def publish_single_heartbeat(self):
        global device_client
        
        if not self.device_provisioned or device_client is None:
            logger.error("Cannot publish: Device not provisioned")
            return

        logger.info(f"publish_single_heartbeat: {DEVICE_ID}")       
        logger.info(f"publish_single_heartbeat: {THING_NAME}")       
        logger.info(f"publish_single_heartbeat: {f"devices/{THING_NAME}/heartbeat"}")        
     
        try:
            # Create single heartbeat message
            message = {
                "device_id": provisioned_thing_name or THING_NAME,
                "timestamp": int(time.time()),
                "count": -1,  # Single message indicator
                "status": "active",
                "type": "manual"
            }
            HEARTBEAT_TOPIC = f"devices/{THING_NAME}/heartbeat"
          
            # Publish the message
            result = device_client.publish(HEARTBEAT_TOPIC, json.dumps(message), 1)
            if result:
                logger.info("✅ Single heartbeat published successfully")
            else:
                logger.warning("⚠️ Failed to publish single heartbeat")
                
        except Exception as e:
            logger.error(f"❌ Error publishing single heartbeat: {e}")

    def publish_custom_message(self, topic_entry, message_text):
        logger.info(f"✅ publish_custom_message recieved :{self} {topic_entry} {message_text}")
        global device_client
        
        if not self.device_provisioned or device_client is None:
            logger.error("Cannot publish: Device not provisioned")
            return
        
        try:
            # Get topic and message from UI
            topic = topic_entry.get()
            message_str = message_text.get("1.0", tk.END).strip()
            
            try:
                # Validate JSON
                message = json.loads(message_str)
                
                # Add timestamp if not present
                if "timestamp" not in message or message["timestamp"] == 0:
                    message["timestamp"] = int(time.time())
                    message_str = json.dumps(message)
            except json.JSONDecodeError:
                logger.error("❌ Invalid JSON format in message")
                return
            
            # Publish the message
            result = device_client.publish(topic, message_str, 1)
            if result:
                logger.info(f"✅ Custom message published to {topic}")
            else:
                logger.warning(f"⚠️ Failed to publish to {topic}")
                
        except Exception as e:
            logger.error(f"❌ Error publishing custom message: {e}")

    def publish_heartbeat_thread(self):
        global device_client, stop_heartbeat
        counter = 0
       
        while not stop_heartbeat:
            try:
                counter += 1
                message = {
                    "device_id": provisioned_thing_name or THING_NAME,
                    "timestamp": int(time.time()),
                    "count": counter,
                    "status": "active",
                    "type": "automatic"
                }
                if device_client:
                    HEARTBEAT_TOPIC = f"devices/{THING_NAME}/heartbeat"               
                    result = device_client.publish(HEARTBEAT_TOPIC, json.dumps(message), 1)
                    if result:
                        logger.info(f"💓 Heartbeat #{counter} published")
                        logger.info(f"💓 HEARTBEAT_TOPIC #{HEARTBEAT_TOPIC}")
                        logger.info(f"💓 message #{message}")
                        # Update counter in UI thread-safely
                        self.root.after(0, lambda c=counter: self.heartbeat_counter.configure(text=f"Count: {c}"))
                    else:
                        logger.warning(f"⚠️ Failed to publish heartbeat #{counter}")
                
                # Wait for next heartbeat interval (10 seconds)
                for i in range(10):
                    if stop_heartbeat:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"❌ Error publishing heartbeat: {e}")
                time.sleep(5)  # Wait before retrying

    def on_exit(self):
        global stop_heartbeat, device_client
        
        # Stop heartbeat if running
        stop_heartbeat = True
        
        # Disconnect from AWS IoT
        if device_client:
            logger.info("Disconnecting from AWS IoT...")
            device_client.disconnect()
        
        self.root.destroy()

    def check_file_exists(self, file_path):
        """Check if a file exists and is readable"""
        if not os.path.isfile(file_path):
            logger.error(f"Required file not found: {file_path}")
            return False
        return True

    def initialize_mqtt_client(self, client_id, cert_path, key_path, endpoint=IOT_ENDPOINT):
        """Initialize and configure MQTT client for AWS IoT"""
        try:
            logger.info(f"Initializing MQTT client: {client_id}...")
            
            # Verify certificate files exist
            if not (self.check_file_exists(cert_path) and 
                    self.check_file_exists(key_path) and 
                    self.check_file_exists(ROOT_CA_PATH)):
                return None
            
            client = AWSIoTMQTTClient(client_id)
            client.configureEndpoint(endpoint, 8883)
            client.configureCredentials(ROOT_CA_PATH, key_path, cert_path)
            
            # Configure MQTT client
            client.configureAutoReconnectBackoffTime(1, 32, 20)
            client.configureOfflinePublishQueueing(-1)  # Infinite queueing
            client.configureDrainingFrequency(2)  # Drains queue at 2 Hz
            client.configureConnectDisconnectTimeout(10)  # 10 second connection timeout
            client.configureMQTTOperationTimeout(5)  # 5 second operation timeout
            
            return client
        except Exception as e:
            logger.error(f"❌ Error initializing MQTT client: {e}")
            return None

    def connect_mqtt_client(self, client, max_retries=3):
        """Connect to AWS IoT with retry logic"""
        retries = 0
        while retries < max_retries:
            try:
                logger.info("Attempting to connect to AWS IoT Core...")
                if client.connect():
                    logger.info("✅ Successfully connected to AWS IoT")
                    return True
                else:
                    logger.warning(f"Connection attempt failed (attempt {retries+1}/{max_retries})")
            except Exception as e:
                logger.error(f"❌ Connection error: {e}")
            
            retries += 1
            time.sleep(2)  # Wait before retrying
        
        logger.error("❌ Failed to connect after multiple attempts")
        return False

    def certificate_create_callback(self, client, userdata, message):
        """Callback function to receive the Certificate Ownership Token"""
        global ownership_token
        try:
            payload = json.loads(message.payload)
            ownership_token = payload.get("certificateOwnershipToken")
            if ownership_token:
                logger.info(f"✅ Received Certificate Ownership Token")
            else:
                logger.error("❌ Certificate Ownership Token not found in response")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to decode certificate ownership token response: {e}")

    def provisioning_accepted_callback(self, client, userdata, message):
        """Callback function to handle provisioning accepted response"""
        global provisioning_complete, provisioned_thing_name
        try:
            payload = json.loads(message.payload)
            logger.info("✅ Provisioning accepted")
            logger.info(f"Response payload: {json.dumps(payload, indent=2)}")
            
            # Extract thing name if available
            if "thingName" in payload:
                provisioned_thing_name = payload["thingName"]
                logger.info(f"✅ Device registered as thing: {provisioned_thing_name}")
            
            # Mark provisioning as complete regardless of certificate data
            # We'll continue using the claim certificate
            provisioning_complete = True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to decode provisioning response: {e}")

    def provisioning_rejected_callback(self, client, userdata, message):
        """Callback function to handle provisioning rejected response"""
        try:
            payload = json.loads(message.payload)
            logger.error(f"❌ Provisioning rejected: {payload}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to decode provisioning rejection: {e}")

    def request_certificate_ownership_token(self, client):
        """Request a certificate ownership token"""
        global ownership_token
        ownership_token = None
        
        logger.info("📢 Requesting Certificate Ownership Token...")
        
        # Subscribe to ownership token response topics
        client.subscribe(CERTIFICATE_CREATE_ACCEPTED, 1, self.certificate_create_callback)
        client.subscribe(CERTIFICATE_CREATE_REJECTED, 1, self.certificate_create_callback)
        
        # Empty payload for token request
        client.publish("$aws/certificates/create/json", "{}", 1)
        
        # Wait for response with timeout
        timeout = 10  # seconds
        start_time = time.time()
        while ownership_token is None and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        # Clean up subscriptions
        client.unsubscribe(CERTIFICATE_CREATE_ACCEPTED)
        client.unsubscribe(CERTIFICATE_CREATE_REJECTED)
        
        if ownership_token is None:
            logger.error("❌ Failed to retrieve Certificate Ownership Token (timeout)")
            return None
        
        return ownership_token

    def request_device_provisioning(self, client, token):
        """Request device provisioning using the certificate ownership token"""
        global provisioning_complete, provisioned_thing_name
        provisioning_complete = False
        
        # Subscribe to provisioning response topics
        client.subscribe(PROVISIONING_ACCEPTED_TOPIC, 1, self.provisioning_accepted_callback)
        client.subscribe(PROVISIONING_REJECTED_TOPIC, 1, self.provisioning_rejected_callback)
        
        # Prepare provisioning request payload
        payload = {
            "parameters": {
                "SerialNumber": DEVICE_ID,
                "ThingName": THING_NAME
            },
            "certificateOwnershipToken": token
        }
        
        # Publish provisioning request
        logger.info(f"📢 Publishing provisioning request for device {DEVICE_ID}")
        client.publish(PROVISIONING_TOPIC, json.dumps(payload), 1)
        
        # Wait for provisioning response with timeout
        timeout = 15  # seconds
        start_time = time.time()
        while not provisioning_complete and (time.time() - start_time) < timeout:
            time.sleep(0.5)
        
        # Clean up subscriptions
        client.unsubscribe(PROVISIONING_ACCEPTED_TOPIC)
        client.unsubscribe(PROVISIONING_REJECTED_TOPIC)
        
        if not provisioning_complete:
            logger.error("❌ Device provisioning failed or timed out")
            return False
        
        return True

def main():
    root = tk.Tk()
    app = HeartbeatApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()