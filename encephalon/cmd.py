import argparse
import chromadb
import os
import readline

from chromadb.config import DEFAULT_TENANT, DEFAULT_DATABASE, Settings
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from encephalon.ingest import DATA_HOME, get_transcript, read_pdf, read_epub, read_text
from encephalon.rag import EncephalonRAG, vector_search

DBDIR = os.path.join(DATA_HOME, "encephalon/vectordb")

chroma_client = chromadb.PersistentClient(
    path=DBDIR,
    settings=Settings(),
    tenant=DEFAULT_TENANT,
    database=DEFAULT_DATABASE
)

collection = chroma_client.get_or_create_collection("Knowledge")


HIST_FILE = os.path.join(DATA_HOME, ".cmdhist")

def setup_readline():
    try:
        readline.read_history_file(HIST_FILE)
    except FileNotFoundError:
        pass

    readline.set_history_length(1000)
    readline.parse_and_bind("tab: complete")

def save_history():
    readline.write_history_file(HIST_FILE)


def main():
    setup_readline()
    parser = argparse.ArgumentParser(description="An AI-powered knowledge database.")

    parser.add_argument("-y", "--youtube", type=str, nargs='*',
                        metavar="youtube_link", default=None,
                        help="Adds the information from a YouTube \
                        video to Knowledge.")

    parser.add_argument("-p", "--pdf", type=str, nargs='*',
                        metavar="pdf_fp", default=None,
                        help="Adds the information from a PDF \
                        document to Knowledge.")

    parser.add_argument("-e", "--epub", type=str, nargs='*',
                        metavar="epub_fp", default=None,
                        help="Adds the information from an EPUB \
                        file to Knowledge.")

    parser.add_argument("-t", "--txt", type=str, nargs='*',
                        metavar="txt_fp", default=None,
                        help="Adds the information from a text \
                        document to Knowledge.")

    parser.add_argument("-s", "--search", type=str, nargs='*',
                        metavar="txt_fp", default=None,
                        help="Performs a vector search on the \
                        given query.")

    args = parser.parse_args()
    if args.youtube != None:
        get_transcript(args.youtube[0], collection)
    elif args.pdf != None:
        read_pdf(args.pdf[0], collection)
    elif args.epub != None:
        read_epub(args.epub[0], collection)
    elif args.txt != None:
        read_text(args.txt[0], collection)
    elif args.search != None:
        vector_search(args.search[0], collection)
    else:
        prompt = PromptTemplate(
            template="""Use the following documents to answer
            the question accurately. Do not mention the source
            explicitly—respond as if the knowledge is yours.
            Keep the answer concise, less than ~150 words.
            If you can't find the answer in the documents,
            just say that you don't know.
            Question: {question}
            Documents: {documents}
            """,
            input_variables=["question", "documents"],
        )

        llm = ChatOllama(
            model="llama3.2:1b",
            temperature=0,
            disable_streaming=False
        )

        rag_chain = prompt | llm | StrOutputParser()
        rag_application = EncephalonRAG(rag_chain, collection)

        try:
            while True:
                try:
                    question = input(">>> ")
                    if question.strip().lower() == "bye":
                        break
                    rag_application.run(question)
                except EOFError:
                    break
        finally:
            save_history()
            print("\nCatch you on the flip!\nPeace out.")

if __name__ == "__main__":
    main()
