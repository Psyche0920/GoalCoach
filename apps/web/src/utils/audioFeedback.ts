// Web Audio API Sound Synthesizer & High-Quality Natural Female TTS Manager for Language Learning

export const cleanPronunciationText = (text: string): string => {
  if (!text) return '';
  let str = text.trim();

  // If JSON array format string (e.g. '["我", "叫", "王朋"]')
  if (str.startsWith('[') && str.endsWith(']')) {
    try {
      const parsed = JSON.parse(str);
      if (Array.isArray(parsed)) str = parsed.join('');
    } catch {
      // ignore
    }
  }

  // Strip blanks (e.g. '____')
  str = str.replace(/_{2,}/g, '');

  // Strip dialogue speaker prefixes like 'A: ', 'B: ', 'A：', 'B：'
  str = str.replace(/^[AB][:：]\s*/gm, '');

  // Strip parenthetical translations or hints like （in front of） or (teacher)
  str = str.replace(/（[^）]+）|\([^)]+\)/g, '');

  // Strictly strip all punctuation marks and symbols (跳过标点符号，不朗读标点)
  str = str.replace(/[\p{P}\p{S}]+/gu, '');

  // Remove unnecessary inner whitespace
  return str.replace(/\s+/g, '').trim();
};

class AudioFeedbackManager {
  private ctx: AudioContext | null = null;
  private cachedVoice: SpeechSynthesisVoice | null = null;
  private currentAudio: HTMLAudioElement | null = null;

