from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
import os
from pinecone import Pinecone, ServerlessSpec
from langchain.vectorstores import Pinecone as LangChainPineconeVectorStore
from langchain.embeddings import HuggingFaceEmbeddings
from fastapi.middleware.cors import CORSMiddleware
import logging
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = "stocks"
namespace = "stock-descriptions"


origins = [
    "http://localhost:3000",  # Next.js frontend
    # Add your production frontend URL here, e.g., "https://yourdomain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allow specified origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

try:
    pc = Pinecone(
        api_key=PINECONE_API_KEY,
        environment=PINECONE_ENVIRONMENT
    )
    logger.info("Pinecone client initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize Pinecone client: %s", str(e))
    raise

# Check if the index exists; if not, create it
if PINECONE_INDEX_NAME not in pc.list_indexes().names():
    try:
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=768,  # Ensure this matches your embedding dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws',    # Adjust based on your cloud provider
                region='us-east-1'  # Adjust based on your region
            )
        )
        logger.info(f"Created Pinecone index: {PINECONE_INDEX_NAME}")
    except Exception as e:
        logger.error("Failed to create Pinecone index: %s", str(e))
        raise

# Specify the index
try:
    index = pc.Index(PINECONE_INDEX_NAME)
    logger.info(f"Connected to Pinecone index: {PINECONE_INDEX_NAME}")
except Exception as e:
    logger.error("Failed to connect to Pinecone index: %s", str(e))
    raise

# Initialize embeddings with explicit model_name to avoid deprecation warning
try:
    hf_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    logger.info("HuggingFaceEmbeddings initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize HuggingFaceEmbeddings: %s", str(e))
    raise

# Initialize LangChain's Pinecone VectorStore with text_key
try:
    vectorstore = LangChainPineconeVectorStore(
        index=index,
        embedding=hf_embeddings,
        text_key="text",  # Ensure this matches the key in your documents
        namespace=namespace
    )
    logger.info("LangChain Pinecone VectorStore initialized successfully.")
except Exception as e:
    logger.error("Failed to initialize LangChain Pinecone VectorStore: %s", str(e))
    raise

class SearchRequest(BaseModel):
    query: str
    k: int = 5  # Default number of results

class SearchResult(BaseModel):
    text: str
    metadata: Dict

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

@app.post("/research", response_model=SearchResponse)
def research(search: SearchRequest):
    if not search.query:
        raise HTTPException(status_code=400, detail="Query parameter is required.")
    try:
        results = vectorstore.similarity_search(search.query, k=search.k)
        json_results = [
            SearchResult(text=r.page_content, metadata=r.metadata) for r in results
        ]
        return SearchResponse(query=search.query, results=json_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Optional: Test query when running the script directly
def test_query(query: str):
    try:
        results = vectorstore.similarity_search(query, k=5)
        logger.info("Query: %s", query)
        logger.info("Number of results: %d", len(results))
        for i, result in enumerate(results):
            logger.info("Result %d:", i+1)
            logger.info("Text: %s", result.page_content)
            logger.info("Metadata: %s", result.metadata)
            logger.info("---")
    except Exception as e:
        logger.error("Error during test query: %s", str(e))



