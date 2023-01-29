from uuid import uuid4
from typing import Optional

from paho.mqtt import client as mqtt_client
from paho.mqtt.client import Client

class Mqtt:

    def __init__(
        self, 
        username: str,
        password: str,
        broker: str = "localhost",
        port: int = 1883,
        client_id: Optional[str] = None
    ) -> None:
        """ Constructor.

        Parameters
        ----------
        username: :class:`str`
            Username to connect to broker.
        password: :class:`str`
            Password to connect to broker.
        broker: :class:`str`
            Broker address.
        port: :class:`int`
            Broker port
        client_id: :class:`str | None`
            Unique ID used to identify the connection.
        """

        self.broker = broker
        self.port = port

        if(client_id == None):
            self.client_id = f"paho-mqtt-{str(uuid4()).split('-')[0]}"
        else:
            self.client_id = client_id

        self.username = username
        self.password = password

        self.client = self.__connect_mqtt()


    def __connect_mqtt(self) -> Client:
        """ Connect to MQTT broker.

        Return
        ------
        :class:`Client`
        """

        def on_connect(client, userdata, flags, rc):
            if(rc == 0):
                print("Connected to MQTT Broker!")
            else:
                print(f"Failed to connect to Broker! Return code {rc}.")

        client: Client = mqtt_client.Client(self.client_id)
        client.username_pw_set(self.username, self.password)
        client.on_connect = on_connect

        client.connect(self.broker, self.port)
        
        return client
    
    def publish(self, topic: str, message: str) -> bool:
        """ Publish a message to a specified topic.

        Parameters
        ----------
        topic: :class:`str`
            MQTT topic.
        message: :class:`str`
            The message.
        
        Return
        ------
        :class:`bool`
        """
        
        result = self.client.publish(topic, message)

        status = result[0]

        if(status == 0):
            print(f"Message sended to topic '{topic}'.")

            return True
        else:
            print(f"Failed to send message to topic {topic}")

            return False
        
    def subscribe(self, topic: str) -> None:
        """ Subscribe to a specific topic.

        Parameters
        ----------
        topic: :class:`str`
            MQTT topic.
        """

        def on_message(client, userdata, msg):
            print(f"Received from '{msg.topic}' topic:")
            print(msg.payload.decode())

        self.client.subscribe(topic)
        self.client.on_message = on_message

    def loop_forever(self) -> None:
        """ Calls the network loop functions for you in an 
        infinite blocking loop. It is useful for the case where you only want 
        to run the MQTT client loop in your program.
        """
        
        self.client.loop_forever()