import os
import json
import asyncio
import logging
import uvicorn
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from orchestrator.orchestrator_core import OrchestratorCore

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

# Global variables
orchestrator_instance: Optional[OrchestratorCore] = None
orchestrator_task: Optional[asyncio.Task] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator_instance, orchestrator_task
    logging.info("Starting OrchestratorCore as part of FastAPI lifespan...")
    try:
        # Initialize the orchestrator instance
        orchestrator_instance = OrchestratorCore(cli_directory="C:/Users/vdonc/AMI-SDA/gemini-cli-main/packages/cli")
        
        # Start the orchestrator's main loop as a background task
        orchestrator_task = asyncio.create_task(orchestrator_instance.start())
        
        logging.info("OrchestratorCore has been started in the background.")
        yield
    except Exception as e:
        logging.error(f"Error during OrchestratorCore startup: {e}")
        # Ensure the task is cancelled if startup fails
        if orchestrator_task:
            orchestrator_task.cancel()
        raise
    finally:
        logging.info("Stopping OrchestratorCore as part of FastAPI lifespan...")
        if orchestrator_task:
            orchestrator_task.cancel()
            try:
                await orchestrator_task
            except asyncio.CancelledError:
                logging.info("Orchestrator background task was successfully cancelled.")
        
        if orchestrator_instance:
            await orchestrator_instance.stop()
            
        logging.info("OrchestratorCore stopped.")

app = FastAPI(lifespan=lifespan)

@app.post("/command")
async def process_command(request: Request):
    try:
        data = await request.json()
        command_type = data.get("type")
        command_content = data.get("content")

        if not command_type:
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message": "Command type is required."})

        message_data = {"type": command_type, "content": command_content}
        
        # Publish to Redis stream
        await orchestrator_instance.redis_client.xadd(
            orchestrator_instance.USER_COMMAND_STREAM,
            {"message": json.dumps(message_data)}
        )
        logging.info(f"[API] Received and published command: {command_type}")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": f"Command {command_type} received and queued."})

    except Exception as e:
        logging.error(f"[API] Error processing command: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": f"Internal server error: {e}"})

@app.get("/status")
async def get_orchestrator_status():
    # This endpoint will trigger the STATUS_REQUEST command via Redis
    # and the orchestrator will log the status. For a proper API response,
    # the orchestrator would need to publish status back to a Redis stream
    # that this API could then consume.
    try:
        message_data = {"type": "STATUS_REQUEST", "content": None}
        await orchestrator_instance.redis_client.xadd(
            orchestrator_instance.USER_COMMAND_STREAM,
            {"message": json.dumps(message_data)}
        )
        logging.info("[API] Status request published.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Status request queued. Check orchestrator logs for details."})
    except Exception as e:
        logging.error(f"[API] Error requesting status: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": f"Internal server error: {e}"})

@app.post("/exit")
async def exit_orchestrator():
    try:
        message_data = {"type": "EXIT", "content": None}
        await orchestrator_instance.redis_client.xadd(
            orchestrator_instance.USER_COMMAND_STREAM,
            {"message": json.dumps(message_data)}
        )
        logging.info("[API] Exit command published.")
        return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Exit command queued. Orchestrator will shut down."})
    except Exception as e:
        logging.error(f"[API] Error sending exit command: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message": f"Internal server error: {e}"})

# OpenAI API Emulation Models and Endpoint
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None

class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"

class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-openai-api-emulation"
    object: str = "chat.completion"
    created: int = 0 # Placeholder
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    try:
        user_message_content = None
        for message in request.messages:
            if message.role == "user":
                user_message_content = message.content
                break

        if not user_message_content:
            raise HTTPException(status_code=400, detail="No user message found in request.")

        logging.info(f"[API] Received chat completion request: {user_message_content}")

        # Pass the natural language message to the OrchestratorAgent
        agent_response = await orchestrator_instance.orchestrator_agent_instance.handle_event(
            "natural_language_command",
            {"content": user_message_content}
        )

        # Construct OpenAI-like response
        response_message = ChatMessage(role="assistant", content=str(agent_response))
        response_choice = ChatCompletionResponseChoice(index=0, message=response_message)
        
        return ChatCompletionResponse(
            model=request.model,
            choices=[response_choice],
            created=int(datetime.now().timestamp())
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"[API] Error in chat_completions: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)