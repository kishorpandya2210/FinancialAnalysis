# index_data.py

import os
import json
import requests
import yfinance as yf
import concurrent.futures
from dotenv import load_dotenv
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Pinecone as PineconeVectorStore
import pinecone

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = "stocks"
NAMESPACE = "stock-descriptions"

# Initialize Pinecone
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

# Create the index if it doesn't exist
if PINECONE_INDEX_NAME not in pinecone.list_indexes():
    pinecone.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=768,  # Ensure this matches your embedding dimension
        metric="cosine"
    )

# Connect to the index
index = pinecone.Index(PINECONE_INDEX_NAME)

# Initialize embeddings with explicit model_name to avoid deprecation warning
hf_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

# Initialize vectorstore
vectorstore = PineconeVectorStore(
    index_name=PINECONE_INDEX_NAME,
    embedding=hf_embeddings,
    namespace=NAMESPACE
)

# Tracking lists for processed tickers
successful_tickers = []
unsuccessful_tickers = []

# Function to load tickers from a file
def load_tickers(file_path):
    try:
        with open(file_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# Load existing successful/unsuccessful tickers
successful_tickers = load_tickers('successful_tickers.txt')
unsuccessful_tickers = load_tickers('unsuccessful_tickers.txt')

# Function to fetch stock information
def get_stock_info(symbol: str) -> dict:
    data = yf.Ticker(symbol)
    stock_info = data.info
    properties = {
        "Ticker": stock_info.get('symbol', 'Information not available'),
        "Name": stock_info.get('longName', 'Information not available'),
        "Business Summary": stock_info.get('longBusinessSummary') or "No data available",
        "City": stock_info.get('city', 'Information not available'),
        "State": stock_info.get('state', 'Information not available'),
        "Country": stock_info.get('country', 'Information not available'),
        "Industry": stock_info.get('industry', 'Information not available'),
        "Sector": stock_info.get('sector', 'Information not available')
    }
    return properties

# Function to process and index a single stock
def process_stock(stock_ticker: str) -> str:
    if stock_ticker in successful_tickers:
        return f"Already processed {stock_ticker}"
    try:
        stock_data = get_stock_info(stock_ticker)
        stock_description = stock_data['Business Summary']
        if not isinstance(stock_description, str):
            stock_description = "No summary available"

        # Ensure all metadata values are valid
        for key, value in stock_data.items():
            if value is None:
                stock_data[key] = "No data available"
            elif isinstance(value, list):
                stock_data[key] = [str(item) for item in value]
            elif not isinstance(value, (str, int, float, bool)):
                stock_data[key] = str(value)

        # Create a Document
        doc = Document(page_content=stock_description, metadata=stock_data)
        vectorstore.add_documents([doc])

        # Record success
        with open('successful_tickers.txt', 'a') as f:
            f.write(f"{stock_ticker}\n")
        successful_tickers.append(stock_ticker)

        return f"Processed {stock_ticker} successfully"

    except Exception as e:
        # Record failure
        with open('unsuccessful_tickers.txt', 'a') as f:
            f.write(f"{stock_ticker}\n")
        unsuccessful_tickers.append(stock_ticker)
        return f"ERROR processing {stock_ticker}: {e}"

# Function to process stocks in parallel
def parallel_process_stocks(tickers: list, max_workers: int = 10) -> None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(process_stock, ticker): ticker
            for ticker in tickers
        }

        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result()
                print(result)
                if result.startswith("ERROR"):
                    print(f"Stopping program due to error in {ticker}")
                    executor.shutdown(wait=False)
                    raise SystemExit(1)
            except Exception as exc:
                print(f'{ticker} generated an exception: {exc}')
                print("Stopping program due to exception")
                executor.shutdown(wait=False)
                raise SystemExit(1)

# Function to fetch company tickers from GitHub
def get_company_tickers():
    url = "https://raw.githubusercontent.com/team-headstart/Financial-Analysis-and-Automation-with-LLMs/main/company_tickers.json"
    response = requests.get(url)
    if response.status_code == 200:
        company_tickers = json.loads(response.content.decode('utf-8'))
        with open("company_tickers.json", "w", encoding="utf-8") as file:
            json.dump(company_tickers, file, indent=4)
        print("File downloaded successfully and saved as 'company_tickers.json'")
        return company_tickers
    else:
        print(f"Failed to download file. Status code: {response.status_code}")
        return None

# Main execution block
if __name__ == "__main__":
    company_tickers = get_company_tickers()
    if company_tickers:
        print(f"Number of tickers to process: {len(company_tickers)}")
        tickers_to_process = [stock['ticker'] for stock in company_tickers.values()]
        parallel_process_stocks(tickers_to_process, max_workers=10)
