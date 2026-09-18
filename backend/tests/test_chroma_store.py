"""ChromaDB backend returns the same science as the CSV store (offline hashing embeddings)."""
import pytest

pytest.importorskip("chromadb")

from app.pipeline import assess  # noqa: E402
from app.retrieval.chroma_store import ChromaStore  # noqa: E402
from app.retrieval.store import CsvStore  # noqa: E402


@pytest.fixture(scope="module")
def chroma(tmp_path_factory):
    return ChromaStore(path=str(tmp_path_factory.mktemp("chroma")))


@pytest.mark.parametrize("site_id", ["beed_wheat", "anantapur_groundnut", "dharwad_cotton", "unknown_plot"])
def test_chroma_and_csv_assessments_identical(chroma, site_id):
    csv = CsvStore()
    a = assess(chroma.get_site(site_id), chroma)[0].model_dump(exclude={"supporting_passages"})
    b = assess(csv.get_site(site_id), csv)[0].model_dump(exclude={"supporting_passages"})
    assert a == b


def test_metadata_filters_and_semantic_search(chroma):
    assert {c.target_metric for c in chroma.claims_for_metrics(["soc_percent"])} == {"soc_percent"}
    assert chroma.zone_for(18.99, 75.76) == "semi_arid"
    hits = chroma.search("keeping water in the soil", 5)
    assert any(h["target_metric"] == "moisture_percent" for h in hits)


def test_conversation_and_assessment_persistence(chroma):
    chroma.save_conversation("t1", {"soc_percent": 0.3})
    chroma.add_message("t1", "user", "hello")
    assert chroma.get_conversation("t1")["messages"][0]["content"] == "hello"
    aid = chroma.save_assessment("s", {}, {"x": 1}, "text")
    assert chroma.get_assessment(aid)["output"] == {"x": 1}
