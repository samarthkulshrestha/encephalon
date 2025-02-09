import tiktoken
import re


def chunk_text(text, chunk_size=256, overlap=32):
    """
    Splits text into chunks of approximately `chunk_size` tokens with `overlap` between chunks.
    Uses `tiktoken` for token counting.
    """
    encoding = tiktoken.get_encoding("cl100k_base")  # Change based on LLaMA's tokenizer
    tokens = encoding.encode(text)

    chunks = []
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk = tokens[i : i + chunk_size]
        chunks.append(encoding.decode(chunk))

    return chunks

def preprocess_markdown(md_text):
    """
    Preprocess Markdown by keeping structure but ensuring logical splits.
    """
    sections = re.split(r'(?=^#{1,6} )', md_text, flags=re.MULTILINE)  # Split on headings
    processed_chunks = []

    for section in sections:
        if not section.strip():
            continue
        processed_chunks.extend(chunk_text(section))

    return processed_chunks

def tokenize_file(file_path):
    """
    Reads a text or Markdown file and tokenizes it into uniform chunks.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if file_path.endswith(".md"):
        return preprocess_markdown(content)
    else:
        return chunk_text(content)

