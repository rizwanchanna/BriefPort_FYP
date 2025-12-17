import os
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

from sources.database import SessionLocal
from sources import models
from utils.shared_models import llm, embedding_model, chroma_collection, transcription_model
from utils.ai_services import generate_summary, generate_report, audiolize_summary, transcribe_video
from sources.hashing import calculate_file_hash
from unstructured.partition.auto import partition
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- 1. Define the State ---
class AgentState(TypedDict):
    doc_id: int
    filepath: str
    file_hash: str
    owner_id: int
    extracted_content: str
    content_type: Literal["academic", "business", "legal_policy", "generic"]

# --- 2. Define the Nodes (The "Agents") ---
def node_extract_and_embed(state: AgentState) -> dict:
    """
    Node 1: (Phase 1) Extracts content, embeds it,
    and sets the document to 'ready_for_chat'.
    """
    print(f"--- Agent [1/4]: Extracting & Embedding Doc ID: {state['doc_id']} ---")
    db = SessionLocal()
    try:
        doc = db.query(models.Document).filter(models.Document.id == state['doc_id']).first()
        doc.status = "extracting"
        db.commit()
        # Extract Content
        filepath = state['filepath']
        file_extension = os.path.splitext(filepath)[1].lower()
        extracted_content = ""
        
        if file_extension in [".pdf", ".docx", ".txt"]:
            elements = partition(filename=filepath)
            extracted_content = "\n\n".join([str(el) for el in elements])
        elif file_extension in [".mp4", ".mov", ".avi"]:
            extracted_content = transcribe_video(filepath)
        elif file_extension in [".mp3", ".wav", ".m4a"]:
            result = transcription_model.transcribe(filepath, fp16=False)
            extracted_content = result["text"]
        
        # Embed Content
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=20000, chunk_overlap=1000)
        chunks = text_splitter.split_text(extracted_content)
        embeddings = embedding_model.encode(chunks).tolist()
        chunk_ids = [f"doc{state['doc_id']}_chunk{i}" for i in range(len(chunks))]
        metadatas = [{"doc_id": state['doc_id'], "owner_id": state['owner_id'], "filename": state['filepath']} for _ in chunks]
        chroma_collection.add(
            ids=chunk_ids, 
            embeddings=embeddings, 
            documents=chunks, 
            metadatas=metadatas
        )
        
        doc.content = extracted_content
        doc.status = "ready_for_chat"
        db.commit()
        
        return {"extracted_content": extracted_content}
    except Exception as e:
        print(f"Error in node_extract_and_embed: {e}")
        raise
    finally:
        db.close()

def node_classify_content(state: AgentState) -> dict:
    """
    Node 2 (The Dispatcher): Analyzes the content to decide what it is.
    """
    print(f"--- Agent [2/4]: Classifying Doc ID: {state['doc_id']} ---")
    content_preview = state['extracted_content'][:2000] # Use a preview
    
    prompt = f"""You are a document classification expert. Analyze the following text preview and classify its primary purpose.
    Your answer MUST be a single word from this list: [academic, business, legal_policy, generic].
    
    - 'academic': For research papers, dissertations, lectures, scholarly articles.
    - 'business': For business reports, meeting notes, strategy documents, corporate memos.
    - 'legal_policy': For insurance policies, legal contracts, claims, risk assessments, regulatory files.
    - 'generic': For all other document types (articles, books, etc.).
    
    Text Preview:
    ---
    {content_preview}
    ---
    Classification:"""
    
    response = llm.invoke(prompt)
    classification = str(response.content).strip().lower()
    
    if classification not in ['academic', 'business', 'legal_policy', 'generic']:
        classification = 'generic'
        
    print(f"--- Agent: Classified as: {classification} ---")
    return {"content_type": classification}

def node_academic_agent(state: AgentState):
    """
    Node 3a (Academic Agent): Generates a concise summary and an academic report.
    """
    print(f"--- Agent [3/4]: Running Academic Agent for Doc ID: {state['doc_id']} ---")
    db = SessionLocal()
    try:
        summary_text = generate_summary(state['doc_id'], "short")
        summary_audio = audiolize_summary(summary_text)
        db.add(models.Summary(
            content=summary_text, 
            audio_path=summary_audio,
            summary_type="short", 
            user_id=state['owner_id'], 
            document_id=state['doc_id']
        ))
        report_text = generate_report(state['doc_id'], "academic")
        db.add(models.Report(
            content=report_text, 
            report_type="academic", 
            user_id=state['owner_id'], 
            document_id=state['doc_id']
        ))
        db.commit()
    finally:
        db.close()
    return {}

