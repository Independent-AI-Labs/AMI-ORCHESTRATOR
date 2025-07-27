import json
import os

from dotenv import load_dotenv
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.llms.openai import OpenAI

from orchestrator.bpmn.models import Resource
from orchestrator.core.redis_client import RedisClient
from orchestrator.core.worker_manager import WorkerManager

# Load environment variables from .env file
load_dotenv()

# 1. Initialize necessary components
redis_client = RedisClient()
worker_manager = WorkerManager(redis_client)


# 2. Define tool functions that wrap WorkerManager methods
def register_worker(worker_id: str, capabilities: str, resources: str = "GENERIC") -> str:
    """
    Registers a new worker with the orchestrator.

    Args:
        worker_id (str): A unique identifier for the worker.
        capabilities (str): A comma-separated list of capabilities the worker possesses (e.g., 'file_read,file_write').
        resources (str): A comma-separated list of resource pools the worker belongs to.
                         Valid options are: GENERIC, CPU_INTENSIVE, GPU_INTENSIVE, MEMORY_INTENSIVE.
                         Defaults to 'GENERIC'.
    """
    try:
        cap_list = [c.strip() for c in capabilities.split(",")]

        res_list_str = [r.strip().upper() for r in resources.split(",")]
        res_list_enum = []
        for r_str in res_list_str:
            if r_str in Resource.__members__:
                res_list_enum.append(Resource[r_str])
            else:
                return f"Error: Invalid resource '{r_str}'. Valid options are: {", ".join(Resource.__members__)}"

        worker_manager.register_worker(worker_id, cap_list, res_list_enum)
        return f"Successfully registered worker '{worker_id}' with capabilities {cap_list} and resources {res_list_str}."
    except (ValueError, TypeError) as e:
        return f"Error registering worker: {e}"


def get_registered_workers() -> str:
    """
    Retrieves a list of all currently registered workers and their configurations.
    """
    workers = worker_manager.get_workers()
    if not workers:
        return "No workers are currently registered."
    return json.dumps(workers, indent=2, default=lambda o: o.name if isinstance(o, Resource) else str(o))


# 3. Create Llama Index FunctionTools
register_worker_tool = FunctionTool.from_defaults(
    fn=register_worker, name="register_worker", description="Use this tool to register a new worker process with the orchestrator."
)

get_workers_tool = FunctionTool.from_defaults(
    fn=get_registered_workers,
    name="get_registered_workers",
    description="Use this tool to get a list of all workers currently registered with the orchestrator.",
)

# 4. Initialize the LLM and Agent
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

llm = OpenAI(model="gpt-4-0613", api_key=api_key)
tools: list[BaseTool] = [register_worker_tool, get_workers_tool]
agent = ReActAgent.from_tools(tools, llm=llm, verbose=True)

# 5. Main execution loop
if __name__ == "__main__":
    print("Orchestrator Agent is running. Type 'exit' to quit.")
    # Example of how to run in a loop
    # while True:
    #     prompt = input("Enter a prompt: ")
    #     if prompt.lower() == "exit":
    #         break
    #     response = agent.chat(prompt)
    #     print(str(response))
    print("Agent initialized successfully with worker management tools.")
