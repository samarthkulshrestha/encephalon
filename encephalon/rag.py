import ollama
import uuid

from encephalon.tokenize_ import tokenize_file


def add_file(fp, source, col):
    tokens = tokenize_file(fp)
    print("INFO: adding vectors to collection")
    for d in tokens:
        response = ollama.embeddings(model="nomic-embed-text",
                                     prompt=f"search document:{d}")
        embedding = response["embedding"]
        col.add(
            ids=[str(uuid.uuid4())],
            embeddings=[embedding],
            documents=[d],
            metadatas=[{"source": str(source)}]
        )
    print("INFO: done")

def vector_search(q, col):
    response = ollama.embeddings(model="nomic-embed-text",
                                 prompt=f"search query: {q}")
    res = col.query(
        query_embeddings=[response["embedding"]],
        n_results=3
    )
    for meta in res["metadatas"]:
        print(f"source: {meta[0]["source"]}")
    # for doc in res["documents"]:
    #     print(f"{doc[0]}")
    return res

class EncephalonRAG:
    def __init__(self, rag_chain, collection):
        self.rag_chain = rag_chain
        self.collection = collection

    def run(self, question):
        print("INFO: searching...")
        response = ollama.embeddings(model="nomic-embed-text",
                                     prompt=f"search query: {question}")
        results = self.collection.query(
            query_embeddings=[response["embedding"]],
            n_results=3
        )

        documents = results["documents"]
        print("INFO: done")

        doc_texts = "\\n".join([doc[0] for doc in documents])
        print("INFO: invoking llm")
        answer = self.rag_chain.stream({"question": question, "documents": doc_texts})
        for chunk in answer:
            print(chunk, end='', flush=True)
        print('\n')
