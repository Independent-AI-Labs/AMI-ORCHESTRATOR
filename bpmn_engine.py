import logging
import asyncio
import json
from datetime import datetime

from sda.core.bpmn_models import Process, Task, Event, Gateway, ProcessStatus, TaskStatus, EventType, GatewayType
from sda.services.dgraph_client import DgraphClient

class BPMNEngine:
    def __init__(self, dgraph_client: DgraphClient, active_processes: dict, worker_clients: dict, redis_client, dead_letter_queue_stream: str):
        self.dgraph_client = dgraph_client
        self.active_processes = active_processes
        self.worker_clients = worker_clients
        self.redis_client = redis_client
        self.DEAD_LETTER_QUEUE_STREAM = dead_letter_queue_stream

    async def run_bpmn_engine_loop(self, running_flag):
        logging.info("[ORCHESTRATOR] BPMN Engine loop started.")
        while running_flag():
            try:
                for process_id, process in list(self.active_processes.items()):
                    if process.status == ProcessStatus.RUNNING:
                        for element_id in list(process.current_elements_ids):
                            element = await self.dgraph_client.get_bpmn_element(element_id)
                            if isinstance(element, Task):
                                await self._process_task(process, element)
                            elif isinstance(element, Event):
                                await self._process_event(process, element)
                            elif isinstance(element, Gateway):
                                await self._process_gateway(process, element)

                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] {e}")
                await asyncio.sleep(5)

    async def _process_task(self, process: Process, task: Task):
        if task.status == TaskStatus.READY:
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Task '{task.name}' (ID: {task.id}) is READY. Attempting to assign.")

            assigned_worker_id = None
            for worker_id, worker_client in self.worker_clients.items():
                worker_agent = await self.dgraph_client.get_agent(worker_id)
                if worker_agent and worker_agent.status == AgentStatus.IDLE:
                    assigned_worker_id = worker_id
                    break

            if assigned_worker_id:
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Assigning task {task.id} to worker {assigned_worker_id}.")
                task.status = TaskStatus.IN_PROGRESS
                task.assigned_agent_id = assigned_worker_id
                await self.dgraph_client.upsert_task(task)

                worker_agent.status = AgentStatus.BUSY
                worker_agent.current_task_id = task.id
                await self.dgraph_client.upsert_agent(worker_agent)

                worker_client = self.worker_clients[assigned_worker_id]
                task_payload = {
                    "task_id": task.id,
                    "task_name": task.name,
                    "task_type": task.task_type.value,
                    "process_id": process.id,
                    "input_data": task.input_data
                }
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Sending task {task.id} to worker {assigned_worker_id} for execution.")
                await worker_client.send_message("execute_task", task_payload)

            else:
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] No idle worker available for task {task.id}. Retrying later.")

    async def _process_event(self, process: Process, event: Event):
        # Basic event processing: just mark as completed and advance
        if event.event_type == EventType.START_EVENT and event.status != TaskStatus.COMPLETED:
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Processing Start Event '{event.name}' (ID: {event.id}).")
            event.status = TaskStatus.COMPLETED # Using TaskStatus.COMPLETED for events for simplicity
            await self.dgraph_client.upsert_event(event)
            # Advance to next elements based on sequence flows
            outgoing_flows = [flow for flow in process.sequence_flows if flow.source_ref == event.id]
            if outgoing_flows:
                for flow in outgoing_flows:
                    process.current_elements_ids.append(flow.target_ref)
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Event {event.id} completed. Advancing to next elements: {process.current_elements_ids}")
            else:
                process.status = ProcessStatus.COMPLETED
                process.end_time = datetime.now()
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Process '{process.name}' (ID: {process.id}) COMPLETED (no outgoing flows from event {event.id}).")
            await self.dgraph_client.upsert_process(process)
            if process.status == ProcessStatus.COMPLETED:
                self.active_processes.pop(process.id, None)

    async def _process_gateway(self, process: Process, gateway: Gateway):
        if gateway.gateway_type == GatewayType.EXCLUSIVE_GATEWAY and gateway.status != TaskStatus.COMPLETED:
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Processing Exclusive Gateway '{gateway.name}' (ID: {gateway.id}).")
            # For exclusive gateway, we need to evaluate conditions of outgoing sequence flows
            # For now, let's assume a simple decision based on a preceding task's output
            # This needs to be much more sophisticated in a real BPMN engine

            # Find the preceding task that led to this gateway
            preceding_task_id = None
            for flow in process.sequence_flows:
                if flow.target_ref == gateway.id:
                    preceding_task_id = flow.source_ref
                    break

            if preceding_task_id:
                preceding_task = await self.dgraph_client.get_task(preceding_task_id)
                if preceding_task and preceding_task.output_data:
                    try:
                        output_data = json.loads(preceding_task.output_data)
                        # Example condition: if 'data_valid' is true, take the 'valid' path
                        if output_data.get("data_valid") == True:
                            # Find the sequence flow for 'Handle Valid Data' task
                            target_flow = next((flow for flow in process.sequence_flows if flow.source_ref == gateway.id and flow.target_ref == "task_handle_valid"), None)
                            if target_flow:
                                process.current_elements_ids.append(target_flow.target_ref)
                                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Gateway {gateway.id} evaluated to 'Handle Valid Data'.")
                        else:
                            # Find the sequence flow for 'Handle Invalid Data' task
                            target_flow = next((flow for flow in process.sequence_flows if flow.source_ref == gateway.id and flow.target_ref == "task_handle_invalid"), None)
                            if target_flow:
                                process.current_elements_ids.append(target_flow.target_ref)
                                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Gateway {gateway.id} evaluated to 'Handle Invalid Data'.")
                    except json.JSONDecodeError:
                        logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] Preceding task {preceding_task_id} output data is not valid JSON.")
                else:
                    logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] No preceding task output data for gateway {gateway.id}.")
            else:
                logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] No preceding task found for gateway {gateway.id}. Cannot evaluate condition.")

            gateway.status = TaskStatus.COMPLETED # Mark gateway as completed after evaluation
            await self.dgraph_client.upsert_gateway(gateway)
            await self.dgraph_client.upsert_process(process)

    async def handle_worker_task_completion(self, worker_id: str, task_id: str, success: bool, result: str):
        logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Worker {worker_id} reported task {task_id} completion (Success: {success}).")
        task = await self.dgraph_client.get_task(task_id)
        if not task:
            logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] Task {task_id} not found for completion handling.")
            return

        worker_agent = await self.dgraph_client.get_agent(worker_id)
        if not worker_agent:
            logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] Worker agent {worker_id} not found for completion handling.")
            return

        if success:
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()
            task.output_data = result
        else:
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.READY
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Task '{task.name}' (ID: {task.id}) failed. Retrying ({task.retry_count}/{task.max_retries}).")
            else:
                task.status = TaskStatus.FAILED
                task.end_time = datetime.now()
                task.output_data = f"Failed after {task.max_retries} retries: {result}"
                logging.error(f"[ORCHESTRATOR][BPMN_ENGINE] Task '{task.name}' (ID: {task.id}) failed permanently after {task.max_retries} retries.")
                dlq_message = {
                    "task_id": task.id,
                    "process_id": task.process_id,
                    "reason": f"Task failed after {task.max_retries} retries.",
                    "timestamp": datetime.now().isoformat(),
                    "last_output": result
                }
                self.redis_client.xadd(self.DEAD_LETTER_QUEUE_STREAM, {"message": json.dumps(dlq_message)})

        await self.dgraph_client.upsert_task(task)

        worker_agent.status = AgentStatus.IDLE
        worker_agent.current_task_id = None
        await self.dgraph_client.upsert_agent(worker_agent)

        if task.status == TaskStatus.COMPLETED or task.status == TaskStatus.FAILED:
            process = await self.dgraph_client.get_process(task.process_id)
            if process:
                if task.id in process.current_elements_ids:
                    process.current_elements_ids.remove(task.id)

                if task.status == TaskStatus.COMPLETED:
                    outgoing_flows = [flow for flow in process.sequence_flows if flow.source_ref == task.id]
                    if outgoing_flows:
                        for flow in outgoing_flows:
                            process.current_elements_ids.append(flow.target_ref)
                        logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Task {task.id} completed. Advancing to next elements: {process.current_elements_ids}")
                    else:
                        process.status = ProcessStatus.COMPLETED
                        process.end_time = datetime.now()
                        logging.info(
                            f"[ORCHESTRATOR][BPMN_ENGINE] Process '{process.name}' (ID: {process.id}) COMPLETED (no outgoing flows from task {task.id}).")
                    await self.dgraph_client.upsert_process(process)
                    if process.status == ProcessStatus.COMPLETED:
                        self.active_processes.pop(process.id, None)
                elif task.status == TaskStatus.FAILED:
                    process.status = ProcessStatus.FAILED
                    process.end_time = datetime.now()
                    await self.dgraph_client.upsert_process(process)
                    logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Process '{process.name}' (ID: {process.id}) FAILED due to task {task.id}.")
                    self.active_processes.pop(process.id, None)
            else:
                logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] Process {task.process_id} not found for task completion.")
