from __future__ import annotations

from typing import Dict, List

from .base import IntelligenceBackend, register_backend
from ..config import BackendConfig


class StrategicBase(IntelligenceBackend):
	stateful = True
	type_name = "strategic"
	game_phase = "unknown"
	player_names: List[str]
	decision_history: Dict[str, List[str]]
	resource_units: Dict[str, int]
	paired_with: str
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	
	
	def to_config(self) -> BackendConfig:
		return BackendConfig(backend_type = self.type_name)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		raise NotImplementedError("Strategic backend is not implemented for querying.")
	
	
	def update_state(
		self, game_phase: str = None, player_names: List[str] = None, decision_history: Dict[str, List[str]] = None, resource_units: Dict[str, int] = None,
		paired_with: str = None, **kwargs
	):
		if game_phase is not None:
			self.game_phase = game_phase
		if player_names is not None:
			self.player_names = player_names
		if decision_history is not None:
			self.decision_history = decision_history
		if resource_units is not None:
			self.resource_units = resource_units
		if paired_with is not None:
			self.paired_with = paired_with
	
	
	def post_process(self, agent_name: str, **kwargs):
		pass


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


@register_backend
class Grudger(StrategicBase):
	type_name = "strategic:grudger"
	__grudge_held_n_person: bool
	__grudge_held_binary: Dict[str, bool]
	__previous_RUs: int
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.__grudge_held_n_person = False
		self.__grudge_held_binary = {player: False for player in self.player_names}
		self.__previous_RUs = 0
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		if self.game_phase == "snowdrift":
			return "Volunteer"
		elif self.game_phase == "prisoners-dilemma":
			if self.paired_with:
				return "Defect" if self.__grudge_held_binary[self.paired_with] else "Cooperate"
			else:
				return "Defect" if self.__grudge_held_n_person else "Cooperate"
		else:
			raise ValueError("Unknown game phase.")
	
	
	def post_process(self, agent_name: str, **kwargs):
		if self.game_phase == "prisoners-dilemma":
			if self.paired_with:
				if self.decision_history[self.paired_with][-1] == "D":
					self.__grudge_held_binary[self.paired_with] = True
			else:
				# If enough players Defected to where I lost RUs, hold a grudge.
				if self.resource_units[agent_name] < self.__previous_RUs:
					self.__grudge_held_n_person = True
			self.__previous_RUs = self.resource_units[agent_name]


@register_backend
class TitForTat(StrategicBase):
	type_name = "strategic:tit-for-tat"
	
	
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
	
	
	def query(self, agent_name: str, **kwargs) -> str:
		if agent_name in self.decision_history and self.decision_history[agent_name]:
			# Return the opponent's last decision
			return self.decision_history[agent_name][-1]
		else:
			# Default to "Cooperate" if no history is available
			return "Cooperate"
