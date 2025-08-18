"""
LLM Service

This module provides services for configuring and interacting with language model APIs.
Following a testable-first approach with typed data contracts.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

# Data Contracts
@dataclass
class LLMConfigData:
    id: UUID
    name: str
    model_name: str
    api_key: str
    base_prompt: str
    temperature: float
    max_tokens: int
    is_default: bool
    is_active: bool

@dataclass
class LLMResponseResult:
    response_text: str
    tokens_used: int
    success: bool = True
    error: Optional[str] = None


class LLMService:
    """
    Service class for LLM-related business logic.
    
    This service follows a testable-first approach with clear data contracts
    and properly typed methods for easier testing and maintenance.
    """
    
    @staticmethod
    def get_response(conversation: 'Conversation', content: str, message_type: str) -> str:
        """
        Generate an AI response based on conversation context.
        
        Args:
            conversation: Conversation object
            content: Latest message content
            message_type: Type of message
            
        Returns:
            String containing the AI response
        """
        import requests
        
        try:
            # Get LLM config - first from the homework, then fallback to default
            llm_config = None
            if hasattr(conversation.section, 'homework') and conversation.section.homework.llm_config:
                llm_config = conversation.section.homework.llm_config
            
            # If no config on homework, get default config
            if not llm_config:
                config_data = LLMService.get_default_config()
                if not config_data:
                    return "I'm sorry, but there's no valid LLM configuration available right now."
                
                # Get actual LLM config object from data
                from .models import LLMConfig
                llm_config = LLMConfig.objects.get(id=config_data.id)
            
            # Get API key from config
            api_key = llm_config.api_key
            if not api_key:
                logger.error("API key not found in LLM configuration")
                return "I'm sorry, but there was an error connecting to the AI service. Please contact support."
            
            # Build prompt
            prompt = LLMService._build_prompt(conversation, content, message_type)
            
            # Call OpenAI API (assuming OpenAI-compatible API)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Construct the request body based on the model being used
            # This assumes OpenAI-like API structure
            request_body = {
                "model": llm_config.model_name,
                "messages": [
                    {"role": "system", "content": llm_config.base_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": llm_config.temperature,
                "max_tokens": llm_config.max_tokens
            }
            
            # Make API call
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=request_body
            )
            
            # Parse response
            response_json = response.json()
            if 'choices' in response_json and len(response_json['choices']) > 0:
                return response_json['choices'][0]['message']['content']
            else:
                logger.error(f"Unexpected API response: {response_json}")
                return "I'm sorry, but I couldn't generate a response. Please try again."
        
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "I'm sorry, but there was an error generating a response. Please try again."
    
    @staticmethod
    def get_default_config() -> Optional[LLMConfigData]:
        """
        Get the default LLM configuration.
        
        Returns:
            LLMConfigData if default config found, None otherwise
        """
        from .models import LLMConfig
        
        try:
            # Get default config
            config = LLMConfig.objects.get(is_default=True, is_active=True)
            
            # Convert to data contract
            return LLMConfigData(
                id=config.id,
                name=config.name,
                model_name=config.model_name,
                api_key=config.api_key,
                base_prompt=config.base_prompt,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                is_default=config.is_default,
                is_active=config.is_active
            )
        except LLMConfig.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting default LLM config: {str(e)}")
            return None
    
    @staticmethod
    def create_config(data: Dict[str, Any]) -> UUID:
        """
        Create a new LLM configuration.
        
        Args:
            data: Dictionary with configuration parameters
            
        Returns:
            UUID of the created configuration
        """
        from .models import LLMConfig
        
        # Extract fields from data
        name = data.get('name')
        model_name = data.get('model_name')
        api_key = data.get('api_key')
        base_prompt = data.get('base_prompt')
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1000)
        is_default = data.get('is_default', False)
        is_active = data.get('is_active', True)
        
        # Create config
        config = LLMConfig.objects.create(
            name=name,
            model_name=model_name,
            api_key=api_key,
            base_prompt=base_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            is_default=is_default,
            is_active=is_active
        )
        
        return config.id
    
    @staticmethod
    def update_config(config_id: UUID, data: Dict[str, Any]) -> bool:
        """
        Update an existing LLM configuration.
        
        Args:
            config_id: UUID of the configuration to update
            data: Dictionary with configuration parameters
            
        Returns:
            True if updated successfully, False otherwise
        """
        from .models import LLMConfig
        
        try:
            # Get config
            config = LLMConfig.objects.get(id=config_id)
            
            # Update fields if provided
            if 'name' in data:
                config.name = data['name']
            if 'model_name' in data:
                config.model_name = data['model_name']
            if 'api_key' in data:
                config.api_key = data['api_key']
            if 'base_prompt' in data:
                config.base_prompt = data['base_prompt']
            if 'temperature' in data:
                config.temperature = data['temperature']
            if 'max_tokens' in data:
                config.max_tokens = data['max_tokens']
            if 'is_default' in data:
                config.is_default = data['is_default']
            if 'is_active' in data:
                config.is_active = data['is_active']
            
            # Save changes
            config.save()
            
            return True
        except LLMConfig.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error updating LLM config: {str(e)}")
            return False
    
    @staticmethod
    def _build_prompt(conversation: 'Conversation', content: str, message_type: str) -> str:
        """
        Build the prompt to send to the language model.
        
        Args:
            conversation: Conversation object
            content: Latest message content
            message_type: Type of message
            
        Returns:
            String containing the prompt for the language model
        """
        # Get conversation context
        context_parts = [
            f"Section Title: {conversation.section.title}",
            f"Section Content: {conversation.section.content}",
            "\nPrevious Messages:\n"
        ]
        
        # Add previous messages
        for msg in conversation.messages.all().order_by('timestamp'):
            if msg.is_from_student:
                context_parts.append(f"Student: {msg.content}")
            elif msg.is_from_ai:
                context_parts.append(f"AI Tutor: {msg.content}")
            elif msg.is_system_message:
                context_parts.append(f"System: {msg.content}")
        
        # Add current message
        if message_type == 'student':
            context_parts.append(f"\nCurrent Message - Student: {content}")
        elif message_type == 'code':
            context_parts.append(f"\nCurrent Message - Student Code Submission:\n```r\n{content}\n```")
        
        # Instruction to the AI
        context_parts.append("\nPlease respond as an AI tutor helping the student with this section.")
        
        return "\n\n".join(context_parts)
    
    # Removing _get_api_key method as we now get the API key directly from config