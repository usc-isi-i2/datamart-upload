from abc import ABC, abstractmethod
import typing
from etk.document import Document
from typing import TypeVar
DatasetID = TypeVar('DatasetID')  # a string indicate the dataset id


class PreParsedResult(object):
    def __init__(self, content: list, metadata: typing.List[dict] = None):
        self._content = content
        self._metadata = metadata

    @property
    def metadata(self):
        return self._metadata

    @property
    def content(self):
        return self._content


class ParserBase(ABC):
    """Abstract class of parser, should be extended for other parsers.

    """

    @abstractmethod
    def load_and_preprocess(self, **kwargs) -> PreParsedResult:
        """
        Implement loading and preprocessing method
        """
        pass

    def model_data(self, doc: Document, inputs: PreParsedResult, **kwargs) -> typing.Union[Document, DatasetID]:
        """
        Implement data modeling method and append this to doc
        """
        pass
