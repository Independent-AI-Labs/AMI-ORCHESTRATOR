import logging
import json
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.gemini import Gemini

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class OrchestratorAgent:
    async def list_agents(self) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Listing all agents.")
        try:
            query = '''{
                agents(func: has(agent_type)) {
                    uid
                    expand(_all_)
                }
            }'''
            results = await self.dgraph_client.query(query)
            if not results:
                return "No agents found."
            return json.dumps(results)
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error listing agents: {e}")
            return f"Error listing agents: {e}"

    async def get_worker_status(self, worker_id: str) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Getting status for worker {worker_id}")
        try:
            agent = await self.dgraph_client.get_agent(worker_id)
            if agent:
                return f"Worker {worker_id} status: {agent.status}"
            return f"Worker {worker_id} not found."
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error getting worker status: {e}")
            return f"Error getting worker status: {e}"

    def __init__(self, orchestrator_core_instance, dgraph_client, worker_manager, redis_client, user_command_stream, worker_result_stream, dead_letter_queue_stream, user_output_stream, google_api_key: str):
        self.orchestrator_core_instance = orchestrator_core_instance
        self.dgraph_client = dgraph_client
        self.worker_manager = worker_manager
        self.redis_client = redis_client
        self.user_command_stream = user_command_stream
        self.worker_result_stream = worker_result_stream
        self.dead_letter_queue_stream = dead_letter_queue_stream
        self.user_output_stream = user_output_stream

        self.google_api_key = google_api_key

        # Initialize LLM
        self.llm = Gemini(api_key=self.google_api_key)

        self.tools = [
            FunctionTool.from_defaults(fn=self.create_worker, name="create_worker", description="Creates a new worker agent."),
            FunctionTool.from_defaults(fn=self.get_worker_status, name="get_worker_status", description="Gets the status of a worker."),
            FunctionTool.from_defaults(fn=self.send_message_to_user, name="send_message_to_user", description="Sends a message to the user."),
            FunctionTool.from_defaults(fn=self.inspect_worker_output, name="inspect_worker_output", description="Inspects the output of a worker."),
            FunctionTool.from_defaults(fn=self.send_message_to_worker, name="send_message_to_worker", description="Sends a message to a specific worker."),
            FunctionTool.from_defaults(fn=self.query_dgraph, name="query_dgraph", description="Queries the Dgraph database with a DQL query. Returns JSON results."),
            FunctionTool.from_defaults(fn=self.list_agents, name="list_agents", description="Lists all agents in the system."),
            FunctionTool.from_defaults(fn=self.start_bpmn_process, name="start_bpmn_process", description="Starts a BPMN process given its process definition ID."),
            FunctionTool.from_defaults(fn=self.stop_orchestrator, name="stop_orchestrator", description="Stops the orchestrator gracefully."),
            # Add more tools as needed based on orchestrator logic
        ]

        self.agent = ReActAgent.from_tools(self.tools, llm=self.llm, verbose=True)

    async def handle_event(self, event_type: str, event_data: dict):
        # This method will be the event-driven entrypoint for the agent
        # The agent will process the event and decide on actions using its tools
        logging.info(f"[OrchestratorAgent] Handling event: {event_type} with data: {event_data}")

        if event_type == "user_command" and event_data.get("type") == "EXIT":
            logging.info("[OrchestratorAgent] Received EXIT command. Calling stop_orchestrator tool.")
            return await self.stop_orchestrator()

        response = await self.agent.achat(f"Event Type: {event_type}, Event Data: {event_data}")
        logging.info(f"[OrchestratorAgent] Agent Response: {response}")
        return response

    # --- Agent Tools --- #

    async def create_worker(self, worker_id: str) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Creating worker: {worker_id}")
        try:
            await self.worker_manager.spawn_worker(worker_id)
            return f"Worker {worker_id} created successfully."
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error creating worker {worker_id}: {e}")
            return f"Error creating worker {worker_id}: {e}"

    async def send_message_to_user(self, message: str) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Sending message to user: {message}")
        try:
            await self.redis_client.xadd(self.user_output_stream, {'message': message})
            return f"Message sent to user: {message}"
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error sending message to user: {e}")
            return f"Error sending message to user: {e}"

    async def inspect_worker_output(self, worker_id: str, task_id: str) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Inspecting output for worker {worker_id}, task {task_id}")
        # This tool would query Dgraph for task output data
        try:
            task = await self.dgraph_client.get_task(task_id)
            if task and task.output_data:
                return f"Output for task {task_id} from worker {worker_id}: {task.output_data}"
            return f"No output found for task {task_id} from worker {worker_id}."
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error inspecting worker output: {e}")
            return f"Error inspecting worker output: {e}"

    async def send_message_to_worker(self, worker_id: str, message: str) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Sending message to worker {worker_id}: {message}")
        try:
            worker_command_stream = f"worker_commands:{worker_id}"
            await self.redis_client.xadd(worker_command_stream, {'message': message})
            return f"Message sent to worker {worker_id}: {message}"
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error sending message to worker {worker_id}: {e}")
            return f"Error sending message to worker {worker_id}: {e}"

    async def query_dgraph(self, query: str) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Querying Dgraph: {query}")
        try:
            results = await self.dgraph_client.query(query)
            return json.dumps(results)
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error querying Dgraph: {e}")
            return f"Error querying Dgraph: {e}"

    async def start_bpmn_process(self, process_definition_id: str) -> str:
        logging.info(f"[OrchestratorAgent][Tool] Starting BPMN process: {process_definition_id}")
        try:
            # This will trigger the process_definitions_loader to start the process
            # The orchestrator_core_instance has access to process_definitions_loader
            await self.orchestrator_core_instance.process_definitions_loader.start_bpmn_process(process_definition_id)
            return f"BPMN process {process_definition_id} started successfully."
        except Exception as e:
            logging.error(f"[OrchestratorAgent][Tool] Error starting BPMN process {process_definition_id}: {e}")
            return f"Error starting BPMN process {process_definition_id}: {e}"

    async def stop_orchestrator(self) -> str:
        logging.info("[OrchestratorAgent][Tool] Stopping orchestrator via tool call.")
        self.orchestrator_core_instance.running = False
        return "Orchestrator stop signal sent."