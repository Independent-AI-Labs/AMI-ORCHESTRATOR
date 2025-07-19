import logging
import asyncio
import redis
import subprocess
import threading
import json

from gemini_acp_client import GeminiACPClient
from sda.core.bpmn_models import Agent, AgentType
from sda.services.dgraph_client import DgraphClient
from orchestrator.bpmn_engine import BPMNEngine
from orchestrator.worker_manager import WorkerManager
from orchestrator.user_interface import UserInterface
from orchestrator.process_definitions_loader import ProcessDefinitionsLoader

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class OrchestratorCore:
    def __init__(self, cli_directory: str, dgraph_url: str = "localhost:9080"):
        self.cli_directory = cli_directory
        self.dgraph_client = DgraphClient(dgraph_url=dgraph_url)
        self.orchestrator_agent = Agent(id="orchestrator-agent", name="Orchestrator Agent", agent_type=AgentType.ORCHESTRATOR, status=AgentStatus.IDLE)
        self.orchestrator_client = None
        self.worker_clients = {}
        self.worker_message_queue = asyncio.Queue()
        self.running = False
        self.active_processes = {}
        self.bpmn_engine_task = None
        self.worker_message_processing_task = None

        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.USER_COMMAND_STREAM = "user_commands"
        self.WORKER_RESULT_STREAM = "worker_results"
        self.DEAD_LETTER_QUEUE_STREAM = "dead_letter_queue"
        self.ORCHESTRATOR_GROUP = "orchestrator_group"

        try:
            self.redis_client.xgroup_create(self.USER_COMMAND_STREAM, self.ORCHESTRATOR_GROUP, mkstream=True)
        except redis.exceptions.DataError:
            logging.info(f"Consumer group {self.ORCHESTRATOR_GROUP} already exists for {self.USER_COMMAND_STREAM}")
        try:
            self.redis_client.xgroup_create(self.WORKER_RESULT_STREAM, self.ORCHESTRATOR_GROUP, mkstream=True)
        except redis.exceptions.DataError:
            logging.info(f"Consumer group {self.ORCHESTRATOR_GROUP} already exists for {self.WORKER_RESULT_STREAM}")

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
        self.user_interface = UserInterface(
            redis_client=self.redis_client,
            user_command_stream=self.USER_COMMAND_STREAM
        )
        self.process_definitions_loader = ProcessDefinitionsLoader(
            dgraph_client=self.dgraph_client,
            active_processes=self.active_processes
        )

    async def start(self):
        if self.running:
            logging.info("Orchestrator is already running.")
            return

        logging.info("Starting Orchestrator client...")
        await self.dgraph_client.upsert_agent(self.orchestrator_agent)

        self.orchestrator_client = GeminiACPClient(
            cli_directory=self.cli_directory,
            on_message_callback=self._orchestrator_message_handler
        )
        if not self.orchestrator_client.start_cli():
            logging.error("Failed to start Orchestrator client. Exiting.")
            return

        self.running = True
        logging.info("Orchestrator started successfully.")

        self.bpmn_engine_task = asyncio.create_task(self.bpmn_engine.run_bpmn_engine_loop(lambda: self.running))
        self.worker_message_processing_task = asyncio.create_task(self._process_worker_messages())
        self.user_interface.start_input_thread()

        # Main loop for orchestrator logic (will be simplified later)
        while self.running:
            try:
                # This part will be moved to user_interface.py
                messages = self.redis_client.xreadgroup(
                    self.ORCHESTRATOR_GROUP, self.orchestrator_agent.id,
                    {self.USER_COMMAND_STREAM: '>'},
                    count=1, block=100
                )
                if messages:
                    for stream, message_list in messages:
                        for message_id, message_data in message_list:
                            parsed_message = json.loads(message_data[b'message'].decode('utf-8'))
                            message_type = parsed_message.get("type")
                            message_content = parsed_message.get("content")

                            if message_type == "EXIT":
                                self.running = False
                                break
                            elif message_type == "SPAWN_WORKER":
                                logging.info(f"[ORCHESTRATOR] Spawning worker: {message_content}")
                                await self.worker_manager.spawn_worker(message_content)
                            elif message_type == "STATUS_REQUEST":
                                logging.info("[ORCHESTRATOR] Processing Status Request:")
                                logging.info("--- Active Processes ---")
                                if not self.active_processes:
                                    logging.info("No active processes.")
                                for pid, process in self.active_processes.items():
                                    logging.info(f"  Process ID: {pid}, Name: {process.name}, Status: {process.status.value}")
                                    logging.info(f"    Current Elements: {process.current_elements_ids}")
                                logging.info("--- Worker Agents ---")
                                if not self.worker_clients:
                                    logging.info("No worker agents spawned.")
                                for worker_id, process_obj in self.worker_clients.items():
                                    agent_status = "UNKNOWN"
                                    agent_task = "None"
                                    try:
                                        agent_model = await self.dgraph_client.get_agent(worker_id)
                                        if agent_model:
                                            agent_status = agent_model.status.value
                                            agent_task = agent_model.current_task_id if agent_model.current_task_id else "None"
                                    except Exception as e:
                                        logging.warning(f"Could not retrieve Dgraph status for worker {worker_id}: {e}")
                                    logging.info(
                                        f"  Worker ID: {worker_id}, Process Status: {process_obj.poll()}, Agent Status: {agent_status}, Current Task: {agent_task}")
                                logging.info("----------------------")
                            elif message_type == "START_BPMN_PROCESS":
                                logging.info(f"[ORCHESTRATOR] Starting BPMN Process: {message_content}")
                                await self.process_definitions_loader.start_bpmn_process(message_content)
                            # Other message types will be handled by other modules
                if not self.running:
                    break

            except KeyboardInterrupt:
                logging.info("Exiting orchestrator.")
                self.running = False
                break
            except Exception as e:
                logging.error(f"[ORCHESTRATOR][ERROR] {e}")
                await asyncio.sleep(1)

    async def _orchestrator_message_handler(self, message):
        logging.debug(f"[ORCHESTRATOR_CLIENT_MSG] {message}")

    async def _process_worker_messages(self):
        logging.info("[ORCHESTRATOR] Worker message processing loop started.")
        while self.running:
            try:
                messages = self.redis_client.xreadgroup(
                    self.ORCHESTRATOR_GROUP, self.orchestrator_agent.id,
                    {self.WORKER_RESULT_STREAM: '>'},
                    count=1, block=100 # Block for 100ms
                )
                if messages:
                    for stream, message_list in messages:
                        for message_id, message_data in message_list:
                            parsed_message = json.loads(message_data[b'message'].decode('utf-8'))
                            # Assuming the message from worker_agent.py will contain a 'worker_id'
                            worker_id = parsed_message.get("worker_id", "unknown_worker")
                            await self.bpmn_engine.handle_worker_task_completion(worker_id, parsed_message.get("params", {}).get("task_id"), parsed_message.get("params", {}).get("success"), parsed_message.get("params", {}).get("output_data"))

            except asyncio.CancelledError:
                logging.info("[ORCHESTRATOR] Worker message processing loop cancelled.")
                break
            except Exception as e:
                logging.error(f"[ORCHESTRATOR][WORKER_MSG_ERROR] {e}")
                await asyncio.sleep(1) # Prevent tight loop on errors

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
        if self.orchestrator_client:
            self.orchestrator_client.close()
        self.worker_manager.stop_workers()
        self.user_interface.stop_input_thread()
        if self.dgraph_client:
            await self.dgraph_client.close()
        self.running = False
        logging.info("Orchestrator stopped.")
