"""
REST API for the Orchestrator.
"""

from flask import Flask, jsonify, request

from orchestrator.bpmn.engine import BpmnEngine
from orchestrator.core.dgraph_client import DgraphClient
from orchestrator.core.prometheus_client import PrometheusClient
from orchestrator.core.redis_client import RedisClient
from orchestrator.core.security import SecurityManager
from orchestrator.core.worker_manager import WorkerManager

app = Flask(__name__)

dgraph_client = DgraphClient()
redis_client = RedisClient()
security_manager = SecurityManager()
prometheus_client = PrometheusClient()
worker_manager = WorkerManager(redis_client)
bpmn_engine = BpmnEngine(dgraph_client, security_manager, redis_client, prometheus_client, worker_manager)


@app.route("/api/processes/<process_name>/start", methods=["POST"])
def start_process(process_name):
    """Start a new process instance."""
    user = request.headers.get("X-User", "admin")
    variables = request.json
    process_instance_id = bpmn_engine.start_process(f"orchestrator/bpmn/definitions/{process_name}.json", user, variables)
    return jsonify({"id": process_instance_id})


@app.route("/api/processes/instances/<process_instance_id>", methods=["GET"])
def get_process_instance(process_instance_id):
    """Get the status of a process instance."""
    # This is a placeholder for the actual implementation.
    return jsonify({"id": process_instance_id, "status": "COMPLETED"})


if __name__ == "__main__":
    app.run(port=8080)
