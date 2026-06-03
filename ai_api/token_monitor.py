"""
Token Monitoring System for LLM Calls
Tracks input/output tokens, costs, and performance metrics using MLflow and LangGraph
"""

import os
import time
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
import tiktoken
ENABLE_MLFLOW = os.getenv("ENABLE_MLFLOW", "").lower() in {"1", "true", "yes"}
DISABLE_MLFLOW = os.getenv("DISABLE_MLFLOW", "").lower() in {"1", "true", "yes"} or not ENABLE_MLFLOW

if not DISABLE_MLFLOW:
    try:
        import mlflow
        import mlflow.tracking
        from mlflow.exceptions import MlflowException  # type: ignore
        MLFLOW_AVAILABLE = True
    except Exception as mlflow_import_error:  # pragma: no cover - logging only
        mlflow = None  # type: ignore
        MlflowException = Exception  # type: ignore
        MLFLOW_AVAILABLE = False
        print(f"Warning: MLflow import failed ({mlflow_import_error}). Token monitoring will continue without MLflow logging.")
else:
    mlflow = None  # type: ignore
    MlflowException = Exception  # type: ignore
    MLFLOW_AVAILABLE = False
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.callbacks.manager import CallbackManager
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load .env from ai_api directory explicitly
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_env_path, override=False)

AI_CALL_TIMEOUT_SECONDS = float(os.getenv("AI_CALL_TIMEOUT_SECONDS", "120"))
AI_TIMEOUT_MAX_ATTEMPTS = max(1, int(os.getenv("AI_TIMEOUT_MAX_ATTEMPTS", "3")))

@dataclass
class TokenUsage:
    """Data class for tracking token usage"""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    model: str
    timestamp: str
    operation: str
    duration_ms: float

@dataclass
class LLMCall:
    """Data class for tracking complete LLM call information"""
    call_id: str
    operation: str
    model: str
    input_text: str
    output_text: str
    token_usage: TokenUsage
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class TokenTrackingCallback(BaseCallbackHandler):
    """LangChain callback handler for tracking token usage"""
    
    def __init__(self, operation: str, model: str):
        self.operation = operation
        self.model = model
        self.start_time = None
        self.token_usage = None
        
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts"""
        self.start_time = time.time()
        
    def on_llm_end(self, response: Any, **kwargs) -> None:
        """Called when LLM ends"""
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            
            # Extract token usage from response
            if hasattr(response, 'llm_output') and response.llm_output:
                token_usage_data = response.llm_output.get('token_usage', {})
                input_tokens = token_usage_data.get('input_tokens', 0)
                output_tokens = token_usage_data.get('output_tokens', 0)
            else:
                # Fallback: estimate tokens using tiktoken
                input_tokens = self._estimate_tokens(str(response.generations[0][0].text))
                output_tokens = 0
            
            self.token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                input_cost=self._calculate_cost(input_tokens, self.model, 'input'),
                output_cost=self._calculate_cost(output_tokens, self.model, 'output'),
                total_cost=0.0,  # Will be calculated
                model=self.model,
                timestamp=datetime.now().isoformat(),
                operation=self.operation,
                duration_ms=duration_ms
            )
            
            # Calculate total cost
            self.token_usage.total_cost = self.token_usage.input_cost + self.token_usage.output_cost
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken"""
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except:
            # Fallback: rough estimation (4 chars per token)
            return len(text) // 4
    
    def _calculate_cost(self, tokens: int, model: str, token_type: str) -> float:
        """Calculate cost based on model and token type"""
        # LLM pricing per 1M tokens (legacy Claude models kept for reference)
        pricing = {
            # Legacy Anthropic Claude pricing (for reference only)
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-5-sonnet-20240620": {"input": 3.0, "output": 15.0},
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            # Azure OpenAI GPT-5.1 pricing (estimated - adjust based on actual pricing)
            "gpt-5.2-chat": {"input": 0.25, "output": 1.0},
        }
        
        model_pricing = pricing.get(model, {"input": 0.25, "output": 1.0})  # Default to GPT-5.1 pricing
        price_per_1m = model_pricing[token_type]
        return (tokens / 1_000_000) * price_per_1m

