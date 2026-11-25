"""
bot.py - Pipecat Voice Pipeline & Tool Registration for Doctor Appointment Assistant.

Pipeline architecture:
Mic audio -> Silero VAD -> ElevenLabs Realtime STT -> Google Gemini LLM -> ElevenLabs TTS -> Audio Output (WebRTC)

Tools:
1. check_doctor_availability(doctor_name, speciality, date)
2. book_appointment(phone_number, doctor_name, date, time, patient_name)
3. cancel_appointment(phone_number)
"""

import os
import asyncio
from typing import Dict, Any, List
from dotenv import load_dotenv

# Pipecat core imports
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    TextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TTSSpeakFrame,
    EndFrame
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.adapters.llm.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

# Services
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.google.llm import GoogleLLMService

# Transport
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.base_transport import TransportParams

# Local modules
from backend import tools

load_dotenv()

# System Prompt embodying the voice receptionist persona and strict rules
SYSTEM_PROMPT = """
You are Aanya, a warm, efficient, and professional voice receptionist at Apollo Healthcare Clinic.
You are conversing with a patient over a voice phone call in real time.

CORE VOICE CONVERSATION RULES:
1. Keep your sentences short and natural (1 to 2 sentences per response). This is a spoken voice call, not text.
2. Greet the caller warmly, and handle one thing at a time.
3. NEVER read a long list of slots. Offer at most 2 to 3 available slots at a time.
4. The caller has no login, password, or OTP. The caller is identified ONLY by the 10-digit phone number they speak out loud.

CRITICAL CONFIRMATION PROTOCOL (MANDATORY & ENFORCED IN CODE):
- book_appointment and cancel_appointment require `phone_confirmed: true`.
- BEFORE calling book_appointment or cancel_appointment, you MUST ask for their phone number if not yet provided.
- You MUST read the 10-digit number back to the caller digit-by-digit (for example: "Just to verify, is your number 9 8 7 6 5 4 3 2 1 0?").
- You MUST receive an explicit verbal "yes" or confirmation from the caller BEFORE triggering book_appointment or cancel_appointment with `phone_confirmed: true`.
- If the caller says "no" or corrects any digit, update the number and read it back again until confirmed.
- If you call book_appointment or cancel_appointment without phone_confirmed=true, the system will reject the request.

TOOL USAGE GUIDELINES:
- Use check_doctor_availability to look up open slots by doctor name, speciality (e.g. Cardiologist, Dermatologist, General Physician, Pediatrician, Orthopedic, ENT), or relative date ('today', 'tomorrow', 'Wednesday'). It automatically filters out slots that have already passed today.
- Use book_appointment with phone_confirmed=true only after the caller confirms the digit-by-digit readback.
- Use cancel_appointment with phone_confirmed=true only after the caller confirms the digit-by-digit readback.
- If a slot is already taken or booking fails, explain the situation gently and suggest another available time.
- If no appointment is found for cancellation, politely inform the caller.
- You can check availability, book, and cancel within the same call.
"""

# Tool Schemas for Google Gemini
TOOL_CHECK_AVAILABILITY = FunctionSchema(
    name="check_doctor_availability",
    description="Check open appointment slots for a doctor or speciality on a specific date.",
    properties={
        "doctor_name": {
            "type": "string",
            "description": "Name of the doctor (e.g. 'Dr. Priya Sharma', 'Priya', or doctor's last name)."
        },
        "speciality": {
            "type": "string",
            "description": "Medical speciality or symptom (e.g. General Physician, Cardiologist, Dermatologist, Pediatrician, Orthopedic, ENT, or fever, skin, heart, child)."
        },
        "date": {
            "type": "string",
            "description": "Target date, such as 'today', 'tomorrow', day of the week like 'Wednesday', or ISO format YYYY-MM-DD."
        }
    },
    required=[]
)

