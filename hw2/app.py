"""hw2 custom RAG application.

Extends the LangChain RAG example from Lab 02.3 (02_LangChain/07_RAG) with
support for loading structured JSON documents via LangChain's built-in
JSONLoader (langchain_community.document_loaders.JSONLoader), a loader that
is not used anywhere in the original lab code.

Run this file directly to build (or reuse) a local Chroma vector database
from the documents under rag_data/ and then answer questions about them
from the command line.

Configuration is read entirely from environment variables (see
.env.example) so no API keys or project IDs are hard-coded here.
"""

import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    CSVLoader,
    DirectoryLoader,
    Docx2txtLoader,
    JSONLoader,
    PyPDFDirectoryLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load variables from a local .env file, if present, into the environment.
load_dotenv()

RAG_DATA_DIR = os.path.join(os.path.dirname(__file__), "rag_data")
CHROMA_DIR = os.path.join(RAG_DATA_DIR, ".chromadb")

# Configure the embedding model, matching the lab's use of Vertex AI
# embeddings (higher quota than the AI Studio Generative AI embeddings).
embedding_function = VertexAIEmbeddings(
    model_name="gemini-embedding-001",
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location="us-west1",
)

vectorstore = Chroma(
    embedding_function=embedding_function,
    persist_directory=CHROMA_DIR,
)


def load_docs(docs):
    """Split documents into chunks and add their embeddings to Chroma."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = splitter.split_documents(docs)
    if splits:
        vectorstore.add_documents(documents=splits)


def load_txt(directory):
    """Load every .txt file in directory into the vector database."""
    load_docs(DirectoryLoader(directory, glob="**/*.txt", loader_cls=TextLoader).load())


def load_pdf(directory):
    """Load every PDF in directory into the vector database."""
    load_docs(PyPDFDirectoryLoader(directory).load())


def load_docx(directory):
    """Load every .docx file in directory into the vector database."""
    load_docs(DirectoryLoader(directory, glob="**/*.docx", loader_cls=Docx2txtLoader).load())


def load_md(directory):
    """Load every Markdown file in directory into the vector database."""
    load_docs(DirectoryLoader(directory, glob="**/*.md", loader_cls=UnstructuredMarkdownLoader).load())


def load_csv(directory):
    """Load every CSV file in directory into the vector database."""
    load_docs(DirectoryLoader(directory, glob="**/*.csv", loader_cls=CSVLoader).load())


def _json_metadata(record, metadata):
    """Copy a JSON record's title into the loaded document's metadata."""
    metadata["source"] = record.get("title", metadata.get("source"))
    metadata["title"] = record.get("title")
    return metadata


def load_json(directory):
    """Load every JSON file in directory into the vector database.

    This is the homework's custom functionality: LangChain ships a
    JSONLoader (langchain_community.document_loaders.JSONLoader) that is
    not used anywhere in the Lab 02.3 example code. Each JSON file here is
    expected to hold a list of objects with "title" and "content" keys
    (see rag_data/json/tech_facts.json). jq_schema=".[]" iterates that
    list, content_key="content" picks the field to embed, and
    _json_metadata copies the title into the chunk's metadata so it shows
    up as a readable source when the RAG chain cites its context.
    """
    docs = []
    for filename in os.listdir(directory):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(directory, filename)
        loader = JSONLoader(
            file_path=path,
            jq_schema=".[]",
            content_key="content",
            metadata_func=_json_metadata,
        )
        docs.extend(loader.load())
    load_docs(docs)


def build_database():
    """Populate the vector database from rag_data/ if it is still empty."""
    if vectorstore._collection.count() > 0:
        print("Vector database already populated, skipping reload.")
        return

    sources = {
        "txt": load_txt,
        "pdf": load_pdf,
        "docx": load_docx,
        "md": load_md,
        "csv": load_csv,
        "json": load_json,
    }
    for name, loader_fn in sources.items():
        directory = os.path.join(RAG_DATA_DIR, name)
        if os.path.isdir(directory) and os.listdir(directory):
            print(f"Loading {name} files from: {directory}")
            loader_fn(directory)


def build_chain():
    """Build the retrieval-augmented generation chain used to answer questions."""
    llm = ChatGoogleGenerativeAI(model=os.getenv("GOOGLE_MODEL", "gemini-3.6-flash"))
    retriever = vectorstore.as_retriever()

    prompt = ChatPromptTemplate.from_template(
        """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say that you don't know.
Use three sentences maximum and keep the answer concise.

Question: {question}

Context: {context}

Answer:"""
    )

    def format_docs(docs):
        """Join retrieved documents, each labeled with its source, into one context string."""
        return "\n\n".join(
            f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}"
            for doc in docs
        )

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )


def list_sources():
    """Print the unique source names currently indexed in the vector database."""
    sources = set()
    for metadata in vectorstore.get()["metadatas"]:
        if metadata.get("source"):
            sources.add(metadata["source"])
    for source in sorted(sources):
        print(f"  {source}")


def main():
    """Build the database if needed, then run an interactive question loop."""
    build_database()
    rag_chain = build_chain()

    print("Welcome to my hw2 RAG app. Ask a question about the documents below (blank line to quit):")
    list_sources()

    while True:
        question = input("llm>> ")
        if not question:
            break
        print(rag_chain.invoke(question))


if __name__ == "__main__":
    main()
