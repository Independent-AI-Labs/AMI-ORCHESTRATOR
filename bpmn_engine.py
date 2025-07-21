import logging
import asyncio
import json
from datetime import datetime, timedelta

from orchestrator.models.bpmn_models import Process, Task, Event, Gateway, ProcessStatus, TaskStatus, EventType, GatewayType, AgentStatus
from orchestrator.dgraph.dgraph_client import DgraphClient

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

        elif task.status == TaskStatus.COMPLETED:
            # Task is completed, advance the process
            await self._advance_process(process, task.id)
        elif task.status == TaskStatus.FAILED:
            # Task failed, handle accordingly (e.g., move to error handling or end process)
            logging.error(f"[ORCHESTRATOR][BPMN_ENGINE] Task '{task.name}' (ID: {task.id}) FAILED. Process {process.id} will be marked as failed.")
            process.status = ProcessStatus.FAILED
            process.end_time = datetime.now()
            await self.dgraph_client.upsert_process(process)
            self.active_processes.pop(process.id, None)

    async def _process_event(self, process: Process, event: Event):
        if event.status == TaskStatus.COMPLETED:
            return

        if event.event_type == EventType.START_EVENT:
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Processing Start Event '{event.name}' (ID: {event.id}).")
            event.status = TaskStatus.COMPLETED
            await self.dgraph_client.upsert_event(event)
            await self._advance_process(process, event.id)
        elif event.event_type == EventType.END_EVENT:
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Processing End Event '{event.name}' (ID: {event.id}).")
            event.status = TaskStatus.COMPLETED
            await self.dgraph_client.upsert_event(event)
            process.current_elements_ids.remove(event.id) # Remove the end event from current elements
            if not process.current_elements_ids: # If no other active elements, process is completed
                process.status = ProcessStatus.COMPLETED
                process.end_time = datetime.now()
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Process '{process.name}' (ID: {process.id}) COMPLETED.")
                await self.dgraph_client.upsert_process(process)
                self.active_processes.pop(process.id, None)
        elif event.event_type == EventType.ERROR_EVENT:
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Processing Error Event '{event.name}' (ID: {event.id}).")
            event.status = TaskStatus.COMPLETED
            await self.dgraph_client.upsert_event(event)
            process.status = ProcessStatus.FAILED # Mark process as failed on error
            process.end_time = datetime.now()
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Process '{process.name}' (ID: {process.id}) FAILED due to Error Event {event.id}.")
            await self.dgraph_client.upsert_process(process)
            self.active_processes.pop(process.id, None)
        elif event.event_type == EventType.TIMER_EVENT:
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Processing Timer Event '{event.name}' (ID: {event.id}).")
            # Assuming event.input_data contains 'duration' in seconds for simplicity
            # In a real scenario, this would be more sophisticated (e.g., cron expressions)
            if event.status == TaskStatus.READY: # Only process if not already triggered
                if event.start_time is None:
                    event.start_time = datetime.now() # Record when timer started
                    await self.dgraph_client.upsert_event(event)
                    logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Timer Event {event.id} started at {event.start_time}.")
                    return # Not yet completed

                duration_seconds = 0
                try:
                    if event.input_data:
                        input_data = json.loads(event.input_data)
                        duration_seconds = input_data.get("duration", 0)
                except json.JSONDecodeError:
                    logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] Timer Event {event.id} input_data is not valid JSON. Assuming duration 0.")

                if datetime.now() >= (event.start_time + timedelta(seconds=duration_seconds)):
                    event.status = TaskStatus.COMPLETED
                    await self.dgraph_client.upsert_event(event)
                    logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Timer Event {event.id} completed after {duration_seconds} seconds.")
                    await self._advance_process(process, event.id)
                else:
                    logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Timer Event {event.id} not yet completed. Remaining: {(event.start_time + timedelta(seconds=duration_seconds) - datetime.now()).total_seconds():.2f}s")
        else:
            logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] Unsupported Event Type: {event.event_type} for event {event.id}.")

    async def _advance_process(self, process: Process, completed_element_id: str, next_elements_ids: list = None):
        if completed_element_id in process.current_elements_ids:
            process.current_elements_ids.remove(completed_element_id)

        if next_elements_ids:
            for element_id in next_elements_ids:
                if element_id not in process.current_elements_ids:
                    process.current_elements_ids.append(element_id)
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Advancing process {process.id}. Next elements: {process.current_elements_ids}")
        else:
            # If no specific next elements are provided, find outgoing flows from the completed element
            outgoing_flows = [flow for flow in process.sequence_flows if flow.source_ref == completed_element_id]
            if outgoing_flows:
                for flow in outgoing_flows:
                    if flow.target_ref not in process.current_elements_ids:
                        process.current_elements_ids.append(flow.target_ref)
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Advancing process {process.id}. Next elements from outgoing flows: {process.current_elements_ids}")
            elif not process.current_elements_ids: # No outgoing flows and no other active elements
                process.status = ProcessStatus.COMPLETED
                process.end_time = datetime.now()
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Process '{process.name}' (ID: {process.id}) COMPLETED (no outgoing flows from {completed_element_id} and no other active elements).")
                self.active_processes.pop(process.id, None)

        await self.dgraph_client.upsert_process(process)

    async def _process_gateway(self, process: Process, gateway: Gateway):
        if gateway.status == TaskStatus.COMPLETED:
            return

        logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Processing Gateway '{gateway.name}' (ID: {gateway.id}, Type: {gateway.gateway_type}).")

        outgoing_flows = [flow for flow in process.sequence_flows if flow.source_ref == gateway.id]
        next_elements_to_activate = []

        if gateway.gateway_type == GatewayType.EXCLUSIVE_GATEWAY:
            # For exclusive gateway, evaluate conditions and take the first true path
            taken_path = False
            for flow in outgoing_flows:
                # Placeholder for condition evaluation. This needs to be dynamic.
                # For now, let's assume a simple condition based on flow.condition_expression
                # In a real scenario, this would involve evaluating data from preceding tasks/process variables
                condition_met = True # Default to true if no condition specified
                if flow.condition_expression:
                    # This is where a more sophisticated expression evaluator would go
                    # For demonstration, let's assume a simple check for 'data_valid' in a preceding task's output
                    preceding_task_id = None
                    for incoming_flow in process.sequence_flows:
                        if incoming_flow.target_ref == gateway.id:
                            preceding_task_id = incoming_flow.source_ref
                            break

                    if preceding_task_id:
                        preceding_task = await self.dgraph_client.get_task(preceding_task_id)
                        if preceding_task and preceding_task.output_data:
                            try:
                                output_data = json.loads(preceding_task.output_data)
                                # Example: evaluate 'flow.condition_expression' against 'output_data'
                                # This is a very basic example and needs a proper expression engine
                                if flow.condition_expression == "data_valid == True":
                                    condition_met = output_data.get("data_valid") == True
                                elif flow.condition_expression == "data_valid == False":
                                    condition_met = output_data.get("data_valid") == False
                                else:
                                    condition_met = False # Unknown condition, don't take this path
                            except json.JSONDecodeError:
                                logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] Preceding task {preceding_task_id} output data is not valid JSON for gateway {gateway.id}.")
                                condition_met = False
                        else:
                            condition_met = False # No output data to evaluate condition
                    else:
                        condition_met = False # No preceding task to evaluate condition

                if condition_met and not taken_path:
                    next_elements_to_activate.append(flow.target_ref)
                    taken_path = True
                    logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Exclusive Gateway {gateway.id} took path to {flow.target_ref} based on condition.")
                elif condition_met and taken_path:
                    logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] Exclusive Gateway {gateway.id} has multiple true paths. Taking only the first one.")

        elif gateway.gateway_type == GatewayType.PARALLEL_GATEWAY:
            # For parallel gateway, activate all outgoing flows
            for flow in outgoing_flows:
                next_elements_to_activate.append(flow.target_ref)
            logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Parallel Gateway {gateway.id} activating all outgoing paths.")

        elif gateway.gateway_type == GatewayType.INCLUSIVE_GATEWAY:
            # For inclusive gateway, wait for all incoming flows to complete
            # and then activate all outgoing flows whose conditions are met.
            incoming_flows = [flow for flow in process.sequence_flows if flow.target_ref == gateway.id]
            all_incoming_completed = True
            for flow in incoming_flows:
                source_element = await self.dgraph_client.get_bpmn_element(flow.source_ref)
                if not source_element or source_element.status != TaskStatus.COMPLETED:
                    all_incoming_completed = False
                    break

            if all_incoming_completed:
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Inclusive Gateway {gateway.id}: All incoming flows completed. Activating all outgoing flows.")
                for flow in outgoing_flows:
                    next_elements_to_activate.append(flow.target_ref)
            else:
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Inclusive Gateway {gateway.id}: Waiting for all incoming flows to complete.")

        else:
            logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] Unsupported Gateway Type: {gateway.gateway_type} for gateway {gateway.id}.")

        if next_elements_to_activate:
            gateway.status = TaskStatus.COMPLETED
            await self.dgraph_client.upsert_gateway(gateway)
            await self._advance_process(process, gateway.id, next_elements_to_activate)
        else:
            logging.warning(f"[ORCHESTRATOR][BPMN_ENGINE] Gateway {gateway.id} did not activate any outgoing flows.")
            # If no path is taken, the gateway remains active or process might stall. Needs proper error handling.

    async def handle_worker_task_completion(self, task_id: str, success: bool, result: str):
        logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Task {task_id} completion (Success: {success}).")
        task = await self.dgraph_client.get_task(task_id)
        if not task:
            logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] Task {task_id} not found for completion handling.")
            return

        worker_id = task.assigned_agent_id
        if not worker_id:
            logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] Task {task_id} has no assigned worker.")
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

        if task.status == TaskStatus.COMPLETED:
            process = await self.dgraph_client.get_process(task.process_id)
            if process:
                await self._advance_process(process, task.id)
            else:
                logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] Process {task.process_id} not found for task completion.")
        elif task.status == TaskStatus.FAILED:
            process = await self.dgraph_client.get_process(task.process_id)
            if process:
                process.status = ProcessStatus.FAILED
                process.end_time = datetime.now()
                await self.dgraph_client.upsert_process(process)
                logging.info(f"[ORCHESTRATOR][BPMN_ENGINE] Process '{process.name}' (ID: {process.id}) FAILED due to task {task.id}.")
                self.active_processes.pop(process.id, None)
            else:
                logging.error(f"[ORCHESTRATOR][BPMN_ENGINE_ERROR] Process {task.process_id} not found for task failure.")
