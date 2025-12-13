import os, subprocess
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
    transcription_model,
    device
)


def get_llm_response(prompt: str) -> str:
    try:
        response = llm.invoke(prompt)
        return str(response.content)
    except Exception as e:
        return f"Error while generating response: {str(e)}"

def generate_summary(doc_id: int, summary_type: str) -> str:
    dummy_question = "What is the main topic and key points of this document?"
    question_embedding = embedding_model.encode(dummy_question).tolist()
    
    results = chroma_collection.query(
        query_embeddings=[question_embedding],
        n_results=10,
        where={"doc_id": doc_id}
    )
    
    cited_context = _build_cited_context(results)

    if not cited_context:
        return "Could not retrieve content for summary."

    summary_instruction = (
        "Write a concise, one-paragraph summary of the provided content. "
        "Include numbered citations like [1], [2], etc., that map directly to the 'reference list'."
        if summary_type == "short"
        else "Write a detailed, multi-paragraph summary of the provided content. "
            "Use headings when appropriate and include numbered citations like [1], [2], etc., "
            "that map directly to the reference list."
    )
    
    prompt = f"""
        <|begin_of_text|><|start_header_id|>system<|end_header_id|>
        You are a professional summarization assistant.  
        Your task is to generate structured summaries with **numbered citations** matching the source content.

        ### Summary Rules
        1. Base your summary ONLY on the provided content.
        2. Every major claim or sentence must include at least one citation using bracket format:  
        **[1]**, **[2]**, **[3]**, etc.
        3. Citations must correspond to the source chunks provided in the input.
        4. After writing the summary, include a **References** section list where each number maps to:
        - The filename  
        - Section or part name (if provided in the chunk)  
        Example:  
        `[1] (FYP.pdf, Section: "Problem Statement")`
        `[2] (FYP.pdf, Section: "Market Growth")`
        5. Maintain a clean and natural writing style while preserving traceability.
        6. For multi-paragraph summaries:
        - Group related information together
        - Use headings reflecting the document structure
        - Still use numeric citations for each claim

        ### Output Format (STRICT)
        Your output must follow **this exact structure**:
        
        **Summary:**
        SUMMARY TEXT WITH [1], [2], [3]...

        **References:**
        [1] (filename, section/part: "...")
        [2] (...)
        [3] (...)

        ### Formatting Rules (STRICT)
        - Each reference **must appear on its own line**.
        - Do NOT merge references into a single paragraph.
        - References must not be inline or comma-separated.
        - No text is allowed after the References section.

        <|eot_id|><|start_header_id|>user<|end_header_id|>

        {summary_instruction}

        Here is the content. Each chunk includes source metadata:

        --- CONTENT START ---
        {cited_context}
        --- CONTENT END ---

        <|eot_id|><|start_header_id|>assistant<|end_header_id|>
        """

    summary = get_llm_response(prompt)
    
    return summary

