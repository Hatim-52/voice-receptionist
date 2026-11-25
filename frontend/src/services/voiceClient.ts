/**
 * voiceClient.ts - Browser Voice Call Client powered by Pipecat SmallWebRTC.
 * Manages peer connection, microphone capture, bot audio playback, and audio waveform analysis.
 */

import { PipecatClient } from '@pipecat-ai/client-js';
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';
import type { CallState } from '../types';

export interface VoiceClientCallbacks {
  onStateChange: (state: CallState) => void;
  onUserTranscript?: (text: string) => void;
  onBotTranscript?: (text: string) => void;
  onWaveformLevels?: (levels: number[]) => void;
  onError?: (error: string) => void;
}

export class VoiceClient {
  private client: PipecatClient | null = null;
  private audioEl: HTMLAudioElement | null = null;
  private audioCtx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private animFrameId: number | null = null;
  private isMuted: boolean = false;
  private callbacks: VoiceClientCallbacks;
  private micStream: MediaStream | null = null;

  constructor(callbacks: VoiceClientCallbacks) {
    this.callbacks = callbacks;
  }

  /**
   * Start voice call: requests microphone, initializes SmallWebRTC, and connects to /api/offer.
   */
  public async startCall(): Promise<void> {
    try {
      this.callbacks.onStateChange('ringing');

      // 1. Explicitly check / request microphone permission
      try {
        this.micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      } catch (micErr: unknown) {
        const msg = (micErr as Error)?.name === 'NotAllowedError'
          ? 'Microphone permission was denied by your browser. Please allow microphone access to talk to the receptionist.'
          : 'Could not access microphone. Please check your audio input devices.';
        this.callbacks.onError?.(msg);
        this.callbacks.onStateChange('error');
        return;
      }

      // 2. Set up audio element for bot playback
      if (!this.audioEl) {
        this.audioEl = new Audio();
        this.audioEl.autoplay = true;
      }

      // 3. Set up Web Audio Analyser for reactive waveform
      this.setupAudioAnalyser(this.micStream);

      // 4. Initialize Pipecat Client with SmallWebRTC Transport
      const transport = new SmallWebRTCTransport();
      this.client = new PipecatClient({
        transport,
        enableCam: false,
        enableMic: true,
        callbacks: {
          onConnected: () => {
            console.log('[VoiceClient] Connected to voice bot!');
            this.callbacks.onStateChange('connected');
          },
          onDisconnected: () => {
            console.log('[VoiceClient] Disconnected from voice bot');
            this.handleCallEnded();
          },
          onTrackStarted: (track: MediaStreamTrack) => {
            console.log('[VoiceClient] Track started:', track.kind);
            if (track.kind === 'audio' && this.audioEl) {
              const stream = new MediaStream([track]);
              this.audioEl.srcObject = stream;
              this.audioEl.play().catch(console.error);
              // Also feed bot audio stream to analyser
              this.setupAudioAnalyser(stream);
            }
          },
          onUserTranscript: (data: { text: string }) => {
            if (data?.text) {
              this.callbacks.onUserTranscript?.(data.text);
            }
          },
          onBotTranscript: (data: { text: string }) => {
            if (data?.text) {
              this.callbacks.onBotTranscript?.(data.text);
            }
          },
          onError: (err: unknown) => {
            console.error('[VoiceClient] Pipecat error:', err);
            this.callbacks.onError?.(String(err));
          }
        }
      });

      // 5. Connect to the FastAPI offer endpoint
      const connectionUrl = `${window.location.origin}/api/offer`;
      await this.client.connect({
        connection_url: connectionUrl
      });

    } catch (err: unknown) {
      console.error('[VoiceClient] Failed to start call:', err);
      const errMsg = (err as Error)?.message || 'Failed to establish voice call connection.';
      this.callbacks.onError?.(errMsg);
      this.callbacks.onStateChange('error');
      this.cleanup();
    }
  }

  /**
   * Set up Web Audio AnalyserNode to feed frequency data to waveform callback.
   */
  private setupAudioAnalyser(stream: MediaStream) {
    try {
      if (!this.audioCtx) {
        const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        this.audioCtx = new AudioCtxClass();
      }
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }

      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 64;
      this.analyser.smoothingTimeConstant = 0.7;

      const source = this.audioCtx.createMediaStreamSource(stream);
      source.connect(this.analyser);

      this.startWaveformLoop();
    } catch (err) {
      console.warn('[VoiceClient] Could not set up waveform analyser:', err);
    }
  }

  private startWaveformLoop() {
    if (this.animFrameId) return;

    const bufferLength = this.analyser?.frequencyBinCount || 32;
    const dataArray = new Uint8Array(bufferLength);

    const tick = () => {
      if (this.analyser) {
        this.analyser.getByteFrequencyData(dataArray);
        // Normalize 16 bands to 0.0 - 1.0 range
        const bands = 16;
        const step = Math.floor(bufferLength / bands);
        const levels: number[] = [];
        for (let i = 0; i < bands; i++) {
          const val = dataArray[i * step] / 255;
          levels.push(Math.max(0.08, val)); // Minimum baseline height
        }
        this.callbacks.onWaveformLevels?.(levels);
      }
      this.animFrameId = requestAnimationFrame(tick);
    };

    tick();
  }

  /**
   * Toggle microphone mute state.
   */
  public toggleMute(): boolean {
    if (!this.client && !this.micStream) return false;

    this.isMuted = !this.isMuted;
    if (this.client) {
      try {
        this.client.enableMic(!this.isMuted);
      } catch (err) {
        console.warn('client.enableMic error:', err);
      }
    }
    if (this.micStream) {
      this.micStream.getAudioTracks().forEach((track) => {
        track.enabled = !this.isMuted;
      });
    }
    return this.isMuted;
  }

  public getIsMuted(): boolean {
    return this.isMuted;
  }

  /**
   * End voice call gracefully.
   */
  public endCall(): void {
    if (this.client) {
      try {
        this.client.disconnect();
      } catch (err) {
        console.warn('Disconnect error:', err);
      }
    }
    this.handleCallEnded();
  }

  private handleCallEnded() {
    this.cleanup();
    this.callbacks.onStateChange('ended');
  }

  private cleanup() {
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    if (this.micStream) {
      this.micStream.getTracks().forEach((track) => track.stop());
      this.micStream = null;
    }
    if (this.audioEl) {
      this.audioEl.srcObject = null;
    }
    if (this.audioCtx) {
      try {
        this.audioCtx.close();
      } catch {
        // Ignore
      }
      this.audioCtx = null;
    }
    this.analyser = null;
    this.client = null;
    this.isMuted = false;
  }
}
