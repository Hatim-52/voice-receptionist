# Voice Pipeline Architecture

For this project, I built a real-time voice pipeline using Pipecat in Python, connecting the user's browser directly to the AI assistant over WebRTC. 

When a user clicks "Try Call", their browser microphone audio streams to the backend via Pipecat's SmallWebRTC transport without needing any third-party media gateway. On the server, incoming audio is first processed by a local Silero VAD (Voice Activity Detection) model to accurately detect when the caller starts and finishes speaking.

Once speech is detected, the audio goes into ElevenLabs Realtime STT (using the Scribe model) for low-latency speech-to-text transcription. The transcribed text flows into Google Gemini 2.5 Flash via Pipecat's Google service. I configured Gemini with a strict system prompt and three function calling tools: checking doctor availability, booking an appointment, and cancelling an appointment.

When Gemini decides to call a tool, my Python handlers execute the query against SQLite, enforce digit-by-digit phone confirmation, and prevent slot collisions. The LLM's streaming response is synthesized into speech using ElevenLabs TTS (Turbo v2.5) and sent back over the WebRTC audio track to the user's headphones, while live transcripts and database changes stream to the dashboard over Server-Sent Events.
