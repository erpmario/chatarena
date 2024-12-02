from .base import IntelligenceBackend, register_backend
from ..config import BackendConfig


class StrategicBase(IntelligenceBackend):
	stateful = True
	type_name = "strategic"
	game_phase = "unknown"
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	
	
	def to_config(self) -> BackendConfig:
		return BackendConfig(backend_type = self.type_name)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		raise NotImplementedError("Strategic backend is not implemented for querying.")


@register_backend
class Dove(StrategicBase):
	type_name = "strategic:dove"
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		if self.game_phase == "snowdrift":
			return "Volunteer"
		elif self.game_phase == "prisoners-dilemma":
			return "Cooperate"
		else:
			raise ValueError("Unknown game phase.")


@register_backend
class Hawk(StrategicBase):
	type_name = "strategic:hawk"
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		if self.game_phase == "snowdrift":
			return "Ignore"
		elif self.game_phase == "prisoners-dilemma":
			return "Defect"
		else:
			raise ValueError("Unknown game phase.")


@register_backend
class Random(StrategicBase):
	type_name = "strategic:random"
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		import random
		
		if self.game_phase == "snowdrift":
			return random.choice(["Volunteer", "Ignore"])
		elif self.game_phase == "prisoners-dilemma":
			return random.choice(["Cooperate", "Defect"])
		else:
			raise ValueError("Unknown game phase.")
	