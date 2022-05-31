from typing import Union, List

from fastapi import FastAPI, Query
from pydantic import BaseModel

import os
from itertools import combinations
from py2neo import Graph
import spacy


class Item(BaseModel):
    texts: list = []


class App:
    def __init__(self, uri, user, password):
        self.graph = Graph(uri, auth=(user, password))
        self.nlp = spacy.load("da_core_news_sm")

    def extract_nouns(self, texts):
        noun_lists = list()
        for doc in list(self.nlp.pipe(texts)):
            nouns = [tok.text for tok in doc if tok.tag_ == "NOUN"]
            noun_lists.append(nouns)
        return noun_lists

    def make_edgelist(self, noun_lists):
        edgelist = list()
        for noun_list in noun_lists:
            for a, b in combinations(noun_list, 2):
                edgelist.append(tuple(sorted((a, b))))
        return edgelist

    def make_nodes_and_edge(self, word1, word2):
        self.graph.run(
            """
                MERGE (w1:Word {text: $word1})
                MERGE (w2:Word {text: $word2})
                MERGE (w1)-[r:REL]->(w2)
            ON CREATE SET r.weight = 1
            ON MATCH SET r.weight = r.weight + 1
        """,
            parameters={"word1": word1, "word2": word2},
        )


def run_script(texts):
    uri = os.environ.get("MY_NEO4J_URI")
    user = os.environ.get("MY_NEO4J_USR")
    password = os.environ.get("MY_NEO4J_PSW")

    app = App(uri, user, password)
    noun_lists = app.extract_nouns(texts)
    edgelist = app.make_edgelist(noun_lists)
    for word1, word2 in edgelist:
        app.make_nodes_and_edge(word1, word2)


app = FastAPI()


@app.post("/items/")
async def create_item(item: Item):
    run_script(item.texts)
    return item
