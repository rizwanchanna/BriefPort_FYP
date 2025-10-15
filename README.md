# 📑 Smart Document Assistant

BriefPort is an intelligent web application designed to make sense of your information fast. Whether it’s a document, audio, or video, BriefPort transforms complex content into concise summaries, actionable reports, and interactive chats, all in one unified platform.

## ✨ Features

- 📊 **Smart Summarization**: Automatically generate concise summaries from large documents
- 📝 **Report Generation**: Create structured reports from processed documents
- 💬 **Document Chat**: Interactive Q&A with your documents
- 🚀 **Bulk Processing**: Handle multiple large files efficiently

## 🎧 Output Formats

- Text Summary → Read your summary instantly.

- Audio Summary → Listen to your summary, perfect for multitasking.

- Text Reports → Professionally formatted reports ready for export.

- Chat Interface → Query the document directly to extract exactly what you need.

## 🛠️ Tech Stack

- Authentication: JWT-based secure login system
- Backend: Python (FastAPI)
- Document Processing: Langchain, FFmpeg, Whisper
- Database: SQLalchemy

## 🚀 Getting Started

```bash
# Clone repository
git clone https://github.com/rizwanchanna/BriefPort_FYP.git

# Change to project Directory
cd BriefPort_FYP

# Install dependencies
pip install -r requirements.txt

# Start development server
uvicorn main:app
```

## 💡 Usage

1. Register yourself
2. Upload your documents(e.g. pdf, docx, text, mp3, .wav, mp4, m4a)
3. Choose processing options (by default "short" for summary and "formal" for report)
4. Get instant summaries and reports
5. Chat with your documents

Note: You can generate multiple summaries and reports

### 💡 **Use Cases**

#### 🎓 **Students & Researchers**

* Quickly generate **summaries of lengthy research papers, dissertations, and academic journals** to save time on reading.
* Use **document chat** to ask specific questions about a paper’s methodology, findings, or conclusions.
* Create **literature review reports** automatically by combining multiple uploaded research documents.
* Convert lectures or seminars (uploaded as audio/video) into clean, readable notes or executive summaries.

#### 💼 **Business Analysts & Corporate Teams**

* Upload meeting transcripts, performance reports, or strategy documents and receive **executive-level summaries** in minutes.
* Generate **project status reports** automatically from team updates or CSV exports.
* Use the **chat interface** to pull insights such as “top KPIs from Q3” or “key recommendations from the strategy document.”
* Export the results into **PDF or DOCX reports** for presentations or briefings.

#### 🎥 **Content Creators & Media Professionals**

* Upload podcasts, interviews, or video content to generate **time-stamped summaries** or topic outlines.
* Transform your recordings into **written reports** or blog drafts automatically.
* Use document chat to **find quotes, highlights, or sound bites** from long recordings.
* Generate **audio summaries** to repurpose written content into shareable voice clips or previews.

#### ⚖️ **Legal & Financial Institutions**

* Process contracts, policy documents, or compliance reports and generate **clause-level summaries** for quick review.
* Use document chat to ask questions like, “What are the termination conditions?” or “What is the late payment penalty?”
* Create **case summaries** or **due diligence reports** from multiple uploaded legal documents.
* Ensure accuracy and consistency by using AI to cross-check key terms and entities.

#### 🏢 **Insurance Firms & Risk Analysts**

* Upload **policy documents**, **claims reports**, or **risk assessment files** and let BriefPort summarize the essentials automatically.
* Generate structured **claim summaries**, **underwriting reports**, or **customer communication drafts**.
* Chat directly with uploaded policies to ask, “What does this policy exclude?” or “What’s the deductible limit for this coverage?”
* Transform **audio claim interviews** or **field inspection videos** into accurate, concise **text reports**.
* Use summarization tools to quickly review **regulatory documents** and maintain compliance records.
* Export the results as **formatted claim briefs**, **risk reports**, or **executive summaries** for internal and client use.

#### 🧾 **Government & Public Sector**

* Summarize **policy documents**, **meeting minutes**, or **public reports** into clear, accessible summaries.
* Generate **citizen-friendly summaries** of regulations or legislation.
* Facilitate internal collaboration by chatting with lengthy official documents to extract specific data or decisions.

#### 🧑‍💼 **Consultants & Auditors**

* Upload client documents, contracts, and project proposals to generate **audit summaries** and **recommendation reports**.
* Use chat to query project details like “main compliance risks” or “financial inconsistencies.”
* Export all findings as structured reports ready for client presentation.