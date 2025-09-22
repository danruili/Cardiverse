from __future__ import annotations
import os
from retrying import retry
from openai import OpenAI
from dataclasses import dataclass, field
from typing import Literal, TypedDict, Union
import requests
from urllib.parse import urljoin
import re
import json

MessageRole = Literal["system", "user", "assistant"]


class MessageDict(TypedDict):
    role: MessageRole
    content: str


@dataclass
class Message:
    """OpenAI Message object containing a role and the message content"""

    role: MessageRole
    content: str

    def __init__(self, role: MessageRole, content: str):
        self.role = role
        self.content = content

    def raw(self) -> MessageDict:
        return {"role": self.role, "content": self.content}
    
    @classmethod
    def from_json(cls, json_dict: dict):
        return cls(role=json_dict["role"], content=json_dict["content"])


@dataclass
class ChatSequence:
    """Utility container for a chat sequence"""

    messages: list[Message] = field(default_factory=list)

    def __getitem__(self, i: int):
        return self.messages[i]

    def append(self, message: Message):
        return self.messages.append(message)

    def raw(self) -> list[dict]:
        return [message.raw() for message in self.messages]
    
    def pop(self, i: int = -1):
        return self.messages.pop(i)
    
    @classmethod
    def from_json(cls, json_list: list[dict]):
        return cls(messages=[Message.from_json(json_dict) for json_dict in json_list])


def get_api_key(key_name: str) -> str:
    """
    Get the API key from the environment or .env file.
    """
    api_key = os.environ.get(key_name)
    if not api_key:
        # try reading from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv(".env")
            api_key = os.environ.get(key_name)
        except:
            raise KeyError(f"{key_name} not found in environment or .env file")
    return api_key

