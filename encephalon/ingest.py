import ebooklib
import os
import pathlib
import pymupdf4llm
import re
import warnings
import shutil

from bs4 import BeautifulSoup
from ebooklib import epub
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from encephalon.rag import add_file

DATA_HOME = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share/"))
CACHEDIR = os.path.join(DATA_HOME, "encephalon/cache")

def video_id(value):
    """
    Examples:
    - http://youtu.be/SA2iWivDJiE
    - http://www.youtube.com/watch?v=_oPAwA_Udwc&feature=feedu
    - http://www.youtube.com/embed/SA2iWivDJiE
    - http://www.youtube.com/v/SA2iWivDJiE?version=3&amp;hl=en_US
    """
    query = urlparse(value)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    return None


def get_transcript(url: str, collection) -> str:
    vid_id = video_id(url)
    transcript = YouTubeTranscriptApi.get_transcript(vid_id)
    formatter = TextFormatter()
    txt_transcript = formatter.format_transcript(transcript)

    with open(os.path.join(CACHEDIR, "source/trans/", f"{vid_id}.txt"), "w") as f:
        f.write(url)

    fn = f"{vid_id}_trans.txt"
    fp = os.path.join(CACHEDIR, "proc/trans/", fn)
    with open(fp, 'w', encoding='utf-8') as txt_file:
        txt_file.write(txt_transcript)

    add_file(fp, url, collection)
    return fp

def read_pdf(filename: str, collection) -> str:
    md_text = pymupdf4llm.to_markdown(filename)

    shutil.copy2(os.path.join(os.getcwd(), filename),
                 os.path.join(CACHEDIR, "source/pdf"))

    source = os.path.join(CACHEDIR, "source/pdf", filename)

    fn = f"{filename.split(".")[0]}.md"
    fp = os.path.join(CACHEDIR, "proc/pdf/",  fn)

    pathlib.Path(fp).write_bytes(md_text.encode())

    add_file(fp, source, collection)
    return fp

def read_epub(filename: str, collection) -> str:
    warnings.simplefilter(action='ignore', category=FutureWarning)
    book = epub.read_epub(filename, {"ignore_ncx": True})
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            chapters.append(item.get_content())
    blacklist = ['[document]', 'noscript', 'header', 'html', 'meta', 'head',
                 'input', 'script', 'style']

    text = ""
    for chap in chapters:
        out = ""
        soup = BeautifulSoup(chap, 'html.parser')
        txt = soup.find_all(string=True)
        for t in txt:
            if t.parent.name not in blacklist:
                out += '{}'.format(t)
        text += out

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r'^\n+', '', text)
    lines = [line.strip() for line in text.splitlines()]
    cleaned_text = "\n".join(re.sub(r'\s+', ' ', line) for line in lines)

    def convert_headings(text):
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line.isupper() and len(line) > 3:  # Treat as heading if all uppercase
                lines[i] = f"## {line}"  # Convert to Markdown heading
        return "\n".join(lines)

    cleaned_text = convert_headings(cleaned_text)

    cleaned_text = re.sub(r'(?m)^\s*[-*]\s+', '- ', cleaned_text)
    cleaned_text = re.sub(r'(?m)^\s*\d+\.\s+', lambda m: f"{m.group(0).strip()} ", cleaned_text)

    shutil.copy2(os.path.join(os.getcwd(), filename),
                 os.path.join(CACHEDIR, "source/epub"))

    source = os.path.join(CACHEDIR, "source/epub", filename)

    fn = f"{filename.split(".")[0]}.md"
    fp = os.path.join(CACHEDIR, "proc/epub/", fn)
    with open(fp, 'w', encoding='utf-8') as txt_file:
        txt_file.write(cleaned_text)

    add_file(fp, source, collection)
    return fp

def read_text(filename: str, collection):
    shutil.copy2(os.path.join(os.getcwd(), filename),
                 os.path.join(CACHEDIR, "source/txt"))
    fp = os.path.join(CACHEDIR, "source/txt/", filename)

    add_file(fp, fp, collection)
    return fp
