import google.generativeai as genai
from typing import List, Dict, Any, AsyncIterator
from bio_mcp_host.llm_clients.base import BaseLLMClient, Message, LLMResponse, LLMConfig

class GoogleClient(BaseLLMClient):
    """Google Gemini client"""
    
    def __init__(self, config: LLMConfig, mcp_client=None):
        super().__init__(config, mcp_client)
        genai.configure(api_key=self.api_key)
        
        # Latest models (2025)
        self.available_models = [
            "gemini-2.5-pro",        # Latest Gemini 2.5 Pro (2025)
            "gemini-2.0-flash-lite", # Lightweight version
            "gemini-1.5-pro",        # Previous flagship
            "gemini-1.5-flash",      # Fast model
            "gemini-1.0-pro"         # Legacy model
        ]
        
        # Initialize model
        self.gemini_model = genai.GenerativeModel(self.model)
    
    async def chat_completion(self, 
                            messages: List[Message], 
                            stream: bool = False,
                            **kwargs) -> LLMResponse:
        """Generate chat completion using Google Gemini API with tool calling support"""
        
        # Format messages for Gemini
        chat_history, current_message = self._format_messages_for_gemini(messages)
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        
        # Create generation config
        generation_config = self._create_generation_config(params)
        
        # Get available tools
        available_tools = self._convert_mcp_tools_to_gemini()
        
        try:
            if stream:
                # Handle streaming - for now, disable tool calling in streaming mode
                chat = self.gemini_model.start_chat(history=chat_history)
                
                response_stream = await chat.send_message_async(
                    current_message,
                    generation_config=generation_config,
                    stream=True
                )
                
                response_content = ""
                async for chunk in response_stream:
                    if chunk.text:
                        response_content += chunk.text
                
                return LLMResponse(
                    content=response_content,
                    usage={"stream": True},
                    metadata={"provider": "google", "model": self.model}
                )
            else:
                # Regular completion with tool calling
                if chat_history:
                    chat = self.gemini_model.start_chat(history=chat_history)
                    
                    # Send message with tools if available
                    if available_tools:
                        response = await chat.send_message_async(
                            current_message,
                            generation_config=generation_config,
                            tools=[{"function_declarations": available_tools}]
                        )
                    else:
                        response = await chat.send_message_async(
                            current_message,
                            generation_config=generation_config
                        )
                else:
                    # Use generate_content for single message
                    if available_tools:
                        response = await self.gemini_model.generate_content_async(
                            current_message,
                            generation_config=generation_config,
                            tools=[{"function_declarations": available_tools}]
                        )
                    else:
                        response = await self.gemini_model.generate_content_async(
                            current_message,
                            generation_config=generation_config
                        )
                
                # Check for function calls
                function_calls = self._extract_function_calls(response)
                
                if function_calls:
                    # Execute function calls
                    function_results = await self._execute_function_calls(function_calls)
                    
                    # Format results for continued conversation
                    results_text = self._format_function_results(function_results)
                    
                    # Continue conversation with function results
                    if chat_history:
                        # Add function call and results to chat history
                        follow_up_response = await chat.send_message_async(
                            f"Function results:\n{results_text}\n\nPlease provide a response based on these results.",
                            generation_config=generation_config
                        )
                        final_content = follow_up_response.text
                    else:
                        # For single message, create new chat with function results
                        new_chat = self.gemini_model.start_chat()
                        follow_up_response = await new_chat.send_message_async(
                            f"Based on the function call results:\n{results_text}\n\nOriginal request: {current_message}\n\nPlease provide a helpful response.",
                            generation_config=generation_config
                        )
                        final_content = follow_up_response.text
                else:
                    # No function calls, use original response
                    final_content = response.text
                
                return LLMResponse(
                    content=final_content,
                    usage={
                        "prompt_token_count": getattr(response.usage_metadata, 'prompt_token_count', None),
                        "candidates_token_count": getattr(response.usage_metadata, 'candidates_token_count', None),
                        "total_token_count": getattr(response.usage_metadata, 'total_token_count', None)
                    } if hasattr(response, 'usage_metadata') else None,
                    metadata={
                        "provider": "google",
                        "model": self.model,
                        "finish_reason": response.candidates[0].finish_reason.name if response.candidates else None,
                        "function_calls": function_calls if function_calls else None
                    }
                )
                
        except Exception as e:
            raise Exception(f"Google Gemini API error: {str(e)}")
    
    async def chat_completion_stream(self, 
                                   messages: List[Message], 
                                   **kwargs) -> AsyncIterator[str]:
        """Generate streaming chat completion"""
        
        chat_history, current_message = self._format_messages_for_gemini(messages)
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        generation_config = self._create_generation_config(params)
        
        try:
            chat = self.gemini_model.start_chat(history=chat_history)
            response_stream = await chat.send_message_async(
                current_message,
                generation_config=generation_config,
                stream=True
            )
            
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            raise Exception(f"Google Gemini streaming error: {str(e)}")
    
    def _format_messages_for_gemini(self, messages: List[Message]):
        """Format messages for Gemini API"""
        chat_history = []
        system_instructions = []
        
        # Separate system messages and regular conversation
        for msg in messages[:-1]:  # All but last message
            if msg.role == "system":
                system_instructions.append(msg.content)
            elif msg.role == "user":
                chat_history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                chat_history.append({"role": "model", "parts": [msg.content]})
        
        # Last message is the current prompt
        current_message = messages[-1].content if messages else ""
        
        # Prepend system instructions to current message if any
        if system_instructions:
            current_message = "\n".join(system_instructions) + "\n\n" + current_message
        
        return chat_history, current_message
    
    def _create_generation_config(self, params: Dict[str, Any]):
        """Create Gemini generation configuration"""
        config = {}
        
        if "max_tokens" in params:
            config["max_output_tokens"] = params["max_tokens"]
        if "temperature" in params:
            config["temperature"] = params["temperature"]
        if "top_p" in params:
            config["top_p"] = params["top_p"]
        if "top_k" in params:
            config["top_k"] = params["top_k"]
        
        return genai.GenerationConfig(**config) if config else None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Gemini model information"""
        model_info = {
            "provider": "google",
            "model": self.model,
            "available_models": self.available_models,
            "supports_streaming": True,
            "supports_system_messages": True,
            "max_context_length": self._get_context_length(),
            "capabilities": [
                "text_generation",
                "conversation",
                "analysis",
                "code_generation",
                "multimodal"
            ]
        }
        return model_info
    
    def _get_context_length(self) -> int:
        """Get context length for different Gemini models"""
        context_lengths = {
            "gemini-2.5-pro": 1000000,        # 1M tokens for Gemini 2.5 Pro
            "gemini-2.0-flash-lite": 1000000, # 1M tokens for lightweight
            "gemini-1.5-pro": 2000000,        # 2M tokens for 1.5 Pro
            "gemini-1.5-flash": 1000000,      # 1M tokens for Flash
            "gemini-1.0-pro": 32768           # Legacy context
        }
        return context_lengths.get(self.model, 32768)
    
    def _convert_mcp_tools_to_gemini(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to Gemini function declarations"""
        if not self.mcp_client:
            return []
            
        tools = self.get_available_tools()
        gemini_functions = []
        
        for tool in tools:
            function_declaration = {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
            gemini_functions.append(function_declaration)
        
        return gemini_functions
    
    def _extract_function_calls(self, response) -> List[Dict[str, Any]]:
        """Extract function calls from Gemini response"""
        function_calls = []
        
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call'):
                            function_calls.append({
                                "name": part.function_call.name,
                                "arguments": dict(part.function_call.args)
                            })
            
            # Optional debug output
            # if function_calls:
            #     print(f"🔧 DEBUG: Extracted {len(function_calls)} function calls")
                        
        except Exception as e:
            pass  # Silently handle extraction errors
        
        return function_calls
    
    async def _execute_function_calls(self, function_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute function calls using MCP client"""
        results = []
        
        for call in function_calls:
            try:
                result = await self.call_mcp_tool(call["name"], call["arguments"])
                results.append({
                    "name": call["name"],
                    "result": result
                })
            except Exception as e:
                results.append({
                    "name": call["name"],
                    "error": str(e)
                })
        
        return results
    
    def _format_function_results(self, results: List[Dict[str, Any]]) -> str:
        """Format function call results for the LLM"""
        formatted_results = []
        
        for result in results:
            if "error" in result:
                formatted_results.append(f"Function {result['name']} failed: {result['error']}")
            else:
                formatted_results.append(f"Function {result['name']} returned: {result['result']}")
        
        return "\n".join(formatted_results)
    
    async def test_connection(self) -> bool:
        """Test Google Gemini API connection"""
        try:
            # Use direct API call without tools for testing
            response = await self.gemini_model.generate_content_async("Hello")
            return response.text is not None and len(response.text) > 0
        except Exception:
            return False