# EduBot - WhatsApp AI Assistant

EduBot is a robust, highly interactive AI-powered WhatsApp assistant designed for educational institutions and coaching academies. Built with FastAPI and integrated with Twilio, EduBot handles lead generation, course inquiries, scheduling, and automatic enrollment processing via WhatsApp.

## Features

- **Conversational AI**: Understands natural language queries using LLMs (via Groq).
- **Voice Note Processing**: Automatically transcribes and responds to user voice notes.
- **RAG Engine**: Uses Retrieval-Augmented Generation (RAG) with FAISS to accurately answer questions about courses, fees, schedules, and eligibility based on academy data.
- **Lead Capture & Enrollment Funnel**: Guides students through a dynamic enrollment process, capturing lead details (name, email, preferred course) directly inside WhatsApp.
- **Dynamic FOMO Offers**: Automatically injects "Fear Of Missing Out" discount offers (e.g., 10% off) during active conversations to boost conversion rates.
- **Sentiment & Intent Classification**: Analyzes message intent and user sentiment to provide contextual replies.
- **Auto-Escalation**: Detects complex queries or objections and seamlessly hands over the conversation to a human counsellor.
- **Rich Media**: Dynamically sends appropriate course brochures (JEE, NEET, etc.) as images within the chat.
- **Admin Dashboard & Analytics**: A built-in `/leads` endpoint provides a funnel overview and exports captured leads for the sales team.

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: SQLite / SQLAlchemy (easily swapable to PostgreSQL/MySQL)
- **WhatsApp Integration**: Twilio API (Webhook)
- **AI & ML**: 
  - Groq (for LLM intent/sentiment classification)
  - `sentence-transformers` & `faiss-cpu` (for RAG document retrieval)
- **Task Scheduling**: APScheduler (for automated follow-ups)

## Prerequisites

- Python 3.9+
- A Twilio Account (for WhatsApp Sandbox or Business API)
- Groq API Key

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/edubot.git
   cd edubot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Environment Variables:**
   Create a `.env` file in the root directory and add:
   ```env
   GROQ_API_KEY=your_groq_api_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   # Add other required environment variables here
   ```

## Running the Application

1. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```
   The server will start on `http://127.0.0.1:8000`.

2. **Expose to the Web (for Twilio webhook):**
   Use ngrok to expose your local server:
   ```bash
   ngrok http 8000
   ```
   Copy the generated HTTPS URL (e.g., `https://<your-ngrok-id>.ngrok-free.app`).

3. **Configure Twilio:**
   Go to your Twilio WhatsApp Sandbox settings and set the **"When a message comes in"** webhook URL to:
   `https://<your-ngrok-id>.ngrok-free.app/inbound`

## API Endpoints

- `POST /inbound`: The primary Twilio WhatsApp webhook endpoint.
- `GET /leads`: Admin endpoint to view captured leads and funnel metrics. (Accepts optional `?status=new|contacted|enrolled` query parameter).
- `GET /health`: Basic health check endpoint.

## Project Structure

- `main.py`: The core FastAPI application, webhook routing, and business logic.
- `database.py` & `models.py`: Database setup and SQLAlchemy ORM models (e.g., Lead schema).
- `rag_engine.py`: FAISS-based vector search and document retrieval logic.
- `intent_classifier.py`: LLM integration for intent and sentiment analysis.
- `session_manager.py`: Manages user state and context across WhatsApp messages.
- `lead_manager.py`: Handles the step-by-step lead capture and enrollment process.
- `audio_handler.py`: Logic for downloading and transcribing WhatsApp voice notes.

## License

This project is licensed under the MIT License.
