"""Wrapper for LangChain LLMs to log invocations to database."""

import time
from typing import Any, Dict, List, Optional, Union
from contextvars import ContextVar

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun

from app.repositories.llm_invocation_repository import LLMInvocationRepository

logger = structlog.get_logger(__name__)

# Context variables for tracking current context
current_user_id: ContextVar[Optional[int]] = ContextVar('current_user_id', default=None)
current_playlist_id: ContextVar[Optional[int]] = ContextVar('current_playlist_id', default=None)
current_session_id: ContextVar[Optional[str]] = ContextVar('current_session_id', default=None)
current_agent_name: ContextVar[Optional[str]] = ContextVar('current_agent_name', default=None)
current_operation: ContextVar[Optional[str]] = ContextVar('current_operation', default=None)


class LoggingChatModel(BaseChatModel):
    """Wrapper around LangChain chat models that logs invocations to database.
    
    This wrapper intercepts calls to the underlying LLM and logs:
    - Input prompts and messages
    - Output responses
    - Token usage
    - Latency
    - Cost estimates
    - Context (user, session, agent, operation)
    
    Multi-worker Safety:
    - Uses ContextVars for async task isolation
    - Safe to share a single instance across multiple concurrent workflows
    - Each workflow's context (session_id, user_id, etc.) is isolated per async task
    - Creates a new database session for each logging operation to prevent
      concurrent access issues
    
    Usage:
        llm = ChatOpenAI(model="gpt-4", temperature=0.7)
        logged_llm = LoggingChatModel(llm)
        
        # Set context (automatically uses ContextVars for isolation)
        logged_llm.set_context(
            user_id=123,
            session_id="abc-123",
            agent_name="MoodAnalyzer"
        )
        
        # Use normally
        response = logged_llm.invoke("Hello")
    """
    
    wrapped_llm: BaseChatModel
    provider: Optional[str] = None
    enable_logging: bool = True
    log_full_response: bool = True
    
    # Context for logging
    # Note: These are fallback values. Primary context is stored in ContextVars
    # for async task isolation (multi-worker safety)
    _user_id: Optional[int] = None
    _playlist_id: Optional[int] = None
    _session_id: Optional[str] = None
    _agent_name: Optional[str] = None
    _operation: Optional[str] = None
    _context_metadata: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        wrapped_llm: BaseChatModel,
        provider: Optional[str] = None,
        enable_logging: bool = True,
        log_full_response: bool = True,
        **kwargs
    ):
        """Initialize the logging wrapper.
        
        Args:
            wrapped_llm: The underlying LangChain chat model to wrap
            provider: LLM provider name (e.g., "openai", "anthropic", "openrouter")
            enable_logging: Whether to enable logging
            log_full_response: Whether to log full response or just metadata
        """
        super().__init__(wrapped_llm=wrapped_llm, **kwargs)
        self.wrapped_llm = wrapped_llm
        self.provider = provider or self._infer_provider(wrapped_llm)
        self.enable_logging = enable_logging
        self.log_full_response = log_full_response

    def set_context(
        self,
        user_id: Optional[int] = None,
        playlist_id: Optional[int] = None,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None,
        context_metadata: Optional[Dict[str, Any]] = None
    ):
        """Set context for logging using ContextVars (thread-safe for async).
        
        ContextVars are isolated per asyncio task, making this safe for
        concurrent workflows in multi-worker setups.
        
        Args:
            user_id: User ID
            playlist_id: Playlist ID
            session_id: Workflow session ID
            agent_name: Name of the agent making the call
            operation: Operation being performed
            context_metadata: Additional context metadata
        """
        if user_id is not None:
            current_user_id.set(user_id)
            self._user_id = user_id  # Keep for backwards compatibility
        if playlist_id is not None:
            current_playlist_id.set(playlist_id)
            self._playlist_id = playlist_id
        if session_id is not None:
            current_session_id.set(session_id)
            self._session_id = session_id
        if agent_name is not None:
            current_agent_name.set(agent_name)
            self._agent_name = agent_name
        if operation is not None:
            current_operation.set(operation)
            self._operation = operation
        if context_metadata is not None:
            self._context_metadata = context_metadata

    def _infer_provider(self, llm: BaseChatModel) -> str:
        """Infer the provider from the LLM class name."""
        class_name = llm.__class__.__name__.lower()
        if 'openai' in class_name:
            return 'openai'
        elif 'anthropic' in class_name:
            return 'anthropic'
        elif 'google' in class_name or 'gemini' in class_name:
            return 'google'
        elif 'cohere' in class_name:
            return 'cohere'
        else:
            return 'unknown'

    def _extract_model_config(self) -> Dict[str, Any]:
        """Extract model configuration from the wrapped LLM."""
        config = {}
        
        # Try to get common attributes
        if hasattr(self.wrapped_llm, 'model_name'):
            config['model_name'] = self.wrapped_llm.model_name
        elif hasattr(self.wrapped_llm, 'model'):
            config['model_name'] = self.wrapped_llm.model
        else:
            config['model_name'] = 'unknown'
            
        if hasattr(self.wrapped_llm, 'temperature'):
            config['temperature'] = self.wrapped_llm.temperature
            
        if hasattr(self.wrapped_llm, 'max_tokens'):
            config['max_tokens'] = self.wrapped_llm.max_tokens
            
        return config

    def _messages_to_dict(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        """Convert messages to dictionary format for logging."""
        return [
            {
                'role': msg.type,
                'content': msg.content
            }
            for msg in messages
        ]

    def _convert_to_messages(self, input_messages: Union[List[BaseMessage], List[Dict[str, str]]]) -> List[BaseMessage]:
        """Convert input messages to BaseMessage objects."""
        if not input_messages:
            return []

        # Check if already BaseMessage objects
        if isinstance(input_messages[0], BaseMessage):
            return input_messages

        # Convert dictionaries to BaseMessage objects
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        messages = []
        for msg_dict in input_messages:
            role = msg_dict.get('role', '').lower()
            content = msg_dict.get('content', '')

            if role == 'user' or role == 'human':
                messages.append(HumanMessage(content=content))
            elif role == 'assistant' or role == 'ai':
                messages.append(AIMessage(content=content))
            elif role == 'system':
                messages.append(SystemMessage(content=content))
            else:
                # Default to HumanMessage for unknown roles
                messages.append(HumanMessage(content=content))

        return messages

    def _extract_prompt_from_messages(self, messages: List[BaseMessage]) -> str:
        """Extract a string representation of the prompt from messages."""
        return "\n".join([f"{msg.type}: {msg.content}" for msg in messages])

    def _calculate_cost(self, model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost based on token usage.
        
        This is a simplified cost calculation. Update with actual pricing.
        """
        # Simplified pricing (per 1K tokens)
        pricing = {
            'gpt-4': {'prompt': 0.03, 'completion': 0.06},
            'gpt-3.5-turbo': {'prompt': 0.0015, 'completion': 0.002},
            'google/gemini-2.5-flash-lite': {'prompt': 0.0001, 'completion': 0.0002},
            'claude-3-opus': {'prompt': 0.015, 'completion': 0.075},
            'claude-3-sonnet': {'prompt': 0.003, 'completion': 0.015},
        }
        
        # Find matching pricing
        model_pricing = None
        for key, value in pricing.items():
            if key.lower() in model_name.lower():
                model_pricing = value
                break
        
        if not model_pricing:
            # Default to very low estimate
            model_pricing = {'prompt': 0.0001, 'completion': 0.0002}
        
        cost = (prompt_tokens / 1000.0 * model_pricing['prompt']) + \
               (completion_tokens / 1000.0 * model_pricing['completion'])
        
        return round(cost, 6)

    async def _log_invocation(
        self,
        messages: List[BaseMessage],
        response: ChatResult,
        latency_ms: int,
        error: Optional[Exception] = None
    ):
        """Log the invocation to the database.
        
        Creates a new database session for each logging operation to avoid
        concurrent access issues when the same LLM instance is shared across
        multiple async workflows.
        """
        if not self.enable_logging:
            return

        # Create a new database session for this logging operation
        # to avoid concurrent access issues with shared LLM instances
        from app.core.database import async_session_factory
        
        async with async_session_factory() as db:
            try:
                config = self._extract_model_config()
                
                # Extract token usage
                prompt_tokens = None
                completion_tokens = None
                total_tokens = None
                
                if response and response.llm_output:
                    token_usage = response.llm_output.get('token_usage', {})
                    prompt_tokens = token_usage.get('prompt_tokens')
                    completion_tokens = token_usage.get('completion_tokens')
                    total_tokens = token_usage.get('total_tokens')
                
                # Calculate cost
                cost_usd = None
                if prompt_tokens and completion_tokens:
                    cost_usd = self._calculate_cost(
                        config.get('model_name', ''),
                        prompt_tokens,
                        completion_tokens
                    )
                
                # Extract response text
                response_text = None
                response_metadata = None
                if response and self.log_full_response:
                    if response.generations:
                        # response.generations[0] is already a ChatGeneration object
                        response_text = response.generations[0].text
                    response_metadata = response.llm_output
                
                # Prepare repository with new session
                repo = LLMInvocationRepository(db)
                
                # Create log entry
                await repo.create_llm_invocation_log(
                    model_name=config.get('model_name', 'unknown'),
                    provider=self.provider,
                    temperature=config.get('temperature'),
                    max_tokens=config.get('max_tokens'),
                    prompt=self._extract_prompt_from_messages(messages),
                    messages=self._messages_to_dict(messages),
                    response=response_text,
                    response_metadata=response_metadata,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost_usd,
                    success=error is None,
                    error_message=str(error) if error else None,
                    error_type=type(error).__name__ if error else None,
                    user_id=current_user_id.get() or self._user_id,
                    playlist_id=current_playlist_id.get() or self._playlist_id,
                    session_id=current_session_id.get() or self._session_id,
                    agent_name=current_agent_name.get() or self._agent_name,
                    operation=current_operation.get() or self._operation,
                    context_metadata=self._context_metadata
                )
                
                logger.debug(
                    "LLM invocation logged",
                    model=config.get('model_name'),
                    playlist_id=current_playlist_id.get() or self._playlist_id,
                    session_id=current_session_id.get() or self._session_id,
                    agent=self._agent_name,
                    tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost_usd
                )
                
            except Exception as e:
                logger.error("Failed to log LLM invocation", error=str(e), exc_info=True)

    @property
    def _llm_type(self) -> str:
        """Return type of language model."""
        return f"logged_{self.wrapped_llm._llm_type}"

    def _generate(
        self,
        messages: Union[List[BaseMessage], List[Dict[str, str]]],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response (sync version)."""
        # Convert messages if needed
        converted_messages = self._convert_to_messages(messages)

        start_time = time.time()
        error = None
        result = None

        try:
            result = self.wrapped_llm._generate(converted_messages, stop, run_manager, **kwargs)
            return result
        except Exception as e:
            error = e
            raise
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            # Note: Can't do async logging in sync method
            # Would need to schedule this for later or use sync logging
            if self.enable_logging:
                logger.debug(
                    "LLM invocation completed (sync)",
                    latency_ms=latency_ms,
                    error=str(error) if error else None
                )

    async def _agenerate(
        self,
        messages: Union[List[BaseMessage], List[Dict[str, str]]],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response (async version)."""
        # Convert messages if needed
        converted_messages = self._convert_to_messages(messages)

        start_time = time.time()
        error = None
        result = None

        try:
            result = await self.wrapped_llm._agenerate(converted_messages, stop, run_manager, **kwargs)
            return result
        except Exception as e:
            error = e
            raise
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            await self._log_invocation(converted_messages, result, latency_ms, error)

    def invoke(
        self,
        input: Union[str, List[BaseMessage], List[Dict[str, str]]],
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke the LLM (sync version)."""
        start_time = time.time()
        error = None
        result = None
        
        try:
            result = self.wrapped_llm.invoke(input, config, **kwargs)
            return result
        except Exception as e:
            error = e
            raise
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            if self.enable_logging:
                logger.debug(
                    "LLM invocation completed (sync invoke)",
                    latency_ms=latency_ms,
                    error=str(error) if error else None
                )

    async def ainvoke(
        self,
        input: Union[str, List[BaseMessage], List[Dict[str, str]]],
        config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        """Invoke the LLM (async version)."""
        if isinstance(input, str):
            from langchain_core.messages import HumanMessage
            logged_messages: List[BaseMessage] = [HumanMessage(content=input)]
        else:
            logged_messages = self._convert_to_messages(input)

        start_time = time.time()
        error = None
        result = None
        
        try:
            result = await self.wrapped_llm.ainvoke(input, config, **kwargs)
            return result
        except Exception as e:
            error = e
            raise
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            # Create a mock ChatResult for logging
            if result:
                chat_result = ChatResult(
                    generations=[ChatGeneration(message=result)],
                    llm_output=getattr(result, 'response_metadata', {})
                )
            else:
                chat_result = None
            await self._log_invocation(logged_messages, chat_result, latency_ms, error)
