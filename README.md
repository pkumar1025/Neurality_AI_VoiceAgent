# AI Voice Agent for Patient Intake

This project is a real-time, AI-powered multilingual voice assistant built using the LiveKit Agents SDK. It demonstrates a scalable pipeline for voice-first patient engagement, with structured intent classification and natural language interaction.

## What It Does

The Neurality Voice Agent:
- Answers incoming phone calls via SIP (using Twilio + TwiML)
- Transcribes patient speech in real time (multilingual)
- Detects the intent of the request (e.g. appointment scheduling, billing, prescription, insurance)
- Validates provided addresses via the SmartyStreets API
- Responds using natural-sounding synthesized speech
- Outputs a structured JSON summary of the conversation

### Key Components:

- **LiveKit Room + Agents SDK**  
  Hosts the LLM-driven agent and handles real-time voice and text streaming in SIP-connected rooms.

- **Twilio SIP + LiveKit Telephony**  
  Routes inbound calls into LiveKit via a SIP domain and dispatch rule.

- **Deepgram STT**  
  Transcribes speech to text in real time and supports automatic language detection.

- **Cartesia Sonic TTS**  
  Converts the assistant's text replies into fluent, natural-sounding speech.

- **Silero VAD**  
  Used for detecting end-of-utterance in the caller's speech to ensure smooth turn-taking.

- **OpenAI GPT-4o**  
  Powers the voice agent's natural language understanding and response generation.

- **Conversation Monitoring Hook**
  Detects when the assistant emits a final JSON summary and saves it to output.json.

- **SmartyStreets API**
  Validates structured address input provided by the caller.

## ✉️ Email Confirmation Logic

Once the assistant says the phrase "Here is the summary of your request.", the backend automatically:
- Parses the message for valid JSON
- Extracts keys like transcript, intent, language, etc.
- Saves it to output.json

## Running the Agent Locally:
1. Clone the Repo
```bash
git clone https://github.com/pkumar1025/NeuralityVoiceAgent.git
cd NeuralityVoiceAgent
```
2. Set Up Your Environment
Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a .env file in the root directory and add the following:
```
SMARTY_AUTH_ID=your_auth_id
SMARTY_AUTH_TOKEN=your_auth_token
EMAIL_USER=your_gmail_address
EMAIL_PASS=your_gmail_app_password
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
```
You will also need valid credentials/API keys for:
- LiveKit
- Deepgram
- OpenAI
- Cartesia Sonic
- Twilio (for SIP)
- Phone Number Being Used: +1(833)-780-1460

3. Run the Agent
``` bash
python3 neurality_voice_ai.py dev
```
Once a call is completed, a structured output.json file will be generated in the root directory.
