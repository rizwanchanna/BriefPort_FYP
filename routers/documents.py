import os
import shutil
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sources import schemas, database, oauth2, models, hashing
from repo import documents
from fastapi.responses import StreamingResponse
import io
from utils.pdf_utils import generate_pdf_bytes
from utils.file_processor import process_document_ingestion
from utils.ai_services import generate_summary, audiolize_summary, generate_report, get_rag_response

router = APIRouter(prefix="/documents", tags=["Documents"])
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".mp3", ".wav", ".mp4", ".m4a"}
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
    
    background_tasks.add_task(process_document_ingestion, new_doc.id, filepath, file_hash)
    
    return {"message": "File upload successful. Ingestion process has started.", "document_id": new_doc.id}

@router.delete("/delete_document/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(
    doc_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    return documents.delete_document(doc_id, current_user.id, db)

@router.get("", response_model=list[schemas.DocumentDisplay])
def get_user_documents(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    documents = (
        db.query(models.Document)
        .filter(models.Document.owner_id == current_user.id)
        .order_by(models.Document.id)
        .all()
    )
    return documents

@router.post("/library/chat", response_model=schemas.ChatResponse, status_code=status.HTTP_202_ACCEPTED)
def chat_with_library(
    request: schemas.ChatRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    """Chat across all documents owned by the current user. Returns an answer with inline citations to filenames/doc_ids."""

    answer = get_rag_response(request.question, owner_id=current_user.id)

    chat_history_entry = models.ChatHistory(
        question=request.question,
        answer=answer,
        user_id=current_user.id,
        document_id=None
    )
    db.add(chat_history_entry)
    db.commit()

    return {"answer": answer}

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

    answer = get_rag_response(request.question, doc_id=doc.id)

    chat_history_entry = models.ChatHistory(
        question=request.question,
        answer=answer,
        user_id=current_user.id,
        document_id=doc.id
    )
    db.add(chat_history_entry)
    db.commit()

    return {"answer": answer}

@router.get("/{doc_id}", response_model=schemas.DocumentDisplay, status_code=status.HTTP_202_ACCEPTED)
def get_document(doc_id: int, db: Session = Depends(database.get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == doc_id) 
        .filter(models.Document.owner_id == current_user.id) 
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

@router.delete("/delete_summary/{doc_id}", status_code=status.HTTP_200_OK)
def delete_summary(
    summary_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    return documents.delete_summary(summary_id, current_user.id, db)

@router.get("/summary/{summary_id}/download", status_code=status.HTTP_200_OK)
def download_summary_pdf(
    summary_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    summary = documents.get_summary_by_id(summary_id, current_user.id, db)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found")

    title = f"Your\nSummarized Document"
    
    # Pass the summary_type ("detailed", "short") as the doc_type for styling
    pdf_bytes = generate_pdf_bytes(title, summary.content, doc_type=summary.summary_type)
    
    filename = f"Summary_{summary_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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

@router.delete("/delete_report/{report_id}", status_code=status.HTTP_200_OK)
def delete_report(
    report_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    return documents.delete_report(report_id, current_user.id, db)

@router.get("/report/{report_id}/download", status_code=status.HTTP_200_OK)
def download_report_pdf(
    report_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    report = documents.get_report_by_id(report_id, current_user.id, db)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    clean_type = report.report_type.replace('_', ' ').title()
    title = f"{clean_type} Report\nfor Your Document"
    
    pdf_bytes = generate_pdf_bytes(title, report.content, doc_type=report.report_type)
    
    filename = f"Report_{report_id}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    from fastapi.responses import FileResponse
    
    doc = (
        db.query(models.Document)
        .filter(models.Document.id == doc_id)
        .filter(models.Document.owner_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    
    filepath = os.path.join(UPLOAD_DIRECTORY, doc.filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found on server.")
    
    return FileResponse(
        path=filepath,
        media_type='application/octet-stream',
        filename=doc.filename
    )
