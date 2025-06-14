from abc import abstractmethod, ABCMeta
from typing import Optional, List

class AdvisorInterface(metaclass=ABCMeta):

    @abstractmethod
    def get_text_suggestions(self, text) -> Optional[List[str]]:
        pass