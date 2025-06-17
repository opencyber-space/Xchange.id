import asyncio
import logging
import json
from nats.aio.client import Client as NATS


class OrgJobPusher:
    def __init__(self, nats_url, topic):
        self.nats_url = nats_url
        self.topic = topic
        self.nc = NATS()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._connect()
        logging.basicConfig(level=logging.INFO)

    def _connect(self):
        try:
            self.loop.run_until_complete(self.nc.connect(self.nats_url))
            logging.info(f"Connected to NATS at {self.nats_url}")
        except Exception as e:
            logging.error(f"Failed to connect to NATS: {e}")
            raise

    async def _push_async(self, message):
        try:
            await self.nc.publish(self.topic, message.encode())
            logging.info(f"Message published to {self.topic}: {message}")
        except Exception as e:
            logging.error(f"Failed to publish message: {e}")
            raise

    def push(self, message_dict):
        try:
            message = json.dumps(message_dict)
            self.loop.run_until_complete(self._push_async(message))
        except Exception as e:
            logging.error(f"Error in push method: {e}")
            raise
