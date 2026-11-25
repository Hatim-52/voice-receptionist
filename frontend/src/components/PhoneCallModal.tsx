import React, { useState, useEffect, useRef } from 'react';
import type { CallState, TranscriptItem, Appointment } from '../types';
import { audioSounds } from '../services/audioSounds';
import {
  Phone,
  PhoneOff,
  Mic,
  MicOff,
  X,
  User,
  Clock,
  CalendarCheck,
  AlertTriangle
} from 'lucide-react';
import { formatCustomDate } from '../utils/dateFormatter';

interface PhoneCallModalProps {
  isOpen: boolean;
  callState: CallState;
  transcripts: TranscriptItem[];
  waveformLevels: number[];
  latestBookedAppointment: Appointment | null;
  errorMessage: string | null;
  onEndCall: () => void;
  onClose: () => void;
  onToggleMute: () => boolean;
  isMuted: boolean;
}

export const PhoneCallModal: React.FC<PhoneCallModalProps> = ({
  isOpen,
  callState,
  transcripts,
  waveformLevels,
  latestBookedAppointment,
  errorMessage,
  onEndCall,
  onClose,
  onToggleMute,
  isMuted
}) => {
  const [callDuration, setCallDuration] = useState<number>(() => {
    if (typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('demo') === 'midcall') {
      return 84; // 01:24 mid-call demo
    }
    return 0;
  });
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll transcript container as speech arrives
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  // Handle call timer and ringtone / disconnect sounds
  useEffect(() => {
    let interval: number | null = null;

    if (callState === 'ringing') {
      audioSounds.playRingtone();
      setCallDuration(0);
    } else if (callState === 'connected') {
      audioSounds.stopRingtone();
      interval = window.setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else if (callState === 'ended') {
      audioSounds.playCallEndTone();
    } else {
      audioSounds.stopRingtone();
    }

    return () => {
      if (interval) clearInterval(interval);
      audioSounds.stopRingtone();
    };
  }, [callState]);

  if (!isOpen) return null;

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-xs transition-opacity">
      {/* Phone Chassis Container: Cream phone body with line border */}
      <div className="relative w-full max-w-[380px] bg-[#F1E8D6] rounded-[28px] shadow-2xl border border-[#B7A89A] overflow-hidden flex flex-col h-[650px] max-h-[92vh]">
        
        {/* Top Speaker & Camera Notch */}
        <div className="bg-[#DDD0B8] pt-2.5 pb-2 px-6 flex items-center justify-between text-[#3A1F23] shrink-0 border-b border-[#B7A89A]">
          {/* Burgundy timer */}
          <div className="text-[11px] font-mono text-[#722F37] font-bold tracking-tight">
            {callState === 'connected' ? formatTimer(callDuration) : 'Apollo Voice'}
          </div>
          <div className="w-16 h-3 bg-[#E8DCC6] rounded-full border border-[#B7A89A] flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-[#722F37]"></div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close call screen"
            className="text-[#6E5A54] hover:text-[#722F37] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Call Status & Avatar Header */}
        <div className="bg-[#F1E8D6] text-[#3A1F23] px-5 pt-3.5 pb-3 text-center shrink-0 border-b border-[#B7A89A]">
          <div className="w-12 h-12 mx-auto rounded-full bg-[#DDD0B8] border border-[#B7A89A] flex items-center justify-center mb-1.5 shadow-xs">
            <User className="w-5 h-5 text-[#722F37]" />
          </div>

          <h3 className="text-base font-serif font-bold tracking-tight text-[#722F37]">
            Apollo Reception Desk
          </h3>

          <div className="text-xs text-[#6E5A54] flex items-center justify-center space-x-1.5 mt-0.5">
            {callState === 'ringing' && (
              <span className="text-[#722F37] animate-pulse font-semibold">
                Calling clinic...
              </span>
            )}
            {callState === 'connected' && (
              <span className="text-[#3F6B4A] font-mono font-semibold flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-[#3F6B4A] animate-ping inline-block mr-1"></span>
                Connected ({formatTimer(callDuration)})
              </span>
            )}
            {callState === 'ended' && (
              <span className="text-[#6E5A54] font-medium">Call Finished</span>
            )}
            {callState === 'error' && (
              <span className="text-[#722F37] font-medium">Connection Error</span>
            )}
          </div>

          {/* Live Reactive Burgundy Audio Waveform */}
          {callState === 'connected' && (
            <div className="mt-2.5 flex items-center justify-center space-x-1 h-6 px-4">
              {waveformLevels.map((lvl, idx) => (
                <div
                  key={idx}
                  className="w-1 bg-[#722F37] rounded-full waveform-bar"
                  style={{
                    height: `${Math.max(4, Math.round(lvl * 24))}px`,
                    opacity: Math.max(0.4, lvl)
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* In-Call Booking Confirmation Ticket Card: Prominent and sticky right under header */}
        {latestBookedAppointment && (
          <div className="px-3.5 pt-3 bg-[#E8DCC6] shrink-0">
            <div className="p-3 bg-[#F1E8D6] border-l-4 border-l-[#722F37] border-y border-r border-[#B7A89A] rounded-xl shadow-xs space-y-1">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-[#3F6B4A]">
                <CalendarCheck className="w-3.5 h-3.5 text-[#3F6B4A]" />
                <span>Appointment Confirmed</span>
              </div>
              <div className="text-xs font-serif font-bold text-[#722F37]">
                {latestBookedAppointment.doctor_name}
              </div>
              <div className="flex items-center justify-between text-[11px] text-[#3A1F23]">
                <span>{formatCustomDate(latestBookedAppointment.date)}</span>
                <span className="font-semibold text-[#722F37]">{latestBookedAppointment.time}</span>
              </div>
              <div className="text-[10px] text-[#6E5A54]">
                Patient: <span className="font-medium text-[#3A1F23]">{latestBookedAppointment.patient_name || 'Caller'}</span> (<span className="font-mono">{latestBookedAppointment.phone}</span>)
              </div>
            </div>
          </div>
        )}

        {/* Phone Content Area: Live Transcript Stream */}
        <div className="flex-1 bg-[#E8DCC6] p-3.5 overflow-y-auto space-y-2.5 scrollbar-thin">
          
          {/* Error Message banner */}
          {errorMessage && (
            <div className="p-3 rounded-lg bg-[#EBD3D0] border border-[#722F37]/30 text-[#722F37] text-xs flex items-start space-x-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Connecting State Placeholder */}
          {callState === 'ringing' && (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#6E5A54] space-y-2">
              <div className="w-7 h-7 rounded-full border-2 border-[#722F37] border-t-transparent animate-spin"></div>
              <p className="text-xs text-[#722F37] font-semibold">
                Establishing voice connection...
              </p>
              <p className="text-[11px] text-[#6E5A54]">
                Please make sure your microphone is unmuted.
              </p>
            </div>
          )}

          {/* Ended State Screen */}
          {callState === 'ended' && transcripts.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#6E5A54] space-y-2">
              <Clock className="w-8 h-8 text-[#B7A89A]" />
              <p className="text-xs font-semibold text-[#722F37]">
                Call completed ({formatTimer(callDuration)})
              </p>
              <button
                onClick={onClose}
                className="mt-2 px-4 py-1.5 text-xs font-semibold bg-[#722F37] text-[#F5EEDF] rounded-md cursor-pointer hover:bg-[#5E242C] transition-colors"
              >
                Close Phone
              </button>
            </div>
          )}

          {/* Live Transcript Stream: Agent = --surface-2, Caller = burgundy with cream text */}
          {transcripts.map((item) => {
            const isUser = item.role === 'user';
            return (
              <div
                key={item.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <span className="text-[10px] text-[#6E5A54] mb-0.5 px-1 font-medium">
                  {isUser ? 'You (Caller)' : 'Aanya (Receptionist)'}
                </span>
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed ${
                    isUser
                      ? 'bg-[#722F37] text-[#F5EEDF] font-normal rounded-tr-xs shadow-xs'
                      : 'bg-[#DDD0B8] text-[#3A1F23] border border-[#B7A89A]/50 rounded-tl-xs shadow-xs'
                  }`}
                >
                  {item.text}
                </div>
              </div>
            );
          })}

          <div ref={transcriptEndRef} />
        </div>

        {/* Bottom Phone Action Bar: burgundy mute button and burgundy-filled end-call button */}
        <div className="bg-[#DDD0B8] p-3.5 border-t border-[#B7A89A] flex items-center justify-around shrink-0">
          {/* Burgundy Mute Button */}
          <button
            onClick={onToggleMute}
            disabled={callState !== 'connected'}
            title={isMuted ? 'Unmute Microphone' : 'Mute Microphone'}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors cursor-pointer disabled:opacity-40 ${
              isMuted
                ? 'bg-[#722F37] text-[#F5EEDF]'
                : 'bg-[#F1E8D6] text-[#722F37] hover:bg-[#E8DCC6] border border-[#B7A89A]'
            }`}
          >
            {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>

          {/* End Call Button: Burgundy-filled end-call button */}
          {callState === 'connected' || callState === 'ringing' ? (
            <button
              onClick={onEndCall}
              title="End Call"
              className="w-14 h-14 rounded-full bg-[#722F37] hover:bg-[#5E242C] active:bg-[#4D1C23] text-[#F5EEDF] flex items-center justify-center shadow-md transition-transform hover:scale-105 active:scale-95 cursor-pointer"
            >
              <PhoneOff className="w-6 h-6 stroke-[2.2]" />
            </button>
          ) : (
            <button
              onClick={onClose}
              title="Dismiss"
              className="w-14 h-14 rounded-full bg-[#722F37] hover:bg-[#5E242C] text-[#F5EEDF] flex items-center justify-center transition-colors cursor-pointer shadow-sm"
            >
              <X className="w-6 h-6" />
            </button>
          )}

          {/* Audio phone status */}
          <div className="w-12 h-12 rounded-full bg-[#F1E8D6] border border-[#B7A89A] flex items-center justify-center text-[#722F37]/70">
            <Phone className="w-4 h-4 opacity-70" />
          </div>
        </div>

      </div>
    </div>
  );
};
