from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from sentence_transformers import CrossEncoder

from src.retriever import Retriever
from src.rag import generate_answer, _client, MODEL

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_N = 3
_reranker = CrossEncoder(RERANK_MODEL)

ABSTAIN_MESSAGE = (
    "INSUFFICIENT_EVIDENCE: no retrieved chunk was graded relevant to the query. "
    "Refusing to answer rather than guess."
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class CRAGState(TypedDict):
    query: str
    documents: list[dict]
    relevance_score: str   # "relevant" | "irrelevant"
    generation: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def retrieve(state: CRAGState) -> CRAGState:
    chunks = Retriever().query(state["query"], k=20)
    print(f"[retrieve] fetched {len(chunks)} chunks from ChromaDB")
    return {**state, "documents": chunks}


def rerank(state: CRAGState) -> CRAGState:
    pairs = [[state["query"], c["text"]] for c in state["documents"]]
    scores = _reranker.predict(pairs)
    ranked = sorted(zip(scores, state["documents"]), key=lambda x: x[0], reverse=True)
    print(f"[rerank]   top {RERANK_TOP_N} of {len(ranked)} chunks:")
    for score, chunk in ranked[:RERANK_TOP_N]:
        print(f"           score={score:.4f}  {chunk['source']} p{chunk['page']} — {chunk['text'][:60]!r}")
    top_chunks = [chunk for _, chunk in ranked[:RERANK_TOP_N]]
    return {**state, "documents": top_chunks}


def grade_documents(state: CRAGState) -> CRAGState:
    relevant = []
    for chunk in state["documents"]:
        response = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Is the following document chunk relevant to the question?\n"
                        "Answer with only 'yes' or 'no'.\n\n"
                        f"Question: {state['query']}\n\n"
                        f"Chunk:\n{chunk['text']}"
                    ),
                }
            ],
        )
        verdict = response.choices[0].message.content.strip().lower()
        label = "PASS" if verdict.startswith("yes") else "FAIL"
        print(f"[grade]    [{label}] {chunk['source']} p{chunk['page']} — {chunk['text'][:60]!r}")
        if verdict.startswith("yes"):
            relevant.append(chunk)

    is_relevant = len(relevant) > 0
    print(f"[grade]    {len(relevant)}/{len(state['documents'])} chunks passed → {'generate' if is_relevant else 'abstain'}")
    return {
        **state,
        "documents": relevant,
        "relevance_score": "relevant" if is_relevant else "irrelevant",
    }


def generate(state: CRAGState) -> CRAGState:
    if state["relevance_score"] != "relevant" or not state["documents"]:
        print("[generate]  no relevant chunks → returning abstain message")
        return {**state, "generation": ABSTAIN_MESSAGE}
    sources = [f"{c['source']} p{c['page']}" for c in state["documents"]]
    print(f"[generate]  using {len(state['documents'])} chunks: {sources}")
    answer = generate_answer(state["query"], state["documents"])
    return {**state, "generation": answer}


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(CRAGState)

    graph.add_node("retrieve", retrieve)
    graph.add_node("rerank", rerank)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("generate", generate)

    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "grade_documents")
    graph.add_edge("grade_documents", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


_graph = build_graph()


def run_crag(query: str) -> str:
    state = _graph.invoke({"query": query, "documents": [], "relevance_score": "", "generation": ""})
    return state["generation"]