def node_business_agent(state: AgentState):
    """
    Node 3b (Business Agent): Generates an executive summary and a BI report.
    """
    print(f"--- Agent [3/4]: Running Business Agent for Doc ID: {state['doc_id']} ---")
    db = SessionLocal()
    try:
        summary_text = generate_summary(state['doc_id'], "short")
        summary_audio = audiolize_summary(summary_text)
        db.add(models.Summary(
            content=summary_text, audio_path=summary_audio, summary_type="short", user_id=state['owner_id'], document_id=state['doc_id']
        ))
        report_text = generate_report(state['doc_id'], "business_insights")
        db.add(models.Report(
            content=report_text, report_type="business_insights", user_id=state['owner_id'], document_id=state['doc_id']
        ))
        db.commit()
    finally:
        db.close()
    return {}

def node_legal_policy_agent(state: AgentState):
    """
    Node 3c (Legal/Policy Agent): Generates a compliance summary and a risk report.
    """
    print(f"--- Agent [3/4]: Running Legal/Policy Agent for Doc ID: {state['doc_id']} ---")
    db = SessionLocal()
    try:
        summary_text = generate_summary(state['doc_id'], "short") # "short" is good for key terms
        summary_audio = audiolize_summary(summary_text)
        db.add(models.Summary(
            content=summary_text, audio_path=summary_audio, summary_type="short", user_id=state['owner_id'], document_id=state['doc_id']
        ))
        report_text = generate_report(state['doc_id'], "risk_analysis")
        db.add(models.Report(
            content=report_text, report_type="risk_analysis", user_id=state['owner_id'], document_id=state['doc_id']
        ))
        db.commit()
    finally:
        db.close()
    return {}

def node_generic_agent(state: AgentState):
    """
    Node 3d (Generic Agent): Default action. We'll just create a simple summary.
    """
    print(f"--- Agent [3/4]: Running Generic Agent for Doc ID: {state['doc_id']} ---")
    db = SessionLocal()
    try:
        summary_text = generate_summary(state['doc_id'], "short")
        summary_audio = audiolize_summary(summary_text)
        db.add(models.Summary(
            content=summary_text, audio_path=summary_audio, summary_type="short", user_id=state['owner_id'], document_id=state['doc_id']
        ))
        db.commit()
    finally:
        db.close()
    return {}

def node_set_status_complete(state: AgentState):
    """
    Final Node: Updates the document status to 'complete' and saves the hash.
    """
    print(f"--- Agent [4/4]: Finalizing Doc ID: {state['doc_id']} ---")
    db = SessionLocal()
    try:
        doc = db.query(models.Document).filter(models.Document.id == state['doc_id']).first()
        doc.status = "complete"
        doc.content_hash = calculate_file_hash(state['filepath'])
        db.commit()
    finally:
        db.close()
    return {}

def router_classify_content(state: AgentState) -> Literal["academic", "business", "legal_policy", "generic"]:
    """This is the conditional edge function."""
    return state['content_type']

workflow = StateGraph(AgentState)

workflow.add_node("extract_and_embed", node_extract_and_embed)
workflow.add_node("classify_content", node_classify_content)
workflow.add_node("academic_agent", node_academic_agent)
workflow.add_node("business_agent", node_business_agent)
workflow.add_node("legal_policy_agent", node_legal_policy_agent)
workflow.add_node("generic_agent", node_generic_agent)
workflow.add_node("set_status_complete", node_set_status_complete)

workflow.set_entry_point("extract_and_embed")
workflow.add_edge("extract_and_embed", "classify_content")

workflow.add_conditional_edges(
    "classify_content",
    router_classify_content,
    {
        "academic": "academic_agent",
        "business": "business_agent",
        "legal_policy": "legal_policy_agent",
        "generic": "generic_agent"
    }
)

workflow.add_edge("academic_agent", "set_status_complete")
workflow.add_edge("business_agent", "set_status_complete")
workflow.add_edge("legal_policy_agent", "set_status_complete")
workflow.add_edge("generic_agent", "set_status_complete")

workflow.add_edge("set_status_complete", END)

agentic_workflow = workflow.compile()