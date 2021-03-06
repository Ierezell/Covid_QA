from datetime import datetime
from typing import Any, List, Tuple, cast

from datatypes import Answer, Indexes, Models, RetrieveOptions

from utils import get_keylemmas


def retrieve_docs(db_name: str, indexes: Indexes, models: Models,
                  question: str, options: RetrieveOptions
                  ) -> Tuple[List[float], List[Any], float, int]:

    question_embed = models['embedder']['fr'].embed(question, "all")
    lem_question = " ".join(get_keylemmas(question, models['processor']['fr']))
    supports, max_score, hits = retrieve_es(db_name, indexes['db'], question,
                                            lem_question,
                                            question_embed, options)

    return question_embed, supports, max_score, hits


def retrieve_es(db_name: str, es: Any, question: str, lem_question: str,
                question_embed: List[float], options: RetrieveOptions
                ) -> Tuple[List[Any], float, int]:
    query = {'multi_match': {
        'query':  lem_question, 'fuzziness': "AUTO", "type": "best_fields",
        # cross_fields, most_fields, best_fields
        'fields': [
            f"title^{options['boost_title']}",
            f"content^{options['boost_content']}",
            f"page_content^{options['boost_page']}",
            f"lemma_content^{options['boost_lem']}",
            f"lemma_page_content^{options['boost_page_lem']}",
            f"parent_title^{options['boost_parent_title']}",
            f"parent_content^{options['boost_parent_content']}"
        ]}}

    dense_script = {
            "source": f"""
            double content = {options['boost_content_embedding']} * cosineSimilarity(params.question_embed, 'content_embedding'); 
            double title = {options['boost_title_embedding']} * cosineSimilarity(params.question_embed, 'title_embedding');
            double parent = {options['boost_parent_embedding']} * cosineSimilarity(params.question_embed, 'parent_title_embedding');
            double embed_score = content + title + parent + {options['boost_parent_embedding'] + options['boost_title_embedding'] + options['boost_content_embedding']};
            double date_score =  {options['boost_date']} * decayDateGauss(params.origin, params.scale, params.offset, params.decay, doc['first_seen_date'].value);
            return _score + embed_score + date_score;
            """,  # noqa E501
            "params": {
                "origin": datetime.now(),
                "scale": "30d",
                "offset": "0",
                "decay": 0.5,
                "question_embed": question_embed,
                }}

    if options["retrieve_mode"] == "sparse":
        es_query_body = {
            "size": options['retrieve_nb'],
            "min_score": "1.0",
            "query":  query,
        }

    elif options["retrieve_mode"] == "dense":
        es_query_body = {
            "size": options['retrieve_nb'],
            "min_score": "1.0",
            "query": {"script_score": {"query": {"match_all": {}},
                                       "script": dense_script}}
        }

    elif options["retrieve_mode"] == "hybrid":
        es_query_body = {
            "size": options['retrieve_nb'],
            "min_score": "1.0",
            "query": {"script_score": {"query": query, "script": dense_script}}
        }

    else:
        raise RuntimeError(
            "Retrieval mode can be only [sparse | dense | hybrid]")

    res = es.search(index=db_name, body=es_query_body)
    max_score = res['hits']['max_score']
    hits = res['hits']['total']

    supports: List[Answer] = []
    for doc in res['hits']['hits']:
        supports.append(cast(Answer,
                             {'score': doc['_score'], **doc["_source"]})
                        )

    return supports, max_score, hits