class LLMHandler:
    llm_model = None
    record_messages = False
    log_path: str
    client = None
    prompt_token_usage = 0
    completion_token_usage = 0
    embedding_token_usage = 0
    clean_json = False
    unified_kwargs = {}

    def __init__(self, llm_model: str = "gpt-4o-2024-08-06", 
                 record_messages: bool = False, 
                 log_path: str = 'llm.log',
                 server_address: str = None):
        
        self.llm_model = llm_model
        self.record_messages = record_messages
        self.log_path = log_path

        # create the folder if the log_path does not exist
        log_folder = os.path.dirname(log_path)
        if not os.path.exists(log_folder) and self.record_messages:
            os.makedirs(log_folder)

        # if using a server, set the server address
        self.server_address = server_address
        if server_address is not None:
            api_key = "no-key-needed"
            base_url = server_address
        # if the llm_model is compatible with OpenAI API, use the OpenAI API
        elif llm_model.startswith("gpt") or "o1" in llm_model:
            base_url = None
            api_key = get_api_key("OPENAI_API_KEY")
        elif llm_model.startswith("qwen") or "gemini" in llm_model:
            base_url="https://openrouter.ai/api/v1"
            api_key = get_api_key("OPENROUTER_API_KEY")
        elif llm_model.startswith("deepseek"):
            base_url="https://api.deepseek.com"
            api_key = get_api_key("DEEPSEEK_API_KEY")
        # if using Claude
        elif llm_model.startswith("claude"):
            try:
                from anthropic import Anthropic
                self.client = Anthropic(
                    api_key=get_api_key("ANTHROPIC_API_KEY"),
                )
                return self
            except ImportError:
                print('Optional: Anthropic is not installed. Please install it if you want to use the Claude model.')
                self.client = None
        else:
            raise ValueError(f"Unsupported model: {llm_model}")

        self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        
    def clean_json_response(self, response: str) -> str:
        """
        Clean the response by removing the thinking process part and newlines.
        Returns a clean JSON string ready for validation.
        """
        # Remove content between <think> tags
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        # Remove any leading/trailing whitespace and newlines
        cleaned = cleaned.strip()
        # Remove all newlines
        cleaned = cleaned.replace('\n', '')
        # Try to parse and re-stringify to ensure valid JSON
        try:
            json_obj = json.loads(cleaned)
            # Handle different response structures
            if isinstance(json_obj, dict) and 'properties' in json_obj:
                # Get the required fields from the properties
                props = json_obj['properties']
                required = json_obj.get('required', [])
                if required == []:
                    required = props.keys()
                # Create a new object with only the required fields
                formatted = {key: props.get(key, '') for key in required}
                json_obj = formatted
            return json.dumps(json_obj)
        except json.JSONDecodeError:
            return cleaned

    @retry(wait_fixed=5000, stop_max_attempt_number=3)
    def chat(self, messages: Union[ChatSequence, list[dict], str], 
                      model=None, **kwargs) -> str:
        # if messages is a ChatSequence, convert it to a list of dicts
        if isinstance(messages, ChatSequence):
            messages = messages.raw()
        # if messages is a string, convert it to a list of dicts
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        if model is None:
            model = self.llm_model

        # save the messages to a file
        self.save_messages(messages)

        if "claude" in model:
            try:
                response = self.client.messages.create(
                    max_tokens=4096,
                    messages=messages,
                    model=model,
                )
            except Exception as err:
                print(f'ANTHROPIC ERROR: {err}')
                raise err

            content = response.content[0].text
            if self.clean_json:
                content = self.clean_json_response(content)
        else:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **self.unified_kwargs,
                    **kwargs
                    )
                content = response.choices[0].message.content
                if self.clean_json:
                    content = self.clean_json_response(content)
                try:
                    self.prompt_token_usage += response.usage.prompt_tokens
                    self.completion_token_usage += response.usage.completion_tokens
                except AttributeError:
                    # Handle the case where usage is not available
                    pass
            except Exception as err:
                print(f'OPENAI ERROR: {err}')
                raise err

        self.save_messages([{"role": "assistant", "content": content}])
        return content

    def save_messages(self, messages: list[dict]):
        if not self.record_messages:
            return
        with open(self.log_path, 'a', encoding='utf-8') as f:
            for message in messages:
                f.write(f'{message["role"]}: ')
                f.write(f'{message["content"]}\n')
                f.write(f'prompt_tokens: {self.prompt_token_usage}\n')
                f.write(f'completion_tokens: {self.completion_token_usage}\n')
                f.write(f'embedding_tokens: {self.embedding_token_usage}\n')
                f.write('-----------------------------------\n\n')

    def get_text_embeddings_multi(self, texts: list[str]) -> list[list[float]]:
        """
        Get the text embeddings from the server or OpenAI API.
        """
        assert all(isinstance(text, str) for text in texts)

        if self.server_address:
            try:
                response = requests.post(
                    urljoin(self.server_address, "/v1/embeddings"),
                    json={
                        "input": texts,
                        "model": "text-embedding-3-large"
                    },
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                self.embedding_token_usage += result.get("prompt_tokens", 0)
                return result["embeddings"]
            except requests.exceptions.RequestException as e:
                print(f'Server Error (Embeddings): {str(e)}')
                raise
        else:
            response = self.client.embeddings.create(
                input=texts,
                model="text-embedding-3-large",
                encoding_format="float",
                dimensions=1536,
            )

            self.embedding_token_usage += response.usage.prompt_tokens
            return [r.embedding for r in response.data]
    
    def get_text_embeddings(self, text: str) -> list[float]:
        return self.get_text_embeddings_multi([text])[0]
    
    def get_usage(self):
        return {
            "prompt_tokens": self.prompt_token_usage,
            "completion_tokens": self.completion_token_usage,
            "embedding_tokens": self.embedding_token_usage
        }
    
    def add_usage(self, usage: dict):
        self.prompt_token_usage += usage["prompt_tokens"]
        self.completion_token_usage += usage["completion_tokens"]
        self.embedding_token_usage += usage["embedding_tokens"]

    def set_log_path(self, log_path: str):
        self.log_path = log_path
        self.record_messages = True

    def get_llm(self):
        return self.llm_model
    
    def set_server_address(self, address: str):
        """Set the server address for LLM communication."""
        self.server_address = address.rstrip('/')  # Remove trailing slash if present
        # Clear existing clients when switching to server mode
        self.client = None
        self.client2 = None

    def get_server_address(self) -> str:
        """Get the current server address."""
        return self.server_address


def get_text_embeddings(text: str) -> list[float]:
    """
    Get the text embeddings from the OpenAI API.
    """

    client = OpenAI()

    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
    )

    return response.data[0].embedding


if __name__ == "__main__":
    handler = LLMHandler()
    res = handler.chat("What is the sum of the first 10 Fibonacci numbers?")
    print(res)