  constructor() {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = () => {
        this.cachedVoice = null;
        this.getChineseFemaleVoice();
      };
    }
  }

  private getAudioContext(): AudioContext | null {
    if (typeof window === 'undefined') return null;
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume().catch(() => {});
    }
    return this.ctx;
  }

  // Select best natural female voice for Chinese fallback
  private getChineseFemaleVoice(): SpeechSynthesisVoice | null {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null;
    if (this.cachedVoice) return this.cachedVoice;

    try {
      const voices = window.speechSynthesis.getVoices();
      if (!voices || voices.length === 0) return null;

      const zhVoices = voices.filter(v => v.lang === 'zh-CN' || v.lang === 'zh_CN' || v.lang.startsWith('zh'));

      // Preferred premium neural female voices
      const femaleKeywords = ['xiaoxiao', 'tingting', 'yaoyao', 'huihui', 'sinji', 'lili', 'female', '女', '普通话 (中国大陆)'];
      const bestFemale = zhVoices.find(v => {
        const lower = v.name.toLowerCase();
        return femaleKeywords.some(kw => lower.includes(kw));
      });

      if (bestFemale) {
        this.cachedVoice = bestFemale;
        return bestFemale;
      }

      if (zhVoices.length > 0) {
        this.cachedVoice = zhVoices[0];
        return zhVoices[0];
      }
    } catch {
      // ignore
    }
    return null;
  }

  // Immediately stop any currently playing speech audio or synth
  stopSpeech() {
    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
      } catch {
        // ignore
      }
      this.currentAudio = null;
    }

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // ignore
      }
    }
  }

  // Play a crisp pop/click sound when tapping tokens
  playPopSound() {
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(600, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.04);

      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.05);
    } catch (e) {
      console.warn('Audio effect error:', e);
    }
  }

  // Play a bright, cheerful Duolingo-style success chime (C5 -> E5 -> G5 chord)
  playSuccessSound() {
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;
      const notes = [
        { freq: 523.25, time: 0, duration: 0.12 },     // C5
        { freq: 659.25, time: 0.09, duration: 0.12 },  // E5
        { freq: 783.99, time: 0.18, duration: 0.35 },  // G5
        { freq: 1046.50, time: 0.24, duration: 0.4 },  // C6 sparkle
      ];

      notes.forEach(({ freq, time, duration }) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + time);

        gain.gain.setValueAtTime(0.18, now + time);
        gain.gain.exponentialRampToValueAtTime(0.001, now + time + duration);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + time);
        osc.stop(now + time + duration);
      });
    } catch (e) {
      console.warn('Success audio error:', e);
    }
  }

  // Play a gentle failure / try-again bonk sound (Eb4 -> C4 pitch slide)
  playFailureSound() {
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;

      const now = ctx.currentTime;

      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();

      osc1.type = 'sawtooth';
      osc1.frequency.setValueAtTime(329.63, now); // E4
      osc1.frequency.exponentialRampToValueAtTime(261.63, now + 0.22);

      gain1.gain.setValueAtTime(0.15, now);
      gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.25);

      osc1.connect(gain1);
      gain1.connect(ctx.destination);

      osc1.start(now);
      osc1.stop(now + 0.25);

      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();

      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(220, now + 0.12);
      osc2.frequency.exponentialRampToValueAtTime(174.61, now + 0.38);

      gain2.gain.setValueAtTime(0.2, now + 0.12);
      gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

      osc2.connect(gain2);
      gain2.connect(ctx.destination);

      osc2.start(now + 0.12);
      osc2.stop(now + 0.4);
    } catch (e) {
      console.warn('Failure audio error:', e);
    }
  }

  // Fallback to browser SpeechSynthesis if network / server TTS is unavailable
  private speakChineseWebSpeech(cleanedText: string, onEnd?: () => void) {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      if (onEnd) onEnd();
      return;
    }

    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanedText);
      utterance.lang = 'zh-CN';
      utterance.rate = 0.85; // Natural clear cadence
      utterance.pitch = 1.05; // Slightly higher, warm and friendly female pitch

      const femaleVoice = this.getChineseFemaleVoice();
      if (femaleVoice) {
        utterance.voice = femaleVoice;
      }

      if (onEnd) {
        utterance.onend = onEnd;
        utterance.onerror = onEnd;
      }

      window.speechSynthesis.speak(utterance);
    } catch {
      if (onEnd) onEnd();
    }
  }

  // Speak Chinese character or complete sentence using the best natural standard female voice
  speakChinese(text: string, onEnd?: () => void) {
    // 1. Strictly strip punctuation & clean text
    const cleaned = cleanPronunciationText(text);
    // If text is empty or contains no Chinese characters (e.g. English options), do not speak
    if (!cleaned || !/[\u4e00-\u9fa5]/.test(cleaned)) {
      if (onEnd) onEnd();
      return;
    }

    // 2. Stop any existing playback
    this.stopSpeech();

    // 3. Play high-quality natural female voice via server TTS
    try {
      const audioUrl = `/api/tts?text=${encodeURIComponent(cleaned)}`;
      const audio = new Audio(audioUrl);
      this.currentAudio = audio;

      audio.onended = () => {
        if (this.currentAudio === audio) {
          this.currentAudio = null;
        }
        if (onEnd) onEnd();
      };

      audio.onerror = () => {
        if (this.currentAudio === audio) {
          this.currentAudio = null;
        }
        // Fallback to local speech synth
        this.speakChineseWebSpeech(cleaned, onEnd);
      };

      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // In case audio playback is blocked, fallback
          this.speakChineseWebSpeech(cleaned, onEnd);
        });
      }
    } catch {
      this.speakChineseWebSpeech(cleaned, onEnd);
    }
  }

  // Play Feedback Sound (Success or Failure) and then pronounce the complete correct sentence
  playGradingFeedbackAndSentence(passed: boolean, fullCorrectSentence: string) {
    if (passed) {
      this.playSuccessSound();
    } else {
      this.playFailureSound();
    }

    // After the chime/bonk completes (~380ms), automatically read the FULL complete sentence
    setTimeout(() => {
      this.speakChinese(fullCorrectSentence);
    }, 380);
  }
}

export const audioFeedback = new AudioFeedbackManager();
