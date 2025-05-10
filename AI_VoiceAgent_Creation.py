import os
import re
import requests
import smtplib
import json
from email.mime.text import MIMEText
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, Agent, JobContext, ConversationItemAddedEvent
from livekit.plugins import openai, cartesia, deepgram, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Creates instance of a conversational AI agent session that can:
    # 1) Listen to audio input
    # 2) Detect when a person is speaking (VAD, Voice Activity Detection)
    # 3) Transcribe Speech (Speech to Text)
    # 4) Generate a text response through an LLM
    # 5) Speak the response aloud (Text to Speech)
    # 6) Detect turn-taking behavior (Turn detection)

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys
openai_key = os.getenv("OPENAI_API_KEY")
deepgram_key = os.getenv("DEEPGRAM_API_KEY")
smarty_auth_id = os.getenv("SMARTY_AUTH_ID")
smarty_auth_token = os.getenv("SMARTY_AUTH_TOKEN")

# # Validate that keys are present
required_keys = {
    "OPENAI_API_KEY": openai_key,
    "DEEPGRAM_API_KEY": deepgram_key,
    "SMARTY_AUTH_ID": smarty_auth_id,
    "SMARTY_AUTH_TOKEN": smarty_auth_token
}
for name, value in required_keys.items():
    if not value:
        raise EnvironmentError(f"Missing {name}. Check your .env file.")

# Function to validate address using SmartyStreets API
def validate_address(street, city=None, state=None, zipcode=None):
    # API endpoint to SmartyStreets Server
    url = "https://us-street.api.smarty.com/street-address" 
    params = {
        "auth-id": smarty_auth_id,
        "auth-token": smarty_auth_token,
        "street": street
    }
    if city: params["city"] = city
    if state: params["state"] = state
    if zipcode: params["zipcode"] = zipcode
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if response.status_code != 200 or not data:
        return False, "Address not found or incomplete."
    
    #Gets DPV match code from result, which indicates whether address is valid and deliverable
    match_code = data[0].get("analysis", {}).get("dpv_match_code", "")
    if match_code == "Y":
        return True, "Address is valid and complete."
    elif match_code == "D":
        return False, "Missing apartment or suite number."
    else:
        return False, f"Invalid address (DPV code: {match_code})"

# Send confirmation email after session ends
def send_summary_email(name, doctor, time):
    print(f"Triggering confirmation email for {name}, {doctor}, {time}")
    msg = MIMEText(f"{name} has scheduled an appointment with {doctor} on {time}.")
    msg["Subject"] = "New Appointment Intake"
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = ", ".join(["jeff@assorthealth.com", "connor@assorthealth.com", "cole@assorthealth.com"])

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.sendmail(msg["From"], msg["To"].split(", "), msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", e)

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model="nova-2"),
        llm=openai.LLM(model="gpt-4o"),
        tts=cartesia.TTS(model="sonic-english"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel()
    )

    # Trigger email when assistant says: "Your appointment has been scheduled."
    def handle_conversation_item(event: ConversationItemAddedEvent):
        if (
            event.item.role == "assistant" and
            "Your appointment has been scheduled." in event.item.text_content
        ):
            print("Sending confirmation email.")
            try:
                # Extract JSON block from message
                match = re.search(r"\{.*\}", event.item.text_content, re.DOTALL)
                if not match:
                    raise ValueError("No JSON found in assistant message.")

                json_str = match.group(0)
                info = json.loads(json_str)
                name = info.get("patient_name", "Unknown")
                doctor = info.get("doctor_name", "Unknown")
                time = info.get("appointment_time", "Unknown")
                send_summary_email(name, doctor, time)
            except Exception as e:
                print("Failed to parse assistant message for email:", e)

    session.on("conversation_item_added")(handle_conversation_item)

    agent = Agent(
        instructions="""
        You are a friendly and helpful voice-based medical intake assistant.
        Walk the caller through the following steps:
        1. Ask for the patient's full name and date of birth.
        2. Collect insurance information: payer name and payer ID.
        3. Ask if they have a referral, and to which physician.
        4. Ask for their chief complaint or reason for the visit.
        5. Ask for their full address (street, city, state, and ZIP code).
            - After collecting it, check if it is valid using an external API.
            - If it’s incomplete or invalid, politely ask the user to repeat it.
        6. Collect contact information: phone number (required), and email (optional).
        7. Offer the following appointment options:
            - Dr. Jane Smith, Monday at 9 AM
            - Dr. Mark Patel, Tuesday at 1 PM
            - Dr. Emily Zhang, Wednesday at 3 PM
        8. Let the user choose one, then repeat the full intake details for confirmation.
        9. End the call politely.
        At the end, summarize the intake in the following JSON format in a message: 
        {
          "patient_name": "<name>",
          "doctor_name": "<doctor>",
          "appointment_time": "<time>"
        }
        Then say: Your appointment has been scheduled.
        """
    )

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions()
    )

    await session.generate_reply(
        instructions="Greet the user and begin the intake process."
    )

# Run Locally for Testing Purposes
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="AI_Patient_VoiceAgent"
    ))

