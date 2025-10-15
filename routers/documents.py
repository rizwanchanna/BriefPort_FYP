import os
import shutil
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sources import schemas, database, oauth2, models, hashing
from utils.file_processor import process_document_ingestion
from utils.ai_services import generate_summary, audiolize_summary, generate_report, get_rag_response

router = APIRouter(prefix="/documents", tags=["Documents"])
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt" ".mp3", ".wav", ".mp4", ".m4a"}
INTERACTION_READY_STATUSES = {"ready_for_chat", "processing_ai", "complete"}
UPLOAD_DIRECTORY = "./uploads"

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not permitted. Allowed types are: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    filepath = os.path.join(UPLOAD_DIRECTORY, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_hash = hashing.calculate_file_hash(filepath)
    existing_doc = (
        db.query(models.Document)
        .filter(models.Document.owner_id == current_user.id)
        .filter(models.Document.content_hash == file_hash)
        .filter(models.Document.status == 'complete')
        .first()
    )
    
    if existing_doc:
        os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This file content has already been uploaded as '{existing_doc.filename}'.",
        )

    new_doc = models.Document(
        filename=file.filename, 
        owner_id=current_user.id, 
        file_type=file_extension,
        status="pending"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    
    background_tasks.add_task(process_document_ingestion, new_doc.id, filepath)
    
    return {"message": "File upload successful. Ingestion process has started.", "document_id": new_doc.id}

@router.get("/{doc_id}", response_model=schemas.DocumentDisplay, status_code=status.HTTP_202_ACCEPTED)
def get_document(doc_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == doc_id) #- Separate filter
        .filter(models.Document.owner_id == current_user.id) #- Separate filter
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.post("/{doc_id}/summarize", response_model=schemas.SummaryDisplay, status_code=status.HTTP_202_ACCEPTED)
def summarize_document(
    doc_id: int,
    request: schemas.SummaryRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == doc_id, models.Document.owner_id == current_user.id).first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if doc.status not in INTERACTION_READY_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Document is not ready for interaction yet. Current status: {doc.status}")

    summary = generate_summary(doc_id, request.summary_type.value)
    audio_summary_path = audiolize_summary(summary)
    
    summary_entry = models.Summary(
            content=summary,
            summary_type=request.summary_type.value,
            audio_path=audio_summary_path,
            user_id=doc.owner_id,
            document_id=doc.id
        )
    
    db.add(summary_entry)
    db.commit()
    db.refresh(summary_entry)

    return summary_entry

@router.post("/{doc_id}/report", response_model=schemas.ReportDisplay)
def create_document_report(
    doc_id: int,
    request: schemas.ReportRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == doc_id)
        .filter(models.Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if doc.status not in INTERACTION_READY_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Document is not ready for interaction yet. Current status: {doc.status}")

    report_content = generate_report(doc_id, request.report_type.value)
    new_report = models.Report(
        content=report_content,
        report_type=request.report_type.value,
        user_id=current_user.id,
        document_id=doc.id
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report

@router.post("/{doc_id}/chat", response_model=schemas.ChatResponse, status_code=status.HTTP_202_ACCEPTED)
def chat_with_document(
    doc_id: int,
    request: schemas.ChatRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == doc_id)
        .filter(models.Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if doc.status not in INTERACTION_READY_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Document is not ready for interaction yet. Current status: {doc.status}")

    answer = get_rag_response(doc_id, request.question)

    chat_history_entry = models.ChatHistory(
        question=request.question,
        answer=answer,
        user_id=current_user.id,
        document_id=doc.id
    )
    db.add(chat_history_entry)
    db.commit()

    return {"answer": answer}