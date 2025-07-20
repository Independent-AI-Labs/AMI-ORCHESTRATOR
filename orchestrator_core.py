import traceback
import os
import logging
import asyncio
import redis.asyncio as redis
import subprocess
import threading
import json
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from orchestrator.orchestrator_agent import OrchestratorAgent
from orchestrator.models.bpmn_models import Agent, AgentType, AgentStatus
from orchestrator.dgraph.dgraph_client import DgraphClient
from orchestrator.bpmn_engine import BPMNEngine
from orchestrator.worker_manager import WorkerManager
from orchestrator.config import AIConfig # Import AIConfig

from orchestrator.process_definitions_loader import ProcessDefinitionsLoader

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class OrchestratorCore:
    def __init__(self, cli_directory: str, dgraph_url: str = "localhost:9080"):
        # Retrieve API key from AIConfig
        self.google_api_key = AIConfig.get_active_llm_config().get('api_key') # Assuming API key is part of LLMConfig
        self.cli_directory = cli_directory
        logging.info(f"[OrchestratorCore] Using CLI directory path: {self.cli_directory}")
        if not os.path.isdir(self.cli_directory):
            logging.error(f"[OrchestratorCore] CLI directory does not exist or is not a directory: {self.cli_directory}")
        self.dgraph_client = DgraphClient()
        self.orchestrator_agent_model = Agent(id="orchestrator-agent", name="Orchestrator Agent", agent_type=AgentType.ORCHESTRATOR, status=AgentStatus.IDLE)
        
        self.worker_clients = {}
        self.worker_message_queue = asyncio.Queue()
        self.running = False
        self.active_processes = {}
        self.bpmn_engine_task = None
        self.worker_message_processing_task = None

        self.redis_client = redis.Redis(host='172.72.72.2', port=6379, db=0, decode_responses=True)

        self.USER_COMMAND_STREAM = "user_commands"
        self.WORKER_RESULT_STREAM = "worker_results"
        self.USER_OUTPUT_STREAM = "user_output"
        self.DEAD_LETTER_QUEUE_STREAM = "dead_letter_queue"
        self.ORCHESTRATOR_GROUP = "orchestrator_group"

        self.bpmn_engine = BPMNEngine(
            dgraph_client=self.dgraph_client,
            active_processes=self.active_processes,
            worker_clients=self.worker_clients,
            redis_client=self.redis_client,
            dead_letter_queue_stream=self.DEAD_LETTER_QUEUE_STREAM
        )
        self.worker_manager = WorkerManager(
            dgraph_client=self.dgraph_client,
            worker_clients=self.worker_clients,
            worker_message_queue=self.worker_message_queue
        )
        
        self.process_definitions_loader = ProcessDefinitionsLoader(
            dgraph_client=self.dgraph_client,
            active_processes=self.active_processes
        )
        self.orchestrator_agent_instance = OrchestratorAgent(
            orchestrator_core_instance=self,
            dgraph_client=self.dgraph_client,
            worker_manager=self.worker_manager,
            redis_client=self.redis_client,
            user_command_stream=self.USER_COMMAND_STREAM,
            worker_result_stream=self.WORKER_RESULT_STREAM,
            dead_letter_queue_stream=self.DEAD_LETTER_QUEUE_STREAM,
            user_output_stream=self.USER_OUTPUT_STREAM,
            google_api_key=self.google_api_key
        )

    async def setup_redis(self):
        self.USER_COMMAND_STREAM = "user_commands"
        self.WORKER_RESULT_STREAM = "worker_results"
        self.DEAD_LETTER_QUEUE_STREAM = "dead_letter_queue"
        self.ORCHESTRATOR_GROUP = "orchestrator_group"

        streams_to_setup = [
            (self.USER_COMMAND_STREAM, self.ORCHESTRATOR_GROUP),
            (self.WORKER_RESULT_STREAM, self.ORCHESTRATOR_GROUP),
            (self.USER_OUTPUT_STREAM, self.ORCHESTRATOR_GROUP) # Add user_output stream
        ]

        for stream_name, group_name in streams_to_setup:
            for i in range(5):
                try:
                    await self.redis_client.xadd(stream_name, {"init": "init"})
                    init_id = (await self.redis_client.xrevrange(stream_name, count=1))[0][0]
                    await self.redis_client.xdel(stream_name, init_id)

                    try:
                        await self.redis_client.xgroup_destroy(stream_name, group_name)
                        logging.info(f"Destroyed existing consumer group {group_name} for {stream_name}")
                    except redis.exceptions.ResponseError as e:
                        if "NOGROUP" not in str(e):
                            logging.warning(f"Could not destroy consumer group {group_name} for {stream_name}: {e}")
                    
                    await self.redis_client.xgroup_create(stream_name, group_name, mkstream=True)
                    logging.info(f"Created consumer group {group_name} for {stream_name}")
                    break
                except Exception as e:
                    logging.warning(f"Attempt {i+1} to setup Redis stream {stream_name} and group {group_name} failed: {e}")
                    await asyncio.sleep(2 ** i)
            else:
                logging.error(f"Failed to setup Redis stream {stream_name} and group {group_name} after multiple retries.")

    async def start(self):
        if self.running:
            logging.info("Orchestrator is already running.")
            return

        await self.setup_redis()

        logging.info("Starting Orchestrator agent...")
        await self.dgraph_client.upsert_agent(self.orchestrator_agent_model)

        self.running = True
        logging.info("Orchestrator started successfully.")

        self.bpmn_engine_task = asyncio.create_task(self.bpmn_engine.run_bpmn_engine_loop(lambda: self.running))
        self.worker_message_processing_task = asyncio.create_task(self._process_worker_messages())
        

        # Main loop for orchestrator logic
        while self.running:
            try:
                # Process user commands
                user_messages = await self.redis_client.xreadgroup(
                    self.ORCHESTRATOR_GROUP, self.orchestrator_agent_model.id,
                    {self.USER_COMMAND_STREAM: '>'},
                    count=1, block=100
                )
                if user_messages:
                    for stream, message_list in user_messages:
                        for message_id, message_data in message_list:
                            parsed_message = json.loads(message_data['message'])
                            message_type = parsed_message.get("type")
                            message_content = parsed_message.get("content")

                            logging.info(f"[ORCHESTRATOR] Received user command: Type={message_type}, Content={message_content}")
                            await self.orchestrator_agent_instance.handle_event("user_command", {"type": message_type, "content": message_content})

            except KeyboardInterrupt:
                logging.info("Exiting orchestrator.")
                self.running = False
                break
            except Exception as e:
                logging.error(f"[ORCHESTRATOR] Unhandled exception in main loop: {e}")
                logging.error(traceback.format_exc())
                await asyncio.sleep(1)

    

    async def _process_worker_messages(self):
        logging.info("[ORCHESTRATOR] Worker message processing loop started.")
        while self.running:
            try:
                messages = await self.redis_client.xreadgroup(
                    self.ORCHESTRATOR_GROUP, self.orchestrator_agent_model.id,
                    {self.WORKER_RESULT_STREAM: '>'},
                    count=1, block=100 # Block for 100ms
                )
                if messages:
                    for stream, message_list in messages:
                        for message_id, message_data in message_list:
                            parsed_message = json.loads(message_data['message'])
                            # Assuming the message from worker_agent.py will contain a 'worker_id'
                            worker_id = parsed_message.get("worker_id", "unknown_worker")
                            await self.bpmn_engine.handle_worker_task_completion(worker_id, parsed_message.get("params", {}).get("task_id"), parsed_message.get("params", {}).get("success"), parsed_message.get("params", {}).get("output_data"))

            except asyncio.CancelledError:
                logging.info("[ORCHESTRATOR] Worker message processing loop cancelled.")
                break
            except Exception as e:
                logging.error(f"[ORCHESTRATOR] Unhandled exception in worker message loop: {e}")
                logging.error(traceback.format_exc())
                await asyncio.sleep(1)

    async def stop(self):
        print("Stopping Orchestrator...")
        if self.bpmn_engine_task:
            self.bpmn_engine_task.cancel()
            try:
                await self.bpmn_engine_task
            except asyncio.CancelledError:
                logging.info("BPMN engine loop cancelled.")
        if self.worker_message_processing_task:
            self.worker_message_processing_task.cancel()
            try:
                await self.worker_message_processing_task
            except asyncio.CancelledError:
                logging.info("Worker message processing loop cancelled.")
        if self.orchestrator_agent_instance:
            # No explicit close method for ReActAgent, but good to have a placeholder
            pass
        self.worker_manager.stop_workers()
        
        if self.dgraph_client:
            await self.dgraph_client.close()
        if self.redis_client:
            await self.redis_client.close()
        self.running = False
        logging.info("Orchestrator stopped.")
