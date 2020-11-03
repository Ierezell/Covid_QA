"""
This file is made to have configuration variables at the same place
as well with the types
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

from elasticsearch import Elasticsearch

from config import LANGUAGES


class RawEntry(TypedDict):
    type: Literal['page', 'section', 'pdf']
    path: str
    title: str
    content: str
    language: Literal['fr', 'en']
    first_seen_date: str
    children: Optional[List['RawEntry']]


class Link(TypedDict):
    path: str
    start: int
    name: str


class MetaData(TypedDict, total=False):
    links: List[Link]
    keywords: List[str]
    title_embedding: List[float]
    content_embedding: List[float]


class Chunk(RawEntry, MetaData):
    chunk_hash: str
    original_hash: str
    chunk_start: int
    page_content: str
    first_seen_date: datetime
    parent_content_embedding: List[float]
    parent_title_embedding: List[float]
    parent_content: str
    parent_title: str


class Indexes(TypedDict):
    db: Elasticsearch


class Answer(TypedDict):
    score: float
    content: str
    answer: str
    start: int
    end: int
    elected: Literal['qa', 'kw', 'n/a']


class Models(TypedDict, total=False):
    embedder: Dict[LANGUAGES, Any]
    answerer: Dict[LANGUAGES, Any]
    processor: Dict[LANGUAGES, Any]
