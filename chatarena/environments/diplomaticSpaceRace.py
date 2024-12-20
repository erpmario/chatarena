import math
from typing import Dict, List, Union

from .base import Environment, TimeStep, register_env
from ..agent import SIGNAL_END_OF_CONVERSATION, Player
from ..backends.strategic import StrategicBase
from ..message import Message, MessagePool


# This app's functionality is so obfuscated that I cannot figure out how to put these in any other way.
DEFAULT_STARTING_RUS = (850, 520, 400, 300, 700, 250)
DEFAULT_VOLUNTEER_COST = 200
DEFAULT_PROJECT_REWARD = 500
DEFAULT_NEEDED_RUS = 600
DEFAULT_COOPERATE_COST = 50
DEFAULT_COOPERATE_CONTRIBUTION = 100

DEFAULT_SD_MODE = "one-shot"
DEFAULT_PD_MODE = "iterated"
PD_ITERATIONS = 3


@register_env
class DiplomaticSpaceRace(Environment):
	type_name = "diplomatic-space-race"
	
	startingRUs: List[int]
	resourceUnits: Dict[str, int]
	decisions: Dict[str, str]
	volunteerCost: int
	projectReward: int
	neededRUs: int
	cooperateCost: int
	cooperateContribution: int
	snowdriftMode: str
	prisonersDilemmaMode: str
	messagePool: MessagePool
	
	gamePhase: str
	currentTurn: int
	currentIteration: int
	nextPlayerIdx: int
	initialized: bool
	
	
	def __init__(
		self, player_names: List[str], players: List[Player], startingRUs: List[int] = None, volunteerCost: int = None,
		projectReward: int = None, neededRUs: int = None, cooperateCost: int = None, cooperateContribution: int = None,
		snowdriftMode: str = None, prisonersDilemmaMode: str = None,
		**kwargs
	):
		super().__init__(player_names, players, **kwargs)
		
		self.messagePool = MessagePool()
		self.initialized = False
		
		if startingRUs is None:
			startingRUs = DEFAULT_STARTING_RUS
		self.startingRUs = startingRUs
		
		if volunteerCost is None:
			volunteerCost = DEFAULT_VOLUNTEER_COST
		self.volunteerCost = volunteerCost
		
		if projectReward is None:
			projectReward = DEFAULT_PROJECT_REWARD
		self.projectReward = projectReward
		
		if neededRUs is None:
			neededRUs = DEFAULT_NEEDED_RUS
		self.neededRUs = neededRUs
		
		if cooperateCost is None:
			cooperateCost = DEFAULT_COOPERATE_COST
		self.cooperateCost = cooperateCost
		
		if cooperateContribution is None:
			cooperateContribution = DEFAULT_COOPERATE_CONTRIBUTION
		self.cooperateContribution = cooperateContribution
		
		if snowdriftMode is None:
			snowdriftMode = DEFAULT_SD_MODE
		self.snowdriftMode = snowdriftMode
		
		if prisonersDilemmaMode is None:
			prisonersDilemmaMode = DEFAULT_PD_MODE
		self.prisonersDilemmaMode = prisonersDilemmaMode
		
		self.reset()
	
	
	def reset(self):
		self.currentTurn = 0
		self.currentIteration = 0
		self.nextPlayerIdx = 0
		self.messagePool.reset()
		self.resourceUnits = {}
		self.decisions = {}
		for i in range(len(self.players)):
			ithPlayer = self.players[i]
			self.resourceUnits[self.player_names[i]] = self.startingRUs[i]
			self.decisions[self.player_names[i]] = ""
			if isinstance(ithPlayer.backend, StrategicBase):
				ithPlayer.backend.game_phase = "snowdrift"
		self.gamePhase = "snowdrift"
		
		self._moderator_speak("Now the game starts! Each of you must choose to Volunteer or Ignore.")
		
		self.initialized = True
		initTimestep = TimeStep(
			observation = [], reward = self.get_zero_rewards(), terminal = False
		)
		return initTimestep
	
	
	def initPD(self):
		self.gamePhase = "prisoners-dilemma"
		self.currentIteration = 0
		for player in self.players:
			if isinstance(player.backend, StrategicBase):
				player.backend.game_phase = "prisoners-dilemma"
		self._moderator_speak("Now we move into the harvesting phase.")
		if self.prisonersDilemmaMode == "iterated":
			self._nextPDIteration()
		else:
			for nation, resourceUnits in self.resourceUnits.items():
				self._moderator_speak(f"You have {resourceUnits} RUs.", visibleTo = nation)
			self._moderator_speak("Each of you must choose to Cooperate or Defect.")
	
	
	def _nextPDIteration(self):
		self.currentIteration += 1
		if self.currentIteration > PD_ITERATIONS:
			pass
		else:
			self._moderator_speak(f"This is iteration {self.currentIteration}.")
			for nation, resourceUnits in self.resourceUnits.items():
				self._moderator_speak(f"You have {resourceUnits} RUs.", visibleTo = nation)
			self._moderator_speak("Each of you must choose to Cooperate or Defect.")
	
	
	def get_observation(self, player_name = None) -> List[Message]:
		if player_name is None:
			return self.messagePool.get_all_messages()
		else:
			return self.messagePool.get_visible_messages(
				player_name, turn = self.currentTurn
			)
	
	
	def get_next_player(self) -> str:
		return self.player_names[self.nextPlayerIdx]
	
	
	def print(self):
		self.messagePool.print()
	
	
	def step(self, player_name: str, action: str) -> TimeStep:
		if not self.initialized:
			self.reset()
		
		assert (player_name == self.get_next_player()), f"Wrong player! It is {self.get_next_player()}'s turn."
		
		if self.gamePhase == "snowdrift":
			timestep = self._processSnowdriftStep(action, player_name)
		elif self.gamePhase == "prisoners-dilemma":
			timestep = self._processPDStep(action, player_name)
		else:
			raise ValueError("Only valid game phases are 'snowdrift' and 'prisoners-dilemma'.")
		
		if self.is_terminal():
			timestep.terminal = True
		
		return timestep
	
	
	def _processSnowdriftStep(self, action, player_name):
		message = Message(agent_name = player_name, content = action, turn = self.currentTurn)
		self.messagePool.append_message(message)
		self.decisions[player_name] = "V" if "Volunteer" in action else "I" if "Ignore" in action else ""
		self.currentTurn += 1
		if self.nextPlayerIdx < len(self.player_names) - 1:
			self.nextPlayerIdx += 1
			timestep = TimeStep(
				observation = self.get_observation(),
				reward = self.get_zero_rewards(),
				terminal = False
			)
		else:
			timestep = self._processSnowdriftEnd()
		return timestep
	
	
	def _processSnowdriftEnd(self):
		self.nextPlayerIdx = 0
		contributedRUs = 0
		for _, decision in self.decisions.items():
			if decision == "V":
				contributedRUs += self.volunteerCost
		projectSucceeded = contributedRUs >= self.neededRUs
		moderatorMessage = ""
		for nation, decision in self.decisions.items():
			moderatorMessage += f"{nation}'s choice: {'Volunteer' if decision == 'V' else 'Ignore'}\n"
		moderatorMessage += f"\nResult: The project {'succeeds' if projectSucceeded else 'fails'}!\n\n"
		for nation, decision in self.decisions.items():
			payoff = self.projectReward if projectSucceeded else 0
			if decision == "V":
				payoff -= self.volunteerCost
			self.resourceUnits[nation] += payoff
			if decision == "V":
				moderatorMessage += f"Since {nation} Volunteered, they lose {self.volunteerCost} RUs. "
			else:
				moderatorMessage += f"Since {nation} Ignored, they do not lose any RUs. "
			if projectSucceeded:
				moderatorMessage += f"However, since the project succeeded, they gain {self.projectReward} RUs. "
			moderatorMessage += f"This results in a net payoff of {payoff} RUs and leaves {nation} with {self.resourceUnits[nation]} RUs in total.\n"
		if projectSucceeded:
			moderatorMessage += "\nSince the project succeeded, we now move into the second phase of the game."
		else:
			moderatorMessage += "\nSince the project failed, the game is over."
		self._moderator_speak(moderatorMessage)
		self.currentTurn += 1
		if projectSucceeded:
			self.initPD()
		timestep = TimeStep(
			observation = self.get_observation(),
			reward = self.resourceUnits,
			terminal = not projectSucceeded
		)
		return timestep
	
	
	def _processPDStep(self, action, player_name):
		message = Message(agent_name = player_name, content = action, turn = self.currentTurn)
		self.messagePool.append_message(message)
		self.decisions[player_name] = "C" if "Cooperate" in action else "D" if "Defect" in action else ""
		self.currentTurn += 1
		if self.nextPlayerIdx < len(self.player_names) - 1:
			self.nextPlayerIdx += 1
			timestep = TimeStep(
				observation = self.get_observation(),
				reward = self.get_zero_rewards(),
				terminal = False
			)
		else:
			timestep = self._processPDEnd()
		return timestep
	
	
	def _processPDEnd(self):
		self.nextPlayerIdx = 0
		cooperated = 0
		for _, decision in self.decisions.items():
			if decision == "C":
				cooperated += 1
		moderatorMessage = ""
		for nation, decision in self.decisions.items():
			# If a nation doesn't have enough RUs to Cooperate, they will Defect by default.
			if self.resourceUnits[nation] < self.cooperateCost:
				self._moderator_speak(
					f"You don't have enough RUs to Cooperate, so you must Defect.", visibleTo = nation
				)
				self.decisions[nation] = "D"
				decision = "D"
			moderatorMessage += f"{nation}'s choice: {'Cooperate' if decision == 'C' else 'Defect'}\n"
		moderatorMessage += f"\nResult: {cooperated} nations Cooperated.\n\n"
		distributedReward = math.floor(cooperated * self.cooperateContribution / len(self.player_names))
		for nation, decision in self.decisions.items():
			payoff = 0
			if decision == "C":
				payoff -= self.cooperateCost
			payoff += distributedReward
			self.resourceUnits[nation] += payoff
			if decision == "C":
				moderatorMessage += f"Since {nation} Cooperated, they lose {self.cooperateCost} RUs. "
			else:
				moderatorMessage += f"Since {nation} Defected, they do not lose any RUs. "
			if cooperated > 0:
				moderatorMessage += f"However, since {cooperated} nations Cooperated, {nation} gains {distributedReward} RUs. "
			moderatorMessage += f"This results in a net payoff of {payoff} RUs and leaves {nation} with {self.resourceUnits[nation]} RUs in total.\n"
		if self.prisonersDilemmaMode == "iterated":
			if self.currentIteration < PD_ITERATIONS:
				self._moderator_speak(moderatorMessage)
				self._nextPDIteration()
				timestep = TimeStep(
					observation = self.get_observation(),
					reward = self.resourceUnits,
					terminal = False
				)
			else:
				moderatorMessage += "\nSince this was the last iteration, the game is over."
				self._moderator_speak(moderatorMessage)
				timestep = TimeStep(
					observation = self.get_observation(),
					reward = self.resourceUnits,
					terminal = True
				)
		else:
			moderatorMessage += "\nThe game is over."
			self._moderator_speak(moderatorMessage)
			timestep = TimeStep(
				observation = self.get_observation(),
				reward = self.resourceUnits,
				terminal = True
			)
		self.currentTurn += 1
		return timestep
	
	
	def check_action(self, action: str, player_name: str) -> bool:
		if self.gamePhase == "snowdrift":
			return any(act in action for act in ("Volunteer", "Ignore"))
		elif self.gamePhase == "prisoners-dilemma":
			return any(act in action for act in ("Cooperate", "Defect"))
		else:
			return True
	
	
	def is_terminal(self) -> bool:
		return self.messagePool.last_message.content.startswith(SIGNAL_END_OF_CONVERSATION)
	
	
	def _moderator_speak(self, text: str, visibleTo: Union[str, List[str]] = "all"):
		"""Moderator say something."""
		message = Message(
			agent_name = "Moderator",
			content = text,
			turn = self.currentTurn,
			visible_to = visibleTo,
		)
		self.messagePool.append_message(message)
