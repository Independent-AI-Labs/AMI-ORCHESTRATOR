import logging
import asyncio
import subprocess
import threading
import json
import os
import sys

from orchestrator.models.bpmn_models import Agent, AgentType, AgentStatus
from orchestrator.dgraph.dgraph_client import DgraphClient

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

class WorkerManager:
    def __init__(self, dgraph_client: DgraphClient, worker_clients: dict, worker_message_queue: asyncio.Queue):
        self.dgraph_client = dgraph_client
        self.worker_clients = worker_clients
        self.worker_message_queue = worker_message_queue

    async def spawn_worker(self, worker_id: str):
        if worker_id in self.worker_clients:
            logging.info(f"Worker '{worker_id}' already exists.")
            return False

        logging.info(f"Spawning worker client '{worker_id}'...")
        new_worker_agent = Agent(id=worker_id, name=f"Worker Agent {worker_id}", agent_type=AgentType.WORKER, status=AgentStatus.IDLE)
        await self.dgraph_client.upsert_agent(new_worker_agent)

        try:
            worker_env = os.environ.copy()
            worker_env["WORKER_ID"] = worker_id

            command = [
                sys.executable,
                os.path.join("C:/Users/vdonc/AMI-SDA/sda/services/worker_agent.py"),
                worker_id
            ]

            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=worker_env
            )
            self.worker_clients[worker_id] = process
            logging.info(f"Worker '{worker_id}' process started successfully.")

            threading.Thread(target=self._enqueue_worker_stream_output, args=(process.stdout, f"WORKER_STDOUT_{worker_id}"), daemon=True).start()
            threading.Thread(target=self._enqueue_worker_stream_output, args=(process.stderr, f"WORKER_STDERR_{worker_id}"), daemon=True).start()

            return True
        except Exception as e:
            logging.error(f"Failed to start worker client '{worker_id}': {e}")
            return False

    def _enqueue_worker_stream_output(self, stream, stream_name):
        for line in iter(stream.readline, ''):
            try:
                message = json.loads(line.strip())
                asyncio.run_coroutine_threadsafe(self.worker_message_queue.put(message), asyncio.get_event_loop())
            except json.JSONDecodeError:
                logging.info(f"[{stream_name}] {line.strip()}")
            except Exception as e:
                logging.error(f"[{stream_name}] Error processing stream line: {e} - {line.strip()}")

    def stop_workers(self):
        for worker_id, process in self.worker_clients.items():
            print(f"Stopping worker process '{worker_id}'...")
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"Worker process '{worker_id}' terminated.")
                except subprocess.TimeoutExpired:
                    print(f"Worker process '{worker_id}' did not terminate gracefully, killing it.")
                    process.kill()
                    process.wait()
                except Exception as e:
                    print(f"Error during worker process termination for '{worker_id}': {e}")
