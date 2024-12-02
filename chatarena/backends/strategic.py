from typing import List

from ..config import BackendConfig
from .base import IntelligenceBackend, register_backend
from ..message import Message


class StrategicBase(IntelligenceBackend):
	stateful = True
	type_name = "strategic"
	game_phase = "unknown"
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.game_phase = "snowdrift"
	
	
	def to_config(self) -> BackendConfig:
		return BackendConfig(backend_type = self.type_name)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		raise NotImplementedError("Strategic backend is not implemented for querying.")
	
	
	def _processQuery(self, agent_name: str, history_messages: List[Message]) -> None:
		lastMessage: Message = history_messages[-1]
		if lastMessage.agent_name == "Moderator" and lastMessage.content == "":
			self.game_phase = lastMessage.content
	
	
class Dove(StrategicBase):
	type_name = "strategic:dove"
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		super().query(agent_name = agent_name, **kwargs)
		return "cooperate"
	
