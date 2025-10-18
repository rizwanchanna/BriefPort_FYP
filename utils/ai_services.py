import os
import uuid
import torch
from scipy.io.wavfile import write as write_wav
from utils.shared_models import (
    llm,
    tts_model,
    tts_tokenizer,
    embedding_model,
    chroma_collection,
    AUDIO_SAVE_DIRECTORY,
    device
)


def get_llm_response(prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return str(response.content)
    except Exception as e:
        return f"Error while generating response: {str(e)}"

def generate_summary(doc_id: int, summary_type: str) -> str:
    # Use embedding search to get most relevant chunks
    dummy_question = "What is the main topic and key points of this document?"
    question_embedding = embedding_model.encode(dummy_question).tolist()
    
    results = chroma_collection.query(
        query_embeddings=[question_embedding],
        n_results=10,  # get more chunks for summary
        where={"doc_id": doc_id}
    )
    
    cited_context = _build_cited_context(results)

    if not cited_context:
        return "Could not retrieve content for summary."

    summary_instruction = (
        "Provide a concise, one-paragraph summary of the following content."
        if summary_type == "short"
        else "Provide a detailed, multi-paragraph summary of the following content. Use headings and bullet points where appropriate to structure the information."
    )
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        You are a professional summarization assistant specializing in creating well-cited summaries that preserve document structure references.
        
        Guidelines:
        1. Create a clear and accurate summary based ONLY on the provided content
        2. For each paragraph in your summary, cite the specific sections or parts of the original document it summarizes
        3. Use detailed citations in this format: (Filename, doc_id=X, section: "Introduction") or (Filename, doc_id=X, part: "Technical Analysis")
        4. When summarizing multiple points from different parts, use multiple citations in the same paragraph
        5. Maintain a natural flow while making it clear which original sections each summary point comes from
        6. For longer summaries:
           - Group related information from the same document sections together
           - Use headings that reflect the original document structure
           - Include page/section references in citations when available
        
        Remember: Each paragraph should clearly show which parts of the original document it summarizes, helping readers locate the full information.<|eot_id|><|start_header_id|>user<|end_header_id|>
        {summary_instruction}
        
        Here is the content (each chunk is prefixed with its source):

        --- CONTENT START ---  
        {cited_context}
        --- CONTENT END ---<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    summary = get_llm_response(prompt)
    
    return summary

def generate_report(doc_id: int, report_type: str) -> str:
    # Use embedding search to get most relevant chunks
    dummy_question = "What are the main findings, analysis points, and conclusions in this document?"
    question_embedding = embedding_model.encode(dummy_question).tolist()
    
    results = chroma_collection.query(
        query_embeddings=[question_embedding],
        n_results=12,  # get more chunks for detailed report
        where={"doc_id": doc_id}
    )
    
    cited_context = _build_cited_context(results)

    if not cited_context:
        return "Could not retrieve content for report generation."

    if report_type == "formal":
        report_instruction = """
        Analyze the following content and structure it into a formal business report. The report must include the following sections:
        1.  **Executive Summary:** A brief, high-level overview of the document's main points.
        2.  **Key Findings:** A bulleted list of the most critical insights, data, and conclusions.
        3.  **Detailed Analysis:** An in-depth exploration of the key topics.
        4.  **Conclusion & Recommendations:** A summary of the analysis and actionable recommendations, if applicable.
        Maintain a professional, objective, and clear tone throughout.
        """
    elif report_type == "academic":
        report_instruction = """
        Analyze the following content and structure it into a formal academic report. The report must include the following sections:
        1.  **Abstract:** A concise summary of the document's purpose, methods, key findings, and conclusions.
        2.  **Introduction:** An overview of the topic and the document's main arguments.
        3.  **Discussion of Findings:** A detailed analysis and interpretation of the key points presented in the content.
        4.  **Conclusion:** A summary of the main arguments and their implications.
        Maintain a formal, scholarly tone and use precise language.
        """
    else:
        return "Invalid report type specified."

    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are an expert report writer specializing in creating detailed, well-cited analysis reports with precise section references.
    
    Guidelines:
    1. Create a structured report following the requested format
    2. For each section in your report, use detailed citations that specify which parts of the original document you're analyzing:
       - Use format: (Filename, doc_id=X, section: "Methods", topic: "Data Analysis")
       - Include multiple citations when combining information from different parts
       - Reference specific sections, pages, or topics in citations when available
    3. In the Executive Summary:
       - Cite the main sections that contributed to each key point
       - Use format: (Filename, doc_id=X, sections: ["Results", "Discussion"])
    4. In Key Findings:
       - Each finding should cite the specific parts of the document it's derived from
       - Include section/topic references to help readers locate the full details
    5. In Detailed Analysis:
       - Structure your analysis to follow the original document's organization
       - Cite specific subsections and topics being analyzed
       - When synthesizing across sections, use multiple detailed citations
    6. In Recommendations:
       - Link each recommendation to specific evidence in the document
       - Cite the exact sections that support each recommendation
    
    Remember: Help readers understand exactly which parts of the original document your analysis is based on.<|eot_id|><|start_header_id|>user<|end_header_id|>
    {report_instruction}

    Here is the source content (each chunk is prefixed with its source):
    --- CONTENT START ---
    {cited_context}
    --- CONTENT END ---<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    report = get_llm_response(prompt)
    return report


def audiolize_summary(text: str) -> str:
    inputs = tts_tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        output = tts_model(**inputs).waveform
    sampling_rate = tts_model.config.sampling_rate
    speech_waveform = output.squeeze().cpu().float().numpy()
    
    filename = f"summary_{uuid.uuid4()}.wav"
    filepath = os.path.join(AUDIO_SAVE_DIRECTORY, filename)
    
    write_wav(filepath, rate=sampling_rate, data=speech_waveform)
    
    return filepath


def _build_cited_context(results: dict) -> str:
    """Given chroma query results, build a context string where each chunk is
    prefixed with a SOURCE label (filename and doc_id) to allow the LLM to cite sources.
    Expects results to have 'documents' and 'metadatas' aligned.
    """
    documents = results.get('documents', [])
    metadatas = results.get('metadatas', [])
    parts = []
    # results may be nested depending on the client; handle common shapes
    if len(documents) == 0:
        return ""

    # If documents is like [[doc1_chunk, doc2_chunk], ...] or a flat list
    # Normalize to a flat list of tuples (doc_text, metadata)
    flat_docs = []
    if isinstance(documents[0], list):
        # assume documents and metadatas are lists of lists
        for doc_list, meta_list in zip(documents, metadatas):
            for d, m in zip(doc_list, meta_list):
                flat_docs.append((d, m))
    else:
        for d, m in zip(documents, metadatas):
            flat_docs.append((d, m))

    for idx, (doc_text, meta) in enumerate(flat_docs):
        filename = meta.get('filename') if isinstance(meta, dict) else None
        doc_id = meta.get('doc_id') if isinstance(meta, dict) else None
        source_label = f"SOURCE: {filename or 'unknown'} (doc_id={doc_id})"
        parts.append(f"{source_label}\n{doc_text}")

    return "\n\n".join(parts)


def get_rag_response(question: str, owner_id: int = None, doc_id: int = None, n_results: int = 8) -> str:
    """Retrieve relevant chunks from Chroma filtered by owner_id (for multi-doc) or by doc_id (single doc).
    Builds a cited context and asks the LLM to answer using only that context. Returns the LLM answer.

    Args:
        question: the user's question
        owner_id: if provided, query across all documents owned by this user
        doc_id: if provided, restrict to a single document (keeps backward compatibility)
        n_results: how many chunks to retrieve
    """
    question_embedding = embedding_model.encode(question).tolist()

    where_filter = {}
    if doc_id is not None:
        where_filter['doc_id'] = doc_id
    elif owner_id is not None:
        where_filter['owner_id'] = owner_id
    # else: no filter -> global (probably not desired)

    context_chunks = chroma_collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
        where=where_filter if where_filter else None
    )
    
    # Debug logging
    print(f"RAG Query - Filters: {where_filter}")
    print(f"Retrieved {len(context_chunks.get('documents', [[]])[0])} chunks")

    cited_context = _build_cited_context(context_chunks)
    
    if cited_context:
        # Log first chunk to debug content quality
        first_chunk = cited_context.split("\n\n")[0] if "\n\n" in cited_context else cited_context
        print(f"First context chunk (preview): {first_chunk[:200]}...")

    if not cited_context:
        return "I couldn't find any relevant content in your documents to answer that."

    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        You are a helpful Q&A assistant specialized in providing detailed, accurate answers from document collections. 
        
        Guidelines:
        1. Use ONLY the provided context chunks to answer the question
        2. ALWAYS cite sources using (Filename, doc_id=X) format when stating facts
        3. If different documents have conflicting information, point this out
        4. If the answer requires information not in the context, say so clearly
        5. Structure longer answers with clear paragraphs or bullet points
        6. Focus on direct, factual information from the documents
        
        Remember: Every fact you state must have a citation to show which document it came from.<|eot_id|><|start_header_id|>user<|end_header_id|>
        Here are the context chunks (each prefixed with its SOURCE label):

        --- CONTEXT START ---
        {cited_context}
        --- CONTEXT END ---

        Based on these context chunks, please provide a detailed answer to the following question, making sure to cite your sources:

        Question: {question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    answer = get_llm_response(prompt)
    return answer
