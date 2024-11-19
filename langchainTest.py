from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_ollama.llms import OllamaLLM
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler


# model = ChatOllama(model = "llama3.1:70", temperature = 0.3)
#
# history = ChatPromptTemplate.from_messages(
# 	[
# 		("system", "You are a helpful pirate chatbot. answer all questions while talking like a pirate."),
# 		("human", "{input}")
# 	]
# )
# chain = history | model
#
# chain.invoke({"input": "What is LangChain?"})

llm = OllamaLLM(model = "llama2", callback_manager = CallbackManager([StreamingStdOutCallbackHandler()]))
llm.invoke("Tell me 5 facts about Roman history:")
