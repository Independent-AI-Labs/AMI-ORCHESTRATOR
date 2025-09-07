from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, dgraph_store):
        self.dgraph_store = dgraph_store

    @abstractmethod
    def execute(self, task):
        pass
