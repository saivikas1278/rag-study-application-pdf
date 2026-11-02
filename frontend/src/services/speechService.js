/**
 * Speech Synthesis Service for AI PDF Study Assistant
 * Wraps browser-native Web Speech API with markdown stripping and playback control.
 */

class SpeechService {
  constructor() {
    this.synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    this.currentUtterance = null;
    this.isPlaying = false;
    this.voices = [];

    if (this.synth) {
      this.loadVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  loadVoices() {
    if (!this.synth) return;
    this.voices = this.synth.getVoices();
  }

  isSupported() {
    return Boolean(typeof window !== 'undefined' && 'speechSynthesis' in window);
  }

  /**
   * Cleans markdown formatting to create natural-sounding spoken audio.
   */
  cleanTextForSpeech(text) {
    if (!text) return '';
    return text
      .replace(/^#{1,6}\s+/gm, '') // Remove markdown headers
      .replace(/\*\*([^*]+)\*\*/g, '$1') // Bold to plain text
      .replace(/\*([^*]+)\*/g, '$1') // Italics to plain text
      .replace(/`([^`]+)`/g, '$1') // Inline code
      .replace(/^\s*[-*+]\s+/gm, '') // Unordered bullet dashes
      .replace(/^\s*\d+\.\s+/gm, '') // Numbered list prefixes
      .replace(/💡 Proactive Suggestions & Next Steps/gi, 'Here are some proactive suggestions and next steps.')
      .replace(/[\[\]]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * Speaks the given text using an available natural English voice.
   */
  speak(text, { onStart, onEnd, onError } = {}) {
    if (!this.isSupported()) {
      if (onError) onError(new Error('Web Speech API is not supported in this browser.'));
      return;
    }

    // Cancel any active utterance first
    this.stop();

    const cleanText = this.cleanTextForSpeech(text);
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    this.currentUtterance = utterance;

    // Select preferred natural voice if available
    if (this.voices.length === 0) {
      this.loadVoices();
    }
    const preferredVoice = this.voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        (v.name.includes('Google') ||
          v.name.includes('Natural') ||
          v.name.includes('Samantha') ||
          v.name.includes('Jenny') ||
          v.name.includes('Daniel'))
    ) || this.voices.find((v) => v.lang.startsWith('en'));

    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }

    utterance.rate = 1.0;
    utterance.pitch = 1.05; // Slightly warm/bright friendly tutor pitch

    utterance.onstart = () => {
      this.isPlaying = true;
      if (onStart) onStart();
    };

    utterance.onend = () => {
      this.isPlaying = false;
      this.currentUtterance = null;
      if (onEnd) onEnd();
    };

    utterance.onerror = (e) => {
      this.isPlaying = false;
      this.currentUtterance = null;
      if (onError) onError(e);
    };

    this.synth.speak(utterance);
  }

  stop() {
    if (this.synth) {
      this.synth.cancel();
    }
    this.isPlaying = false;
    this.currentUtterance = null;
  }

  isSpeaking() {
    return this.isPlaying;
  }
}

export const speechService = new SpeechService();
