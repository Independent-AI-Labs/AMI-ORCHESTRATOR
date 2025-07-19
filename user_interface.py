import logging
import threading
import json
import queue
import redis

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class UserInterface:
    def __init__(self, redis_client: redis.Redis, user_command_stream: str):
        self.redis_client = redis_client
        self.USER_COMMAND_STREAM = user_command_stream
        self.running = False

    def start_input_thread(self):
        self.running = True
        threading.Thread(target=self._handle_user_input, daemon=True).start()

    def _handle_user_input(self):
        while self.running:
            try:
                user_input = input("Enter command (or 'exit' to quit): ")
                message_data = {}
                if user_input.lower().startswith("start_process "):
                    process_name = user_input[len("start_process "):].strip()
                    message_data = {"type": "START_BPMN_PROCESS", "content": process_name}
                elif user_input.lower().startswith("spawn_worker "):
                    worker_id = user_input[len("spawn_worker "):].strip()
                    message_data = {"type": "SPAWN_WORKER", "content": worker_id}
                elif user_input.lower() == "status":
                    message_data = {"type": "STATUS_REQUEST", "content": None}
                elif user_input.lower() == 'exit':
                    message_data = {"type": "EXIT", "content": None}
                else:
                    message_data = {"type": "USER_MESSAGE", "content": user_input}

                if message_data:
                    self.redis_client.xadd(self.USER_COMMAND_STREAM, {"message": json.dumps(message_data)})
            except Exception as e:
                logging.error(f"[USER_INTERFACE] Error handling user input: {e}")

    def stop_input_thread(self):
        self.running = False
