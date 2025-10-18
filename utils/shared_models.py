import os
import chromadb
import torch
from sentence_transformers import SentenceTransformer
from langchain.chat_models.base import init_chat_model
from transformers import VitsModel, AutoTokenizer
import whisper
from sources.config import settings

from transformers import BarkModel, AutoProcessor
from langchain_ollama.llms import OllamaLLM
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["HF_TOKEN"] = settings.HF_TOKEN

# <--- CHROMA DB AND EMBEDDINGS  --->
CHROMA_DB_PATH = "./chroma_db"
CHROMA_COLLECTION_NAME = "documents"

embedding_model = SentenceTransformer("BAAI/bge-m3")
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
chroma_collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

# <--- LLM CONFIG --->
#llm = Llama(model_path=LLM_MODEL_PATH, n_ctx=4096, verbose=False)
#llm = OllamaLLM(model="llama3.1", n_ctx=4096, verbose=False)
#llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

OPEN_ROUTER_KEY = settings.OPEN_ROUTER_KEY
llm = init_chat_model(
    model="openai/gpt-oss-20b:free",
    model_provider="openai",
    base_url="https://openrouter.ai/api/v1",
    api_key = OPEN_ROUTER_KEY,
    temperature=0.1,
    max_tokens=4096,
    model_kwargs={"top_p" : 0.95}
    )

# <--- STT CONFIG --->
transcription_model = whisper.load_model("small")

# <--- (Text-to-Speech) CONFIG --->
AUDIO_SAVE_DIRECTORY = "./audio_summaries"
os.makedirs(AUDIO_SAVE_DIRECTORY, exist_ok=True)
device = "cuda:0" if torch.cuda.is_available() else "cpu" 

tts_tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-eng")
tts_model = VitsModel.from_pretrained("facebook/mms-tts-eng")

# Bark model and processor once
#tts_processor = AutoProcessor.from_pretrained("suno/bark")
#tts_model = BarkModel.from_pretrained("suno/bark").to(device)

