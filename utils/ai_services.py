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

    results = chroma_collection.get(where={"doc_id": doc_id})
    full_text = "\n\n".join(results['documents'])

    if not full_text:
        return "Could not retrieve content for summary."

    summary_instruction = (
        "Provide a concise, one-paragraph summary of the following content."
        if summary_type == "short"
        else "Provide a detailed, multi-paragraph summary of the following content. Use headings and bullet points where appropriate to structure the information."
    )
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        You are a professional summarization assistant. Your goal is to provide clear and accurate summaries with citations based *only* on the provided text. Cite information by referring to the content's key topics.<|eot_id|><|start_header_id|>user<|end_header_id|>
        {summary_instruction} Here is the content:

        --- CONTENT START ---  
        {full_text}
        --- CONTENT END ---<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    summary = get_llm_response(prompt)
    
    return summary

def generate_report(doc_id: int, report_type: str) -> str:

    results = chroma_collection.get(where={"doc_id": doc_id})
    full_text = "\n\n".join(results['documents'])

    if not full_text:
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
    You are an expert report writer. Your task is to generate a structured, comprehensive report based *only* on the provided text, following the user's specific formatting instructions.<|eot_id|><|start_header_id|>user<|end_header_id|>
    {report_instruction}

    Here is the source content:
    --- CONTENT START ---
    {full_text}
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


def get_rag_response(doc_id: int, question: str) -> str:
    question_embedding = embedding_model.encode(question).tolist()

    context_chunks = chroma_collection.query(
        query_embeddings=[question_embedding],
        n_results=5,
        where={"doc_id": doc_id}
    )
    context = "\n\n".join(context_chunks['documents'][0])
    
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        You are a helpful Q&A assistant. Your task is to answer the user's question based *exclusively* on the provided context. If the answer is not available in the context, clearly state that. Do not make up information.<|eot_id|><|start_header_id|>user<|end_header_id|>
        Here is the context:

        --- CONTEXT START ---
        {context}
        --- CONTEXT END ---

        Based on this context, please answer the following question:
        Question: {question}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    answer = get_llm_response(prompt)
    return answer