class TokenMonitor:
    """Main token monitoring system"""
    
    def __init__(self, experiment_name: str = "seo_analyzer_tokens"):
        self.experiment_name = experiment_name
        self.setup_mlflow()
        self.call_history: List[LLMCall] = []
        self.total_cost = 0.0
        self.total_tokens = 0
        
    def setup_mlflow(self):
        """Setup MLflow tracking"""
        if not MLFLOW_AVAILABLE or mlflow is None:
            self.experiment_id = None
            return
        
        try:
            # Set MLflow tracking URI (can be local or remote)
            mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow_server:5002"))
            
            # Create or get experiment
            try:
                experiment_id = mlflow.create_experiment(self.experiment_name)
            except MlflowException:
                experiment = mlflow.get_experiment_by_name(self.experiment_name)
                experiment_id = experiment.experiment_id if experiment else None
            
            if experiment_id:
                mlflow.set_experiment(self.experiment_name)
                self.experiment_id = experiment_id
            else:
                self.experiment_id = None
            
        except Exception as e:
            print(f"Warning: MLflow setup failed: {e}")
            self.experiment_id = None
    
    async def track_openai_call(self, 
                                 operation: str,
                                 model: str,
                                 messages: List[Dict[str, Any]],
                                 max_tokens: int = 5000,
                                 experiment_name: Optional[str] = None,
                                 client: Optional[AzureOpenAI] = None) -> Dict[str, Any]:
        """Track Azure OpenAI API calls directly"""
        start_time = time.time()
        call_id = f"{operation}_{int(time.time())}"
        
        try:
            # Use provided client or create a new one
            if client is None:
                azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
                api_key = os.getenv("AZURE_OPENAI_API_KEY")
                api_version = os.getenv("AZURE_OPENAI_API_VERSION")
                if not api_key:
                    raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
                client = AzureOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_key=api_key,
                    api_version=api_version
                )
            
            # Prepare messages for Azure OpenAI (simplified format - no cache_control)
            openai_messages = []
            for msg in messages:
                # Convert Anthropic format to OpenAI format
                content = msg.get("content", "")
                
                # Handle content that might be a list (from Anthropic format)
                if isinstance(content, list):
                    # Convert mixed content (text + images) to OpenAI format
                    converted_content = []
                    for block in content:
                        if isinstance(block, dict):
                            block_type = block.get("type")
                            if block_type == "text":
                                # Text block: extract text
                                text = block.get("text", "")
                                if text:
                                    converted_content.append({"type": "text", "text": text})
                            elif block_type == "image":
                                # Image block: convert from Claude format to Azure OpenAI format
                                source = block.get("source", {})
                                if source.get("type") == "base64":
                                    media_type = source.get("media_type", "image/png")
                                    base64_data = source.get("data", "")
                                    if base64_data:
                                        # Azure OpenAI format: data URL
                                        image_url = f"data:{media_type};base64,{base64_data}"
                                        converted_content.append({
                                            "type": "image_url",
                                            "image_url": {
                                                "url": image_url
                                            }
                                        })
                        elif isinstance(block, str):
                            # Plain string: add as text
                            if block.strip():
                                converted_content.append({"type": "text", "text": block})
                    
                    # If we have mixed content, use the list format
                    # If only text, flatten to string for compatibility
                    if converted_content:
                        if len(converted_content) == 1 and converted_content[0].get("type") == "text":
                            content = converted_content[0].get("text", "")
                        else:
                            content = converted_content
                    else:
                        content = ""
                
                # Skip cache_control (Anthropic-specific) but keep all messages
                # Always add the message, ignoring cache_control
                openai_messages.append({
                    "role": msg.get("role", "user"),
                    "content": content
                })
            
            response = None
            last_error: Optional[Exception] = None
            for attempt in range(1, AI_TIMEOUT_MAX_ATTEMPTS + 1):
                try:
                    # Build API call arguments
                    api_kwargs = {
                        "model": model,
                        "messages": openai_messages
                    }
                    if max_tokens:
                        # Azure OpenAI GPT-5.1 uses max_completion_tokens instead of max_tokens
                        api_kwargs["max_completion_tokens"] = max_tokens
                    
                    response = await asyncio.wait_for(
                        asyncio.to_thread(
                            client.chat.completions.create,
                            **api_kwargs
                        ),
                        timeout=AI_CALL_TIMEOUT_SECONDS
                    )
                    break
                except asyncio.TimeoutError as timeout_error:
                    last_error = TimeoutError(
                        f"Azure OpenAI call timed out after {AI_CALL_TIMEOUT_SECONDS}s "
                        f"(attempt {attempt}/{AI_TIMEOUT_MAX_ATTEMPTS})"
                    )
                    if attempt == AI_TIMEOUT_MAX_ATTEMPTS:
                        raise last_error
                    continue
            if response is None:
                raise last_error or RuntimeError("Azure OpenAI call failed without response")
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract token usage
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            # Calculate costs
            input_cost = self._calculate_cost(input_tokens, model, 'input')
            output_cost = self._calculate_cost(output_tokens, model, 'output')
            total_cost = input_cost + output_cost
            
            # Create token usage record
            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                model=model,
                timestamp=datetime.now().isoformat(),
                operation=operation,
                duration_ms=duration_ms
            )
            
            # Create LLM call record
            llm_call = LLMCall(
                call_id=call_id,
                operation=operation,
                model=model,
                input_text=str(messages),
                output_text=response.choices[0].message.content,
                token_usage=token_usage,
                success=True,
                metadata={"max_tokens": max_tokens}
            )
            
            # Log to MLflow
            self._log_to_mlflow(llm_call, experiment_name=experiment_name)
            
            # Update totals
            self.total_cost += total_cost
            self.total_tokens += token_usage.total_tokens
            self.call_history.append(llm_call)
            
            return {
                "response": response.choices[0].message.content,
                "token_usage": asdict(token_usage),
                "call_id": call_id
            }
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Create error record
            error_call = LLMCall(
                call_id=call_id,
                operation=operation,
                model=model,
                input_text=str(messages),
                output_text="",
                token_usage=TokenUsage(
                    input_tokens=0, output_tokens=0, total_tokens=0,
                    input_cost=0.0, output_cost=0.0, total_cost=0.0,
                    model=model, timestamp=datetime.now().isoformat(),
                    operation=operation, duration_ms=duration_ms
                ),
                success=False,
                error_message=str(e)
            )
            
            self.call_history.append(error_call)
            raise e
    
    def _calculate_cost(self, tokens: int, model: str, token_type: str) -> float:
        """Calculate cost based on model and token type"""
        # LLM pricing per 1M tokens (legacy Claude models kept for reference)
        pricing = {
            # Legacy Anthropic Claude pricing (for reference only)
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-5-sonnet-20240620": {"input": 3.0, "output": 15.0},
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
            # Azure OpenAI GPT-5.1 pricing (estimated - adjust based on actual pricing)
            "gpt-5.2-chat": {"input": 0.5, "output": 2.0},
        }
        
        model_pricing = pricing.get(model, {"input": 0.5, "output": 2.0})  # Default to GPT-5.1 pricing
        price_per_1m = model_pricing[token_type]
        return (tokens / 1_000_000) * price_per_1m
    
    def _log_to_mlflow(self, llm_call: LLMCall, experiment_name: Optional[str] = None):
        """Log LLM call to MLflow"""
        if not MLFLOW_AVAILABLE or mlflow is None:
            return
        
        if experiment_name:
            try:
                try:
                    exp_id = mlflow.create_experiment(experiment_name)
                except MlflowException:
                    exp = mlflow.get_experiment_by_name(experiment_name)
                    exp_id = exp.experiment_id if exp else None
                if exp_id:
                    mlflow.set_experiment(experiment_name)
            except Exception as e:
                print(f"Warning: Failed to switch MLflow experiment: {e}")
        elif not self.experiment_id:
            return
            
        try:
            with mlflow.start_run(run_name=f"{llm_call.operation}_{llm_call.call_id}"):
                # Log metrics
                mlflow.log_metric("input_tokens", llm_call.token_usage.input_tokens)
                mlflow.log_metric("output_tokens", llm_call.token_usage.output_tokens)
                mlflow.log_metric("total_tokens", llm_call.token_usage.total_tokens)
                mlflow.log_metric("input_cost", llm_call.token_usage.input_cost)
                mlflow.log_metric("output_cost", llm_call.token_usage.output_cost)
                mlflow.log_metric("total_cost", llm_call.token_usage.total_cost)
                mlflow.log_metric("duration_ms", llm_call.token_usage.duration_ms)
                
                # Log parameters
                mlflow.log_param("model", llm_call.model)
                mlflow.log_param("operation", llm_call.operation)
                mlflow.log_param("success", llm_call.success)
                
                # Log tags
                mlflow.set_tag("call_id", llm_call.call_id)
                mlflow.set_tag("timestamp", llm_call.token_usage.timestamp)
                
                # Log artifacts (input/output text)
                if llm_call.input_text:
                    mlflow.log_text(llm_call.input_text, "input.txt")
                if llm_call.output_text:
                    mlflow.log_text(llm_call.output_text, "output.txt")
                
        except Exception as e:
            print(f"Warning: Failed to log to MLflow: {e}")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of token usage"""
        if not self.call_history:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "average_cost_per_call": 0.0,
                "average_tokens_per_call": 0.0,
                "cost_by_operation": {},
                "cost_by_model": {},
                "recent_calls": []
            }
        
        successful_calls = [call for call in self.call_history if call.success]
        
        return {
            "total_calls": len(self.call_history),
            "successful_calls": len(successful_calls),
            "failed_calls": len(self.call_history) - len(successful_calls),
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "average_cost_per_call": self.total_cost / len(successful_calls) if successful_calls else 0,
            "average_tokens_per_call": self.total_tokens / len(successful_calls) if successful_calls else 0,
            "cost_by_operation": self._get_cost_by_operation(),
            "cost_by_model": self._get_cost_by_model(),
            "recent_calls": [asdict(call) for call in self.call_history[-10:]]
        }
    
    def _get_cost_by_operation(self) -> Dict[str, float]:
        """Get cost breakdown by operation"""
        cost_by_op = {}
        for call in self.call_history:
            if call.success:
                op = call.operation
                cost_by_op[op] = cost_by_op.get(op, 0) + call.token_usage.total_cost
        return cost_by_op
    
    def _get_cost_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model"""
        cost_by_model = {}
        for call in self.call_history:
            if call.success:
                model = call.model
                cost_by_model[model] = cost_by_model.get(model, 0) + call.token_usage.total_cost
        return cost_by_model
    
    def export_usage_data(self, filepath: str = None) -> str:
        """Export usage data to JSON file"""
        if not filepath:
            filepath = f"token_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "summary": self.get_usage_summary(),
            "call_history": [asdict(call) for call in self.call_history],
            "exported_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath

# Global token monitor instance
token_monitor = TokenMonitor()

# Decorator for easy token tracking
def track_tokens(operation: str, model: str = "gpt-5.2-chat"):
    """Decorator to automatically track token usage for functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract messages from function arguments
            messages = []
            if 'prompt' in kwargs:
                messages = [{"role": "user", "content": kwargs['prompt']}]
            elif 'seo_data' in kwargs:
                # For SEO analysis functions
                messages = [{"role": "user", "content": f"Analyze SEO data for {kwargs['seo_data'].get('url', 'unknown')}"}]
            elif 'social_data' in kwargs:
                # For social analysis functions
                messages = [{"role": "user", "content": f"Analyze social data for {kwargs['social_data'].get('url', 'unknown')}"}]
            
            if messages:
                return await token_monitor.track_openai_call(operation, model, messages)
            else:
                # Fallback: call original function
                return await func(*args, **kwargs)
        return wrapper
    return decorator