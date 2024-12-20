import os
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import List, Dict

import torch
from tenacity import retry, stop_after_attempt, wait_random_exponential
from huggingface_hub import login

from ..message import SYSTEM_NAME as SYSTEM
from ..message import Message
from .base import IntelligenceBackend, register_backend


DEFAULT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SINGLETON_MODE = True


@contextmanager
def suppress_stdout_stderr():
	"""A context manager that redirects stdout and stderr to devnull."""
	with open(os.devnull, "w") as fnull:
		with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
			yield (err, out)


with suppress_stdout_stderr():
	# Try to import the transformers package
	try:
		import transformers
		from transformers import pipeline
		# from transformers.pipelines.conversational import (
		# 	Conversation,
		# 	ConversationalPipeline,
		# )
		from transformers.pipelines.text_generation import TextGenerationPipeline
		
		login("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")
	except ImportError:
		is_transformers_available = False
	else:
		is_transformers_available = True


@register_backend
class TransformersTextGeneration(IntelligenceBackend):
	"""Interface to the Transformers TextGenerationPipeline."""
	
	stateful = False
	type_name = "transformers:text-generation"
	generator = None
	
	
	def __init__(self, model: str = DEFAULT_MODEL, device: int = DEVICE, **kwargs):
		super().__init__(model = model, device = device, **kwargs)
		self.model = model
		self.device = device
		
		assert is_transformers_available, "Transformers package is not installed"
		# If backend is in singleton mode, only create the generator once.
		if SINGLETON_MODE:
			if TransformersTextGeneration.generator is None:
				print(f"Creating generator for model: {model}")
				TransformersTextGeneration.generator = pipeline(
					task = "text-generation", model = self.model, device = self.device
				)
			self.generator = TransformersTextGeneration.generator
		else:
			print(f"Creating generator for model: {model}")
			self.generator = pipeline(
				task = "text-generation", model = self.model, device = self.device
			)
	
	
	@retry(stop = stop_after_attempt(6), wait = wait_random_exponential(min = 1, max = 60))
	def _get_response(self, chat: List[Dict[str, str]]) -> str:
		response = self.generator(chat, num_return_sequences = 1, max_new_tokens = 300, return_full_text = False)
		return response[0]['generated_text']
	
	
	@staticmethod
	def _msg_template(agent_name: str, content: str):
		return {"role": agent_name, "content": content}
	
	
	def query(
		self,
		agent_name: str,
		role_desc: str,
		history_messages: List[Message],
		global_prompt: str = None,
		request_msg: Message = None,
		*args,
		**kwargs,
	) -> str:
		chat = []
		
		if global_prompt:
			chat.append(self._msg_template(SYSTEM, global_prompt))
		chat.append(self._msg_template(SYSTEM, role_desc))
		
		for msg in history_messages:
			chat.append(self._msg_template(msg.agent_name, msg.content))
		if request_msg:
			chat.append(self._msg_template(SYSTEM, request_msg.content))
		
		# Get the response
		response = self._get_response(chat)
		# responseDict = responseHistory[-1]
		# response = responseDict["content"]
		return response


@register_backend
class TransformersConversational(IntelligenceBackend):
	"""Interface to the Transformers ConversationalPipeline."""
	
	stateful = False
	type_name = "transformers:conversational"
	
	
	def __init__(self, model: str = DEFAULT_MODEL, device: int = -1, **kwargs):
		super().__init__(model = model, device = device, **kwargs)
		self.model = model
		self.device = device
		
		assert is_transformers_available, "Transformers package is not installed"
		self.chatbot = pipeline(
			task = "conversational", model = self.model, device = self.device
		)
	
	
	@retry(stop = stop_after_attempt(6), wait = wait_random_exponential(min = 1, max = 60))
	def _get_response(self, conversation):
		conversation = self.chatbot(conversation)
		response = conversation.generated_responses[-1]
		return response
	
	
	@staticmethod
	def _msg_template(agent_name, content):
		return f"[{agent_name}]: {content}"
	
	
	def query(
		self,
		agent_name: str,
		role_desc: str,
		history_messages: List[Message],
		global_prompt: str = None,
		request_msg: Message = None,
		*args,
		**kwargs,
	) -> str:
		user_inputs, generated_responses = [], []
		all_messages = (
			[(SYSTEM, global_prompt), (SYSTEM, role_desc)]
			if global_prompt
			else [(SYSTEM, role_desc)]
		)
		
		for msg in history_messages:
			all_messages.append((msg.agent_name, msg.content))
		if request_msg:
			all_messages.append((SYSTEM, request_msg.content))
		
		prev_is_user = False  # Whether the previous message is from the user
		for i, message in enumerate(all_messages):
			if i == 0:
				assert (
						message[0] == SYSTEM
				)  # The first message should be from the system
			
			if message[0] != agent_name:
				if not prev_is_user:
					user_inputs.append(self._msg_template(message[0], message[1]))
				else:
					user_inputs[-1] += "\n" + self._msg_template(message[0], message[1])
				prev_is_user = True
			else:
				if prev_is_user:
					generated_responses.append(message[1])
				else:
					generated_responses[-1] += "\n" + message[1]
				prev_is_user = False
		
		assert len(user_inputs) == len(generated_responses) + 1
		past_user_inputs = user_inputs[:-1]
		new_user_input = user_inputs[-1]
		
		# Recreate a conversation object from the history messages
		conversation = Conversation(
			text = new_user_input,
			past_user_inputs = past_user_inputs,
			generated_responses = generated_responses,
		)
		
		# Get the response
		response = self._get_response(conversation)
		return response


# conversation = Conversation("Going to the movies tonight - any suggestions?")
#
# # Steps usually performed by the model when generating a response:
# # 1. Mark the user input as processed (moved to the history)
# conversation.mark_processed()
# # 2. Append a mode response
# conversation.append_response("The Big lebowski.")
#
# conversation.add_user_input("Is it good?")
