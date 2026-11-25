import { useState, useEffect, useRef } from 'react';
import type { Doctor, Appointment, TranscriptItem, CallState } from './types';
import { Header } from './components/Header';
import { DoctorsList } from './components/DoctorsList';
import { AppointmentsTable } from './components/AppointmentsTable';
import { PhoneCallModal } from './components/PhoneCallModal';
import { liveEvents } from './services/sseEvents';
import type { LiveEventPayload } from './services/sseEvents';
import { VoiceClient } from './services/voiceClient';

export function App() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [callState, setCallState] = useState<CallState>('idle');
  const [isCallModalOpen, setIsCallModalOpen] = useState<boolean>(false);
  const [waveformLevels, setWaveformLevels] = useState<number[]>(new Array(16).fill(0.08));
  const [latestBookedAppointment, setLatestBookedAppointment] = useState<Appointment | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isLoadingDoctors, setIsLoadingDoctors] = useState<boolean>(true);
  const [isLoadingAppointments, setIsLoadingAppointments] = useState<boolean>(true);

  const voiceClientRef = useRef<VoiceClient | null>(null);

  // Fetch doctors list
  const loadDoctors = async () => {
    try {
      const res = await fetch('/api/doctors');
      if (!res.ok) throw new Error('Failed to load doctors');
      const data = await res.json();
      setDoctors(data.doctors || []);
      setBackendOnline(true);
    } catch (err) {
      console.warn('Could not load doctors:', err);
      setBackendOnline(false);
    } finally {
      setIsLoadingDoctors(false);
    }
  };

  // Fetch appointments list - sorted by most recently created at the top
  const loadAppointments = async () => {
    try {
      const res = await fetch('/api/appointments');
      if (!res.ok) throw new Error('Failed to load appointments');
      const data = await res.json();
      let apts: Appointment[] = data.appointments || [];

      // Demo query param helper for booked highlight screenshot
      if (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('demo') === 'booked') {
        const demoApt: Appointment = {
          id: 999,
          phone: '9876543210',
          patient_name: 'Rahul Sharma',
          doctor_id: 1,
          doctor_name: 'Dr. Priya Sharma',
          date: '2026-11-26',
          time: '10:30 AM',
          status: 'confirmed',
          _justUpdated: 'booked'
        };
        apts = [demoApt, ...apts.filter((a) => a.id !== 999)];
      }

      // Sort most recently created at top (by ID descending)
      apts.sort((a, b) => {
        if (a._justUpdated === 'booked') return -1;
        if (b._justUpdated === 'booked') return 1;
        return b.id - a.id;
      });

      setAppointments(apts);
      setBackendOnline(true);
    } catch (err) {
      console.warn('Could not load appointments:', err);
      setBackendOnline(false);
    } finally {
      setIsLoadingAppointments(false);
    }
  };

  // Initial load & SSE connection
  useEffect(() => {
    loadDoctors();
    loadAppointments();

    // Connect to live SSE/WebSocket event channel
    liveEvents.connect();

    // Demo query param helper for phone midcall and booking card demo states
    const urlParams = new URLSearchParams(window.location.search);
    const demoMode = urlParams.get('demo');

    if (demoMode === 'midcall' || demoMode === 'booking-card') {
      setIsCallModalOpen(true);
      setCallState('connected');
      setWaveformLevels([0.35, 0.65, 0.95, 0.75, 0.5, 0.85, 1.0, 0.7, 0.9, 0.8, 0.6, 0.95, 0.75, 0.5, 0.4, 0.25]);

      if (demoMode === 'booking-card') {
        setLatestBookedAppointment({
          id: 105,
          phone: '9876543210',
          patient_name: 'Rahul Sharma',
          doctor_id: 1,
          doctor_name: 'Dr. Priya Sharma',
          date: '2026-11-26',
          time: '10:30 AM',
          status: 'confirmed'
        });
      } else {
        setLatestBookedAppointment(null);
      }

      setTranscripts([
        {
          id: 't1',
          role: 'assistant',
          text: 'Hello! Thank you for calling Apollo Clinic. How can I help you today?',
          timestamp: '11:02 AM'
        },
        {
          id: 't2',
          role: 'user',
          text: "Hi, I'd like to book an appointment with Dr. Priya Sharma for tomorrow at 10:30 AM.",
          timestamp: '11:02 AM'
        },
        {
          id: 't3',
          role: 'assistant',
          text: 'Dr. Priya has 10:30 AM open tomorrow. Just to confirm, is your mobile number 9 8 7 6 5 4 3 2 1 0?',
          timestamp: '11:03 AM'
        },
        {
          id: 't4',
          role: 'user',
          text: 'Yes, that is correct.',
          timestamp: '11:03 AM'
        },
        {
          id: 't5',
          role: 'assistant',
          text: 'Your appointment with Dr. Priya Sharma is confirmed for Thu 26 Nov at 10:30 AM.',
          timestamp: '11:03 AM'
        }
      ]);
    }

    const unsubscribe = liveEvents.subscribe((payload: LiveEventPayload) => {
      console.log('[LiveEvent received]:', payload);
      const { event, data } = payload;

      if (event === 'connection_status') {
        setBackendOnline(data.status === 'connected');
      }

      if (event === 'appointment_booked') {
        const newApt = data as unknown as Appointment;
        setLatestBookedAppointment(newApt);
        // Prepend new appointment with highlight flag (most recent at top!)
        setAppointments((prev) => [
          { ...newApt, _justUpdated: 'booked' },
          ...prev.filter((a) => a.id !== newApt.id)
        ]);
        // Refresh doctor slots schedule
        loadDoctors();

        // Remove highlight effect after 2.5 seconds
        setTimeout(() => {
          setAppointments((current) =>
            current.map((a) => (a.id === newApt.id ? { ...a, _justUpdated: undefined } : a))
          );
        }, 2500);
      }

      if (event === 'appointment_cancelled') {
        const cancelledApt = data as unknown as Appointment;
        setAppointments((prev) =>
          prev.map((a) =>
            a.id === cancelledApt.id
              ? { ...cancelledApt, _justUpdated: 'cancelled' }
              : a
          )
        );
        // Refresh doctor slots schedule
        loadDoctors();

        setTimeout(() => {
          setAppointments((current) =>
            current.map((a) => (a.id === cancelledApt.id ? { ...a, _justUpdated: undefined } : a))
          );
        }, 2500);
      }

      if (event === 'transcript') {
        const transcriptData = data as unknown as { role: 'user' | 'assistant'; text: string; timestamp?: string };
        if (transcriptData.text) {
          const newItem: TranscriptItem = {
            id: String(Date.now()) + Math.random(),
            role: transcriptData.role,
            text: transcriptData.text,
            timestamp: transcriptData.timestamp || new Date().toLocaleTimeString()
          };
          setTranscripts((prev) => [...prev, newItem]);
        }
      }

      if (event === 'call_status') {
        const statusData = data as unknown as { status: string };
        if (statusData.status === 'connected') {
          setCallState('connected');
        } else if (statusData.status === 'ended') {
          setCallState('ended');
        }
      }

      if (event === 'database_reset') {
        loadDoctors();
        loadAppointments();
        setTranscripts([]);
        setLatestBookedAppointment(null);
      }
    });

    return () => {
      unsubscribe();
      liveEvents.disconnect();
    };
  }, []);

  // Handle Try Call action
  const handleStartCall = () => {
    setIsCallModalOpen(true);
    setErrorMessage(null);
    setLatestBookedAppointment(null);
    setTranscripts([]);

    if (!voiceClientRef.current) {
      voiceClientRef.current = new VoiceClient({
        onStateChange: (state: CallState) => {
          setCallState(state);
        },
        onUserTranscript: (text: string) => {
          setTranscripts((prev) => [
            ...prev,
            {
              id: String(Date.now()) + Math.random(),
              role: 'user',
              text,
              timestamp: new Date().toLocaleTimeString()
            }
          ]);
        },
        onBotTranscript: (text: string) => {
          setTranscripts((prev) => [
            ...prev,
            {
              id: String(Date.now()) + Math.random(),
              role: 'assistant',
              text,
              timestamp: new Date().toLocaleTimeString()
            }
          ]);
        },
        onWaveformLevels: (levels: number[]) => {
          setWaveformLevels(levels);
        },
        onError: (err: string) => {
          setErrorMessage(err);
        }
      });
    }

    voiceClientRef.current.startCall();
  };

  // Handle End Call action
  const handleEndCall = () => {
    if (voiceClientRef.current) {
      voiceClientRef.current.endCall();
    }
    setCallState('ended');
  };

  // Handle Mute toggle
  const handleToggleMute = () => {
    if (voiceClientRef.current) {
      const muted = voiceClientRef.current.toggleMute();
      setIsMuted(muted);
      return muted;
    }
    return false;
  };

  // Handle Reset DB action
  const handleResetDb = async () => {
    try {
      setIsResetting(true);
      await fetch('/api/reset', { method: 'POST' });
      await loadDoctors();
      await loadAppointments();
      setLatestBookedAppointment(null);
      setTranscripts([]);
    } catch (err) {
      console.error('Reset failed:', err);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#E8DCC6] text-[#3A1F23] flex flex-col font-sans m-0 p-0 border-0">
      {/* Top Clinic Header - completely flush with top of page */}
      <Header
        backendOnline={backendOnline}
        onStartCall={handleStartCall}
        onResetDb={handleResetDb}
        isResetting={isResetting}
      />

      {/* Main Dashboard: ~53% Doctors / ~47% Appointments on wide screens, stacked on narrow */}
      <main className="flex-1 max-w-[1360px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        
        {/* Offline Warning Banner */}
        {!backendOnline && (
          <div className="mb-6 p-4 rounded-xl bg-[#EBD3D0] border border-[#722F37]/30 text-[#722F37] text-xs flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#722F37]"></span>
              <span className="font-semibold">
                Backend server is unreachable on http://localhost:8000. Please ensure the Python FastAPI server is running.
              </span>
            </div>
            <button
              onClick={() => { loadDoctors(); loadAppointments(); }}
              className="px-3 py-1 text-xs font-semibold bg-[#F1E8D6] hover:bg-[#DDD0B8] text-[#722F37] border border-[#B7A89A] rounded-md cursor-pointer transition-colors"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Roughly 55% Doctors / 45% Appointments layout on lg screens, stacked on mobile */}
        <div className="grid grid-cols-1 lg:grid-cols-[51fr_49fr] gap-6 items-start">
          {/* Left Column: Doctors & Available Slots (~53-55%) */}
          <section className="w-full">
            <DoctorsList doctors={doctors} isLoading={isLoadingDoctors} />
          </section>

          {/* Right Column: Sticky Appointments Table (top: 24px on desktop) */}
          <section
            className="w-full lg:sticky self-start"
            style={{ position: 'sticky', top: '24px' }}
          >
            <AppointmentsTable
              appointments={appointments}
              isLoading={isLoadingAppointments}
            />
          </section>
        </div>
      </main>

      {/* Phone-Style Call Screen Overlay */}
      <PhoneCallModal
        isOpen={isCallModalOpen}
        callState={callState}
        transcripts={transcripts}
        waveformLevels={waveformLevels}
        latestBookedAppointment={latestBookedAppointment}
        errorMessage={errorMessage}
        onEndCall={handleEndCall}
        onClose={() => setIsCallModalOpen(false)}
        onToggleMute={handleToggleMute}
        isMuted={isMuted}
      />

      {/* Footer */}
      <footer className="border-t border-[#B7A89A] bg-[#E8DCC6] py-4 text-center text-xs text-[#6E5A54] font-sans">
        Apollo Healthcare Clinic Voice Assistant &bull; Pipecat &bull; ElevenLabs STT/TTS &bull; Google Gemini Flash &bull; SmallWebRTC
      </footer>
    </div>
  );
}

export default App;
