"""Offline, deterministic text embeddings for ChromaDB.

Feature-hashed bag of stemmed unigrams + bigrams, with a small agronomy synonym map so that
"water" finds "moisture" and "bees" finds "pollinator". There is no model download, no network,
the same vector on every machine, and roughly zero memory cost. Set EMBEDDING_MODEL=minilm to use
Chroma's ONNX all-MiniLM-L6-v2 instead where downloads are possible.
"""
from __future__ import annotations

import hashlib
import math
import re

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

DIM = 384
STOP = set("""a an and are as at be by can for from has have in into is it its of on or that the their them then
there these this to was were which while with without when where who will would than also only more most""".split())
SYNONYMS = {
    "water": "moistur", "moistur": "water", "rain": "rainfal", "rainfal": "rain", "drought": "dry", "dry": "drought",
    "soc": "carbon", "carbon": "soc", "organ": "carbon", "bee": "pollin", "pollin": "bee", "bird": "speci",
    "insect": "speci", "biodivers": "speci", "speci": "biodivers", "tree": "agroforestri", "agroforestri": "tree",
    "hedg": "margin", "hedgerow": "margin", "margin": "hedgerow", "pesticid": "insecticid", "insecticid": "pesticid",
    "graze": "livestock", "livestock": "graze", "green": "ndvi", "ndvi": "veget", "veget": "ndvi",
    "fragment": "isol", "isol": "fragment", "mulch": "residu", "residu": "mulch",
}
SUFFIXES = ("ations", "ation", "ities", "ity", "ings", "ing", "ness", "ies", "ied", "ed", "es", "ly", "al", "s", "e", "y")


def stem(word: str) -> str:
    for suf in SUFFIXES:
        if len(word) > len(suf) + 2 and word.endswith(suf):
            return word[: -len(suf)]
    return word


def features(text: str) -> list[str]:
    words = [stem(w) for w in re.findall(r"[a-z]+", text.lower().replace("_", " ")) if w not in STOP and len(w) > 1]
    feats = list(words)
    feats += [SYNONYMS[w] for w in words if w in SYNONYMS]
    feats += [f"{a}_{b}" for a, b in zip(words, words[1:])]
    return feats


def embed(text: str) -> np.ndarray:
    vec = np.zeros(DIM, dtype=np.float32)
    counts: dict[str, int] = {}
    for f in features(text):
        counts[f] = counts.get(f, 0) + 1
    for f, n in counts.items():
        h = int.from_bytes(hashlib.md5(f.encode()).digest()[:8], "little")
        weight = (1 + math.log(n)) * (0.6 if "_" in f else 1.0)
        vec[h % DIM] += weight if (h >> 32) & 1 else -weight
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm else vec


class HashingEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [embed(t) for t in input]

    @staticmethod
    def name() -> str:
        return "hashing_bow_agronomy"

    def get_config(self) -> dict:
        return {"dim": DIM}

    @staticmethod
    def build_from_config(config: dict) -> "HashingEmbeddingFunction":
        return HashingEmbeddingFunction()


def get_embedding_function():
    import os
    if os.getenv("EMBEDDING_MODEL", "hashing").lower() == "minilm":
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        return DefaultEmbeddingFunction()
    return HashingEmbeddingFunction()