TOOL_BOOK_APPOINTMENT = FunctionSchema(
    name="book_appointment",
    description="Book a doctor appointment slot for the caller. Requires phone_confirmed=true after caller confirms digit-by-digit readback.",
    properties={
        "phone_number": {
            "type": "string",
            "description": "The caller's 10-digit mobile number."
        },
        "doctor_name": {
            "type": "string",
            "description": "Name or speciality of the doctor to book."
        },
        "date": {
            "type": "string",
            "description": "Date of appointment, e.g. 'today', 'tomorrow', or YYYY-MM-DD."
        },
        "time": {
            "type": "string",
            "description": "Time slot chosen by caller, e.g. '10:30 AM', '02:00 PM'."
        },
        "patient_name": {
            "type": "string",
            "description": "Optional patient name provided by caller."
        },
        "phone_confirmed": {
            "type": "boolean",
            "description": "Must be set to true ONLY AFTER the caller has explicitly confirmed the digit-by-digit phone readback."
        }
    },
    required=["phone_number", "doctor_name", "date", "time", "phone_confirmed"]
)

TOOL_CANCEL_APPOINTMENT = FunctionSchema(
    name="cancel_appointment",
    description="Cancel the caller's existing active doctor appointment using their verified phone number. Requires phone_confirmed=true.",
    properties={
        "phone_number": {
            "type": "string",
            "description": "The caller's 10-digit mobile number."
        },
        "phone_confirmed": {
            "type": "boolean",
            "description": "Must be set to true ONLY AFTER the caller has explicitly confirmed the digit-by-digit phone readback."
        }
    },
    required=["phone_number", "phone_confirmed"]
)


# ==============================================================================
# Tool Execution Handlers
# ==============================================================================

async def handle_check_doctor_availability(params: FunctionCallParams):
    """Execute check_doctor_availability tool."""
    args = params.arguments
    doc_name = args.get("doctor_name")
    spec = args.get("speciality")
    dt = args.get("date")

    print(f"[Tool] check_doctor_availability called with doc={doc_name}, spec={spec}, date={dt}")
    result = tools.check_doctor_availability(doctor_name=doc_name, speciality=spec, date=dt)
    await params.result_callback(result)


async def handle_book_appointment(params: FunctionCallParams):
    """Execute book_appointment tool."""
    args = params.arguments
    phone = args.get("phone_number", "")
    doc_name = args.get("doctor_name", "")
    dt = args.get("date", "")
    tm = args.get("time", "")
    patient = args.get("patient_name")
    phone_confirmed = args.get("phone_confirmed", False)

    print(f"[Tool] book_appointment called with phone={phone}, doc={doc_name}, date={dt}, time={tm}, confirmed={phone_confirmed}")
    result = tools.book_appointment(
        phone_number=phone,
        doctor_name=doc_name,
        date=dt,
        time=tm,
        patient_name=patient,
        phone_confirmed=phone_confirmed
    )
    await params.result_callback(result)


async def handle_cancel_appointment(params: FunctionCallParams):
    """Execute cancel_appointment tool."""
    args = params.arguments
    phone = args.get("phone_number", "")
    phone_confirmed = args.get("phone_confirmed", False)

    print(f"[Tool] cancel_appointment called with phone={phone}, confirmed={phone_confirmed}")
    result = tools.cancel_appointment(
        phone_number=phone,
        phone_confirmed=phone_confirmed
    )
    await params.result_callback(result)


# ==============================================================================
# Live Transcript Broadcaster Processor
# ==============================================================================

class TranscriptBroadcaster(FrameProcessor):
    """
    Pipeline frame processor that intercepts user speech transcription
    and assistant LLM responses to broadcast live transcript events to the UI.
    """
    def __init__(self):
        super().__init__()
        self._assistant_buffer: List[str] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        # 1. User STT Final Transcription
        if isinstance(frame, TranscriptionFrame) and frame.text.strip():
            user_text = frame.text.strip()
            print(f"[Transcript] Caller: {user_text}")
            tools.notify_event("transcript", {
                "role": "user",
                "text": user_text,
                "timestamp": frame.timestamp or ""
            })

        # 2. Assistant Response Accumulation
        elif isinstance(frame, LLMFullResponseStartFrame):
            self._assistant_buffer = []

        elif isinstance(frame, TextFrame) and frame.text:
            self._assistant_buffer.append(frame.text)

        elif isinstance(frame, LLMFullResponseEndFrame):
            if self._assistant_buffer:
                full_agent_text = "".join(self._assistant_buffer).strip()
                if full_agent_text:
                    print(f"[Transcript] Agent: {full_agent_text}")
                    tools.notify_event("transcript", {
                        "role": "assistant",
                        "text": full_agent_text
                    })
            self._assistant_buffer = []

        await self.push_frame(frame, direction)


