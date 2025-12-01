import os
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sources import models
from utils.shared_models import chroma_collection

UPLOAD_DIRECTORY = "./uploads"

def delete_document(doc_id: int, current_user_id: int, db: Session):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id, 
        models.Document.owner_id == current_user_id
    ).first()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = os.path.join(UPLOAD_DIRECTORY, doc.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")

    for summary in doc.summaries:
        if summary.audio_path and os.path.exists(summary.audio_path):
            try:
                os.remove(summary.audio_path)
            except OSError as e:
                print(f"Error deleting audio file {summary.audio_path}: {e}")

    try:
        chroma_collection.delete(where={"doc_id": doc_id})
    except Exception as e:
        print(f"Error deleting from ChromaDB: {e}")

    db.delete(doc)
    db.commit()

    return {"detail": "Document and all associated data deleted successfully."}

def delete_summary(summary_id: int, current_user_id: int, db: Session):
    summary = db.query(models.Summary).join(models.Document).filter(
        models.Summary.id == summary_id,
        models.Document.owner_id == current_user_id
    ).first()

    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Summary not found or access denied.")

    if summary.audio_path and os.path.exists(summary.audio_path):
        try:
            os.remove(summary.audio_path)
        except OSError as e:
            print(f"Error deleting audio file {summary.audio_path}: {e}")

    db.delete(summary)
    db.commit()

    return {"detail": "Summary and audio deleted successfully."}

def delete_report(report_id: int, current_user_id: int, db: Session):
    report = db.query(models.Report).join(models.Document).filter(
        models.Report.id == report_id,
        models.Document.owner_id == current_user_id
    ).first()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or access denied.")

    db.delete(report)
    db.commit()

    return {"detail": "Report deleted successfully."}

def get_summary_by_id(summary_id: int, current_user_id: int, db: Session):
    return db.query(models.Summary).join(models.Document).filter(
        models.Summary.id == summary_id,
        models.Document.owner_id == current_user_id
    ).first()

def get_report_by_id(report_id: int, current_user_id: int, db: Session):
    return db.query(models.Report).join(models.Document).filter(
        models.Report.id == report_id,
        models.Document.owner_id == current_user_id
    ).first()