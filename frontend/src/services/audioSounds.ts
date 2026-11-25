/**
 * audioSounds.ts - Web Audio API Sound Synthesizer & Waveform Analyzer.
 * Generates realistic telephony ringtones and disconnect tones without asset files.
 */

class AudioSoundService {
  private audioCtx: AudioContext | null = null;
  private ringtoneInterval: number | null = null;
  private ringtoneOscillators: OscillatorNode[] = [];

  private getAudioContext(): AudioContext {
    if (!this.audioCtx) {
      const AudioCtxClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.audioCtx = new AudioCtxClass();
    }
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  }

  /**
   * Play continuous telephony ringing cadence (440Hz + 480Hz).
   * Repeats every 3.5 seconds until stopRingtone is called.
   */
  public playRingtone() {
    this.stopRingtone();
    const ctx = this.getAudioContext();

    const playBurst = () => {
      try {
        const now = ctx.currentTime;
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gain = ctx.createGain();

        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(440, now); // Standard North American ringing frequency

        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(480, now);

        gain.gain.setValueAtTime(0, now);
        // Smooth fade-in
        gain.gain.linearRampToValueAtTime(0.12, now + 0.05);
        // Hold for 1.4 seconds
        gain.gain.setValueAtTime(0.12, now + 1.4);
        // Smooth fade-out
        gain.gain.linearRampToValueAtTime(0, now + 1.5);

        osc1.connect(gain);
        osc2.connect(gain);
        gain.connect(ctx.destination);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + 1.55);
        osc2.stop(now + 1.55);

        this.ringtoneOscillators = [osc1, osc2];
      } catch (err) {
        console.warn('Could not play ringtone burst:', err);
      }
    };

    playBurst();
    this.ringtoneInterval = window.setInterval(playBurst, 3500);
  }

  /**
   * Stop any active ringtone.
   */
  public stopRingtone() {
    if (this.ringtoneInterval) {
      clearInterval(this.ringtoneInterval);
      this.ringtoneInterval = null;
    }
    if (this.ringtoneOscillators.length > 0) {
      try {
        this.ringtoneOscillators.forEach((osc) => osc.stop());
      } catch {
        // Ignore if already stopped
      }
      this.ringtoneOscillators = [];
    }
  }

  /**
   * Play polite telephonic call-end disconnect tone (three short beeps).
   */
  public playCallEndTone() {
    this.stopRingtone();
    const ctx = this.getAudioContext();
    const now = ctx.currentTime;

    const beepTimes = [0, 0.22, 0.44];
    beepTimes.forEach((offset) => {
      try {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(480, now + offset);

        gain.gain.setValueAtTime(0, now + offset);
        gain.gain.linearRampToValueAtTime(0.15, now + offset + 0.02);
        gain.gain.setValueAtTime(0.15, now + offset + 0.12);
        gain.gain.linearRampToValueAtTime(0, now + offset + 0.15);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + offset);
        osc.stop(now + offset + 0.16);
      } catch (err) {
        console.warn('Could not play call end tone:', err);
      }
    });
  }
}

export const audioSounds = new AudioSoundService();