# ==============================================================================
# Pipeline Runner Factory
# ==============================================================================

async def run_bot_pipeline(webrtc_connection: SmallWebRTCConnection):
    """
    Build and run the Pipecat voice pipeline for an active WebRTC session.
    """
    eleven_api_key = os.getenv("ELEVENLABS_API_KEY", "")
    eleven_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel / clear reception voice
    google_api_key = os.getenv("GOOGLE_API_KEY", "")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not google_api_key or google_api_key.startswith("your_"):
        print("[bot.py] WARNING: GOOGLE_API_KEY is not set or placeholder. Please provide a valid key in .env.")
    if not eleven_api_key or eleven_api_key.startswith("your_"):
        print("[bot.py] WARNING: ELEVENLABS_API_KEY is not set or placeholder. Please provide a valid key in .env.")

    # 1. SmallWebRTC Transport
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            video_in_enabled=False,
            video_out_enabled=False
        )
    )

    # 2. Silero VAD (Voice Activity Detection)
    vad = SileroVADAnalyzer()

    # 3. ElevenLabs Realtime STT
    stt = ElevenLabsRealtimeSTTService(
        api_key=eleven_api_key,
        model="scribe_v1"
    )

    # 4. Google LLM Service (Gemini Flash)
    llm = GoogleLLMService(
        api_key=google_api_key,
        settings=GoogleLLMService.Settings(
            model=gemini_model,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3
        )
    )

    # Register the 3 tools with LLM
    llm.register_function("check_doctor_availability", handle_check_doctor_availability)
    llm.register_function("book_appointment", handle_book_appointment)
    llm.register_function("cancel_appointment", handle_cancel_appointment)

    # 5. ElevenLabs TTS
    tts = ElevenLabsTTSService(
        api_key=eleven_api_key,
        voice_id=eleven_voice_id,
        model="eleven_turbo_v2_5"
    )

    # 6. Tools schema and Context
    tools_schema = ToolsSchema(
        standard_tools=[
            TOOL_CHECK_AVAILABILITY,
            TOOL_BOOK_APPOINTMENT,
            TOOL_CANCEL_APPOINTMENT
        ]
    )

    context = LLMContext(tools=tools_schema)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(context)

    # 7. Transcript Broadcaster
    broadcaster = TranscriptBroadcaster()

    # 8. Pipeline Assembly
    pipeline = Pipeline([
        transport.input(),        # Incoming mic audio from browser
        vad,                      # Silero VAD to detect user speech boundaries
        stt,                      # ElevenLabs Realtime STT
        broadcaster,              # Broadcast live transcripts
        user_aggregator,          # Context aggregator for user turn
        llm,                      # Google Gemini with registered function calling tools
        tts,                      # ElevenLabs TTS
        transport.output(),       # Outgoing audio track to browser
        assistant_aggregator      # Context aggregator for assistant turn
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            enable_metrics=False
        )
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport_inst, client):
        print(f"[bot.py] Client connected to WebRTC session (pc_id: {client.pc_id})")
        tools.notify_event("call_status", {"status": "connected", "pc_id": client.pc_id})
        # Queue initial friendly greeting
        greeting = "Hello! Thank you for calling Apollo Clinic. I can help you check doctor availability, book an appointment, or cancel an appointment. How can I help you today?"
        await task.queue_frame(TTSSpeakFrame(text=greeting, append_to_context=True))

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport_inst, client):
        print(f"[bot.py] Client disconnected from WebRTC session (pc_id: {client.pc_id})")
        tools.notify_event("call_status", {"status": "ended", "pc_id": client.pc_id})
        await task.queue_frame(EndFrame())

    runner = PipelineRunner()
    print("[bot.py] Starting voice pipeline runner...")
    try:
        await runner.run(task)
    except Exception as e:
        print(f"[bot.py] Pipeline runner finished with: {e}")
    finally:
        print("[bot.py] Pipeline session ended.")
