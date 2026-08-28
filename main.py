import argparse
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()


def cmd_ingest(args):
    from src.ingest import ingest_pdfs
    from src.retriever import Retriever

    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.is_dir():
        print(f"Directory not found: {pdf_dir}")
        sys.exit(1)

    chunks = ingest_pdfs(pdf_dir, chunk_size=args.chunk_size, overlap=args.overlap)
    if not chunks:
        print("No text extracted. Check that PDFs exist in the directory.")
        return

    Retriever().add_chunks(chunks)
    print(f"Done — {len(chunks)} chunks ingested from {pdf_dir}.")


def cmd_query(args):
    from src.retriever import Retriever
    from src.rag import generate_answer

    chunks = Retriever().query(args.query, k=args.top_k)
    print(f"[retrieve] fetched {len(chunks)} chunks from ChromaDB")
    if not chunks:
        print("No relevant documents found.")
        return

    sources = [f"{c['source']} p{c['page']}" for c in chunks]
    print(f"[generate] using {len(chunks)} chunks: {sources}")
    print(generate_answer(args.query, chunks))


def cmd_crag(args):
    from src.crag import run_crag

    print(run_crag(args.query))


def cmd_triage(args):
    from src.triage import triage_batch, write_report
    from src.triage_tools import TriageTools

    tools = TriageTools(args.data_dir)
    failures = tools.load_failures()
    if not failures:
        print(f"No failures found in {Path(args.data_dir) / 'failures.json'}")
        return
    classifier = None
    if args.online:
        from src.triage import _llm_classifier
        classifier = _llm_classifier
    records = triage_batch(failures, tools, classifier=classifier)
    markdown_path, json_path = write_report(records, args.output_dir)
    print(f"Triage complete: {len(records)} failures")
    print(f"Markdown report: {markdown_path}")
    print(f"JSON report: {json_path}")
    print(f"Tool calls: {len(tools.calls)}; external writes: {sum(call.get('write', False) for call in tools.calls)}")


def main():
    parser = argparse.ArgumentParser(description="Baseline PDF RAG — ChromaDB + Ollama")
    sub = parser.add_subparsers(dest="command")

    p_ingest = sub.add_parser("ingest", help="Ingest PDFs into the vector store")
    p_ingest.add_argument("--pdf-dir", default="pdfs", help="Folder containing PDF files")
    p_ingest.add_argument("--chunk-size", type=int, default=500, help="Words per chunk")
    p_ingest.add_argument("--overlap", type=int, default=50, help="Overlapping words between chunks")

    p_query = sub.add_parser("query", help="Query the RAG pipeline")
    p_query.add_argument("query", help="Question to ask")
    p_query.add_argument("--top-k", type=int, default=5, help="Chunks to retrieve")

    p_crag = sub.add_parser("crag", help="Query using Corrective RAG (LangGraph)")
    p_crag.add_argument("query", help="Question to ask")

    p_triage = sub.add_parser("triage", help="Triage a fixture-backed CI failure batch")
    p_triage.add_argument("--data-dir", default="data", help="Folder containing failure and history fixtures")
    p_triage.add_argument("--output-dir", default="reports", help="Folder for Markdown and JSON reports")
    p_triage.add_argument("--online", action="store_true", help="Use the configured OpenAI-compatible endpoint")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"ingest": cmd_ingest, "query": cmd_query, "crag": cmd_crag, "triage": cmd_triage}[args.command](args)


if __name__ == "__main__":
    main()
