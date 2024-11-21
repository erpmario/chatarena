from typing import Dict, List, Union

from .base import Environment, TimeStep, register_env
from ..agent import SIGNAL_END_OF_CONVERSATION
from ..message import Message, MessagePool


# This app's functionality is so obfuscated that I cannot figure out how to put these in any other way.
DEFAULT_STARTING_RUS = (850, 520, 400, 300, 700, 250)
DEFAULT_VOLUNTEER_COST = 200
DEFAULT_PROJECT_REWARD = 500
DEFAULT_NEEDED_RUS = 600


@register_env
class DiplomaticSpaceRace(Environment):
	type_name = "diplomatic-space-race"
	
	startingRUs: List[int]
	resourceUnits: Dict[str, int]
	decisions: Dict[str, str]
	volunteerCost: int
	projectReward: int
	neededRUs: int
	messagePool: MessagePool
	
	gamePhase: str
	currentTurn: int
	nextPlayerIdx: int
	initialized: bool
	
	
	def __init__(
		self, player_names: List[str], startingRUs: List[int] = None, volunteerCost: int = None,
		projectReward: int = None, neededRUs: int = None, **kwargs
	):
		super().__init__(player_names, **kwargs)
		
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
		
		self.reset()
	
	
	def reset(self):
		self.currentTurn = 0
		self.nextPlayerIdx = 0
		self.messagePool.reset()
		self.resourceUnits = {}
		self.decisions = {}
		for i in range(len(self.player_names)):
			self.resourceUnits[self.player_names[i]] = self.startingRUs[i]
			self.decisions[self.player_names[i]] = ""
		self.gamePhase = "snowdrift"
		
		self._moderator_speak("Now the game starts! Each of you must choose to Volunteer or Ignore.")
		
		self.initialized = True
		initTimestep = TimeStep(
			observation = [], reward = self.get_zero_rewards(), terminal = False
		)
		return initTimestep
	
	
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
			message = Message(agent_name = player_name, content = action, turn = self.currentTurn)
			self.messagePool.append_message(message)
			
			self.decisions[player_name] = "V" if action == "Volunteer" else "I" if action == "Ignore" else ""
			
			self.currentTurn += 1
			if self.nextPlayerIdx < len(self.player_names) - 1:
				self.nextPlayerIdx += 1
				timestep = TimeStep(
					observation = self.get_observation(),
					reward = self.get_zero_rewards(),
					terminal = False
				)
			else:
				self.nextPlayerIdx = 0
				contributedRUs = 0
				for _, decision in self.decisions.items():
					if decision == "V":
						contributedRUs += self.volunteerCost
				projectSucceeded = contributedRUs >= self.neededRUs
				moderatorMessage = ""
				for nation, decision in self.decisions.items():
					moderatorMessage += f"{nation}'s choice: {'Volunteer' if decision == 'V' else 'Ignore'}\n"
				moderatorMessage += f"Result: The project {'succeeds' if projectSucceeded else 'fails'}!\n"
				for nation, decision in self.decisions.items():
					payoff = self.projectReward if projectSucceeded else 0
					if decision == "V":
						payoff -= self.volunteerCost
					self.resourceUnits[nation] += payoff
					moderatorMessage += (
						f"Since "
						f"{nation} "
						f"{'Volunteered' if decision == 'V' else 'Ignored' if decision == 'I' else 'chose nothing this should never happen help'} "
						f"and the project {'succeeded' if projectSucceeded else 'failed'}, "
						f"{nation} {'gains ' if payoff > 0 else 'loses ' if payoff < 0 else 'neither gains nor loses any RUs.'}"
					)
					if payoff == 0:
						moderatorMessage += "\n"
					else:
						if payoff < 0:
							payoff = abs(payoff)
						moderatorMessage += f"{payoff} RUs.\n"
				if projectSucceeded:
					moderatorMessage += "Since the project succeeded, we now move into the second phase of the game."
					self.gamePhase = "prisoners-dilemma"
				else:
					moderatorMessage += "Since the project failed, the game is over."
				self._moderator_speak(moderatorMessage)
				self._moderator_speak(f"{self.resourceUnits}")
				self.currentTurn += 1
				timestep = TimeStep(
					observation = self.get_observation(),
					reward = self.get_zero_rewards(),
					terminal = not projectSucceeded
				)
		elif self.gamePhase == "prisoners-dilemma":
			raise NotImplementedError
		else:
			raise ValueError
		
		if self.is_terminal():
			timestep.terminal = True
		
		return timestep
	
	
	def check_action(self, action: str, player_name: str) -> bool:
		if self.gamePhase == "snowdrift":
			return any(act in action for act in ("Volunteer", "Ignore"))
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
