from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sources.database import Base
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_verified = Column(Boolean, default=False)

    documents = relationship("Document", back_populates="owner")
    summaries = relationship("Summary", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    chat_histories = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "document"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_type = Column(String, nullable=True)
    status = Column(String, default="pending") # pending -> extracting -> embedding -> ready_for_chat -> processing_ai -> complete / failed
    content = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True) 
    owner_id = Column(Integer, ForeignKey("user.id"))
    
    owner = relationship("User", back_populates="documents")
    summaries = relationship("Summary", back_populates="document", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="document", cascade="all, delete-orphan")
    chat_histories = relationship("ChatHistory", back_populates="document", cascade="all, delete-orphan")

class Summary(Base):
    __tablename__ = "summary"

    id = Column(Integer, primary_key=True, index=True)
    summary_type = Column(String, nullable=False, default="detailed")
    content = Column(Text, nullable=False)
    audio_path = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    document_id = Column(Integer, ForeignKey("document.id"))

    user = relationship("User", back_populates="summaries")
    document = relationship("Document", back_populates="summaries")


class Report(Base):
    __tablename__ = "report"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    report_type = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))
    document_id = Column(Integer, ForeignKey("document.id"))

    user = relationship("User", back_populates="reports")
    document = relationship("Document", back_populates="reports")

class ChatHistory(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("user.id"))
    document_id = Column(Integer, ForeignKey("document.id"))

    user = relationship("User", back_populates="chat_histories")
    document = relationship("Document", back_populates="chat_histories")