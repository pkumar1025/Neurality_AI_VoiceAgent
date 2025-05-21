import os
import re
import requests
import json
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, Agent, JobContext, ConversationItemAddedEvent
from livekit.plugins import openai, cartesia, deepgram, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys
openai_key = os.getenv("OPENAI_API_KEY")
deepgram_key = os.getenv("DEEPGRAM_API_KEY")
smarty_auth_id = os.getenv("SMARTY_AUTH_ID")
smarty_auth_token = os.getenv("SMARTY_AUTH_TOKEN")

# Validate required keys
required_keys = {
    "OPENAI_API_KEY": openai_key,
    "DEEPGRAM_API_KEY": deepgram_key,
    "SMARTY_AUTH_ID": smarty_auth_id,
    "SMARTY_AUTH_TOKEN": smarty_auth_token
}
for name, value in required_keys.items():
    if not value:
        raise EnvironmentError(f"Missing {name}. Check your .env file.")

# Address validation using SmartyStreets
def validate_address(street, city=None, state=None, zipcode=None):
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

    match_code = data[0].get("analysis", {}).get("dpv_match_code", "")
    if match_code == "Y":
        return True, "Address is valid and complete."
    elif match_code == "D":
        return False, "Missing apartment or suite number."
    else:
        return False, f"Invalid address (DPV code: {match_code})"

# Voice agent entrypoint
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model="nova-2"),
        llm=openai.LLM(model="gpt-4o"),
        tts=cartesia.TTS(model="sonic-english"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel()
    )

    # Save final JSON output when the assistant delivers it
    def handle_conversation_item(event: ConversationItemAddedEvent):
        if (
            event.item.role == "assistant" and
            "Here is the summary of your request" in event.item.text_content
        ):
            print("Saving final summary JSON.")
            try:
                match = re.search(r"\{.*\}", event.item.text_content, re.DOTALL)
                if not match:
                    raise ValueError("No JSON found in assistant message.")

                json_str = match.group(0)
                parsed = json.loads(json_str)

                with open("output.json", "w") as f:
                    json.dump(parsed, f, indent=2, ensure_ascii=False)

                print("Output.json saved.")
            except Exception as e:
                print("Failed to extract/save JSON:", e)

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
        instructions="Greet the user and begin the conversation."
    )

# Run locally
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="AI_Patient_VoiceAgent"
    ))