def generate_report(doc_id: int, report_type: str) -> str:
    dummy_question = "What are the main findings, analysis points, and conclusions in this document?"
    question_embedding = embedding_model.encode(dummy_question).tolist()
    
    results = chroma_collection.query(
        query_embeddings=[question_embedding],
        n_results=12, 
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
    elif report_type == "business_insights":
        report_instruction = """
        Analyze the following business document and generate a Business Intelligence report. Focus on:
        1. Key Performance Indicators (KPIs) mentioned or implied.
        2. Strategic Opportunities or Threats.
        3. Actionable Recommendations for management.
        """
    elif report_type == "risk_analysis":
        report_instruction = """
        Analyze the following policy, claim, or risk document and generate a structured Risk Analysis Brief. Extract:
        1. Key Terms and Definitions.
        2. A list of specific Exclusions or Limitations.
        3. Underwriting Insights or potential Claim Triggers.
        4. A final assessment of the overall risk level.
        """
    else:
        report_instruction = f"Generate a general report based on the following text."

    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
    You are an expert report writer specializing in creating structured, well-cited analysis reports with precise references.  
    Your task is to generate a clean, organized report using numbered citations that correspond to a References section.

    ### Citation Rules
    1. Every major statement, claim, insight, or conclusion must include at least one numbered citation: [1], [2], [3], etc.
    2. Citations must reference the source chunks included in the input.
    3. For each citation number, include a corresponding entry in the References section with:
    - Filename
    - Section/subsection/topic/page (when provided)

    Example Reference Entries:
    `[1] (FYP.pdf, section: "Methods", topic: "Data Analysis")`

    ### Section-Specific Requirements
    **Executive Summary**
    - Provide a high-level overview.
    - Each key point must include citations like [1], [2].
    - When multiple sections contributed to the point, use multiple citations: [1][3].

    **Key Findings**
    - Present findings as clear bullet points or short paragraphs.
    - Each finding must cite exact source sections or topics.

    **Detailed Analysis**
    - Organize the analysis to follow the structure of the original document.
    - Cite specific subsections and topics for every analytical point.
    - When synthesizing across documents or across sections, use multiple citations: [2][4][5].

    **Recommendations**
    - Each recommendation must link to the evidence that supports it.
    - Use citations pointing to the relevant findings or data sources.

    ### Output Format (STRICT)
    Your final output must follow **exactly** this structure:

    Executive Summary  
    (Paragraphs with citations like [1], [2], [3]...)
    
    Key Findings  
    - Finding 1 [1]  
    - Finding 2 [2][3]  
    - Finding 3 [4]

    Detailed Analysis  
    (Structured sections with citations)

    Recommendations  
    (Recommendations with citations)

    References:
    [1] (filename, section: "...", topic: "...")
    [2] (filename, section: "...", topic: "...")
    [3] (filename, section: "...", topic: "...")

    ### Reference Formatting Rules (STRICT)
    - Each reference MUST appear on its own newline.
    - References must NOT be inline, comma-separated, or merged.
    - No text should appear after the References section.
    - The number of reference entries must match all citation numbers used in the report.

    <|eot_id|><|start_header_id|>user<|end_header_id|>
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
    question_embedding = embedding_model.encode(question).tolist()

    where_filter = {}
    if doc_id is not None:
        where_filter['doc_id'] = doc_id
    elif owner_id is not None:
        where_filter['owner_id'] = owner_id

    context_chunks = chroma_collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
        where=where_filter if where_filter else None
    )
    # DEBUGING
    print(f"RAG Query - Filters: {where_filter}")
    print(f"Retrieved {len(context_chunks.get('documents', [[]])[0])} chunks")

    cited_context = _build_cited_context(context_chunks)
    
    if cited_context:
        # TO CHECK CONTENT QUALITY 1st LOG
        first_chunk = cited_context.split("\n\n")[0] if "\n\n" in cited_context else cited_context
        print(f"First context chunk (preview): {first_chunk[:200]}...")

    if not cited_context:
        return "I couldn't find any relevant content in your documents to answer that."

    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
        You are a reliable document-grounded Q&A assistant.  
        Your role is to answer questions using ONLY the provided context chunks and to cite every factual statement with numbered citations.

        ### Rules for Answering
        1. Use ONLY the provided context chunks—never add outside knowledge.
        2. Every factual statement must include at least one numbered citation: [1], [2], [3], etc.
        3. When multiple documents support a statement, use multiple citations: [1][3][5].
        4. If the documents contain contradictory information, clearly state this with citations.
        5. If the answer cannot be fully answered from the context, say so explicitly.
        6. Structure long answers using paragraphs or bullet points.
        7. All citations must correspond to entries in a **References** section at the end.

        ### Output Format (STRICT)
        Your response must follow this exact format:

        Answer:
        (Paragraphs or bullet points with citations like [1], [2][4], [3]...)

        References:
        [1] (filename, section: "..." if provided)
        [2] (filename, section: "...")
        [3] (...)

        ### Reference Formatting Rules (STRICT)
        - Each reference MUST appear on its own line.
        - Do NOT merge all references into a single sentence.
        - The References list must include ALL citation numbers used.
        - No content is allowed after the References section.

        <|eot_id|><|start_header_id|>user<|end_header_id|>

        Here are the context chunks (each prefixed with its SOURCE label):

        --- CONTEXT START ---
        {cited_context}
        --- CONTEXT END ---

        Question: {question}

        Please provide a detailed, citation-supported answer following the required structure.
        <|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    answer = get_llm_response(prompt)
    return answer

def transcribe_video(video_path: str) -> str:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    audio_output_path = os.path.splitext(video_path)[0] + ".wav"
    
    command = [
        "ffmpeg",
        "-i", video_path,       # Input video file
        "-vn",                  # No video output
        "-acodec", "pcm_s16le", # Audio codec: WAV format
        "-ar", "16000",         # Audio sample rate: 16kHz
        "-ac", "1",             # Audio channels: 1 (mono)
        audio_output_path
    ]

    try:
        print("Extracting audio from video...")
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Audio extracted successfully to: {audio_output_path}")

        print("Loading transcription model...")
        print("Transcribing audio...")
        result = transcription_model.transcribe(audio_output_path, fp16=False)
        transcript = result["text"]
        print("Transcription complete.")
        
        return transcript

    except subprocess.CalledProcessError as e:
        print("Error during FFmpeg audio extraction:")
        print(e.stderr.decode())
        raise
    finally:
        if os.path.exists(audio_output_path):
            os.remove(audio_output_path)
            print(f"Cleaned up temporary audio file: {audio_output_path}")