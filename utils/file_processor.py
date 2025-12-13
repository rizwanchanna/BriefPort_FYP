from sources.database import SessionLocal
from sources import models
from unstructured.partition.auto import partition
from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils.shared_models import embedding_model ,chroma_collection, transcription_model
from utils.ai_services import generate_summary, generate_report, audiolize_summary, transcribe_video
import os

def process_document_ingestion(doc_id: int, filepath: str, file_hash: str):

    db = SessionLocal()
    try:
        doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
        if not doc:
            return

        # --- STAGE 1: FAST PROCESSING (Extraction & Embedding) ---
        doc.status = "extracting"
        db.commit()
        
        extracted_content = ""
        file_extension = os.path.splitext(filepath)[1].lower()
        
        if file_extension in [".pdf", ".docx", ".txt"]:
            elements = partition(filename=filepath)
            extracted_content = "\n\n".join([str(el) for el in elements])
        
        elif file_extension in [".mp4", ".mov", ".avi"]:
            extracted_content = transcribe_video(filepath)

        elif file_extension in [".mp3", ".wav", ".m4a"]:
            result = transcription_model.transcribe(filepath, fp16=False)
            extracted_content = result["text"]
        
        doc.content = extracted_content
        db.commit()


        doc.status = "embedding"
        db.commit()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=20000,
            chunk_overlap=1000
        )
        chunks = text_splitter.split_text(extracted_content)
        embeddings = embedding_model.encode(chunks).tolist()
        chunk_ids = [f"doc{doc_id}_chunk{i}" for i in range(len(chunks))]
        # include owner_id and filename in metadata so we can run owner-level (multi-doc) queries
        chroma_collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"doc_id": doc_id, "owner_id": doc.owner_id, "filename": doc.filename} for _ in chunks]
        )

        doc.status = "ready_for_chat"
        db.commit()

        # --- STAGE 2: SLOW PROCESSING (AI Generation) ---
        doc.status = "processing_ai"
        db.commit()
        
        summary_text = generate_summary(doc_id, "short")
        audio_path = audiolize_summary(summary_text)
        summary_entry = models.Summary(
            content=summary_text,
            summary_type="short",
            audio_path=audio_path,
            user_id=doc.owner_id,
            document_id=doc.id
        )
        db.add(summary_entry)

        report_text = generate_report(doc_id, "formal")
        report_entry = models.Report(
            content=report_text,
            report_type="formal",
            user_id=doc.owner_id,
            document_id=doc.id
        )
        db.add(report_entry)
        doc.content_hash = file_hash
        doc.status = "complete"
        db.commit()

    except Exception as e:
        print(f"Error processing document {doc_id}: {e}")
        if 'doc' in locals():
            doc.status = "failed"
            db.commit()
    finally:
        db.close()
