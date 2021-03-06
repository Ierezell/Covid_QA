
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple, cast

import elasticsearch
import numpy as np
import spacy
from config import EMBED_DIM, LANGUAGES, SPACY_MODEL_NAMES
from datatypes import Chunk, Indexes, Models, RawEntry
from embedders.answerer import Answerer
from embedders.embedders import Embedder
from embedders.summarizer import Summarizer
from utils import remove_links, sanitize_text, get_keylemmas


from .chunker import chunker
from .metabuilder import create_metadata


def recurse_add(db_name: str, raw_entry: RawEntry, level: int,
                indexes: Indexes, models: Models,
                parents: List[Chunk] = []) -> None:
    # Clean entry
    raw_entry['content'], links = remove_links(raw_entry['content'])
    raw_entry['title'] = sanitize_text(raw_entry['title'])
    raw_entry['content'] = sanitize_text(raw_entry['content'])
    first_seen_date = datetime.strptime(raw_entry['first_seen_date'],
                                        "%m/%d/%Y")

    # Chunk entry content
    current_parents: List[Chunk] = []
    for chunk in chunker(raw_entry, models):
        chunk.pop('children', None)
        chunk['first_seen_date'] = first_seen_date
        chunk['page_content'] = raw_entry['content']
        chunk['lemma_content'] = " ".join(get_keylemmas(
            chunk['content'], models["processor"]["fr"]))
        chunk['lemma_page_content'] = " ".join(
            get_keylemmas(chunk['page_content'], models["processor"]["fr"]))

        metadatas = create_metadata(chunk, links, models,
                                    db_name.split('_')[1])

        chunk.update(metadatas)  # type: ignore

        if parents:
            chunk['parent_content_embedding'] = np.sum(
                np.array([p['content_embedding'] for p in parents]), axis=0
            ).tolist()

            chunk['parent_title_embedding'] = np.sum(
                np.array([p['title_embedding'] for p in parents]), axis=0
            ).tolist()

            chunk['parent_content'] = " ".join([p['content'] for p in parents])
            chunk['parent_title'] = parents[0]['title']

        else:
            chunk['parent_content_embedding'] = np.full(EMBED_DIM,
                                                        np.finfo(float).eps
                                                        ).tolist()
            chunk['parent_title_embedding'] = np.full(EMBED_DIM,
                                                      np.finfo(float).eps
                                                      ).tolist()

        current_parents.append(chunk)

        if chunk['content'] != chunk['title']:
            indexes['db'].index(index=db_name,
                                id=chunk['chunk_hash'],
                                body=chunk)

    for child in raw_entry.get('children', []):
        recurse_add(db_name, child, parents=current_parents,
                    indexes=indexes, models=models, level=level+1)


def create_models(langs: List[LANGUAGES]) -> Models:
    processor: Dict[LANGUAGES, Any] = {}

    for lang, model in SPACY_MODEL_NAMES.items():
        if lang in langs:
            nlp = spacy.load(model)
            nlp.add_pipe("sentencizer", first=True)

            processor.update(cast(Dict[LANGUAGES, Any], {lang: nlp}))

    embedder: Dict[LANGUAGES, Embedder] = {}
    answerer: Dict[LANGUAGES, Answerer] = {}
    summarizer: Dict[LANGUAGES, Summarizer] = {}

    for lang in langs:
        embedder.update({lang: Embedder(processor[lang], lang, True)})
        answerer.update({lang: Answerer(cast(LANGUAGES, f'qa_{lang}'))})
        summarizer.update(
            {lang: Summarizer(cast(LANGUAGES, f'sum_{lang}'), True)})

    models: Models = {"embedder": embedder, "answerer": answerer,
                      "processor": processor, "summarizer": summarizer}

    return models


def create_indexes(db_name: str) -> Tuple[Indexes, bool]:
    need_creation = False

    es = elasticsearch.Elasticsearch()

    indexes: Indexes = {"db": es}

    if not es.indices.exists(index=db_name):
        index_body = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "default": {
                            # "filter": ["stop"],
                            # "type": "standard",
                            "type": "french",
                            "language": "french",
                            "stopwords": "_french_"
                        },
                    }
                }
            },
            "mappings": {
                "properties": {
                    "title_embedding": {
                        "type": "dense_vector",
                        "dims": EMBED_DIM
                    },
                    "content_embedding": {
                        "type": "dense_vector",
                        "dims": EMBED_DIM
                    },
                    "parent_content_embedding": {
                        "type": "dense_vector",
                        "dims": EMBED_DIM
                    },
                    "parent_title_embedding": {
                        "type": "dense_vector",
                        "dims": EMBED_DIM
                    },
                    "keywords": {"type": "keyword"},
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "parent_content": {"type": "text"},
                    "parent_title": {"type": "text"},
                    "original_content": {"type": "text"},
                    "first_seen_date": {"type": "date"},
                }
            }
        }

        es.indices.create(index=db_name, ignore=400, body=index_body)
        need_creation = True

    return indexes, need_creation


def preprocess(db_name: str, raw_entry: RawEntry) -> Tuple[Indexes, Models]:
    start = time.time()
    models = create_models(['fr'])
    print(f"Models created in {time.time()-start}s")

    start = time.time()
    indexes, need_creation = create_indexes(db_name)
    print(f"Indexes created in {time.time()-start}s")

    if need_creation:
        print("Doing all : need creation")
        start = time.time()
        recurse_add(db_name, raw_entry, parents=[], level=0,
                    indexes=indexes, models=models)
        print(f"Entries added in {time.time()-start}s")

    return indexes, models
