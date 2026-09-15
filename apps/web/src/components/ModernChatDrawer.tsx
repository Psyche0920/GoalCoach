import React, { useState, useRef, useEffect } from 'react';
import { 
  X, 
  Send, 
  Sparkles, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX,
  MessageSquare, 
  Radio, 
  Award,
  GraduationCap,
  RotateCcw,
  BookOpen,
  CheckCircle2,
  Lightbulb
} from 'lucide-react';
import { PandaMascot } from './PandaMascot.tsx';
import { audioFeedback } from '../utils/audioFeedback.ts';

interface ModernChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  context?: {
    learnerId?: string;
    conceptId?: string;
    currentGoal?: string;
    activePlanItems?: string[];
    errorCount?: number;
  };
}

interface TeachingAction {
  actionType?: 'explain' | 'ask' | 'hint' | 'remediate';
  action_type?: 'explain' | 'ask' | 'hint' | 'remediate';
  content: string;
  expectedResponse?: boolean;
  expected_response?: boolean;
  exercise?: { prompt: string } | null;
}

interface TeachingStepResponse {
  session: { id: string; status: string };
  action?: TeachingAction | null;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  correctionNote?: string;
}

const STORAGE_KEY = 'goalcoach_teaching_history_v1';

export const ModernChatDrawer: React.FC<ModernChatDrawerProps> = ({
  isOpen,
  onClose,
  context,
}) => {
  // Load saved chat messages or use welcoming introductory greeting
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      // Ignore parse error
    }
    return [
      {
        role: 'assistant',
        content:
          "Hi! I'm Coach Baobao, your personal Chinese tutor. 🐼✨\nFeel free to ask me anything in English or practice basic Mandarin! You can ask about grammar rules, pinyin tones, or practice simple dialogues.",
      },
    ];
  });

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [awaitingAnswer, setAwaitingAnswer] = useState(false);
  const [canAdvance, setCanAdvance] = useState(false);
  
  // Voice / Audio Mode
  const [interactionMode, setInteractionMode] = useState<'text' | 'voice'>('text');
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  // Sync to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    } catch (e) {
      // Ignore
    }
  }, [messages]);

  const applyTeachingStep = (step: TeachingStepResponse) => {
    setSessionId(step.session.id);
    const action = step.action;
    if (!action) {
      setAwaitingAnswer(false);
      setCanAdvance(false);
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: `Session ended: ${step.session.status}` },
      ]);
      return;
    }
    const actionType = action.actionType ?? action.action_type;
    const expectedResponse = action.expectedResponse ?? action.expected_response ?? false;
    if (!actionType) {
      throw new Error('Teaching API returned an action without action_type.');
    }
    const prompt = action.exercise?.prompt ? `\n\n${action.exercise.prompt}` : '';
    const content = `[${actionType.toUpperCase()}]\n${action.content}${prompt}`;
    setMessages((current) => [...current, { role: 'assistant', content }]);
    setAwaitingAnswer(expectedResponse);
    setCanAdvance(!expectedResponse && step.session.status === 'active');
    if (interactionMode === 'voice') speakText(content);
  };

  useEffect(() => {
    if (!isOpen || sessionId || isLoading) return;
    const startSession = async () => {
      setIsLoading(true);
      try {
        const response = await fetch('/api/v1/teaching/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            learnerId: context?.learnerId ?? 'learner_001',
            conceptId: context?.conceptId ?? 'hsk1_c20',
          }),
        });
        if (!response.ok) throw new Error(`Failed to start session (${response.status})`);
        applyTeachingStep(await response.json());
      } catch (error) {
        console.error('Unable to start teaching session:', error);
        setMessages((current) => [
          ...current,
          { role: 'assistant', content: 'Unable to start the teaching session. Please try again.' },
        ]);
      } finally {
        setIsLoading(false);
      }
    };
    void startSession();
  }, [isOpen, sessionId, context?.learnerId, context?.conceptId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Web Speech Recognition Initialization with sandbox fallback
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition();
        recognition.lang = 'zh-CN';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onresult = (event: any) => {
          const transcript = event.results[0]?.[0]?.transcript;
          if (transcript) {
            setInput(transcript);
            handleSend(transcript);
          }
          setIsRecording(false);
        };

        recognition.onerror = (err: any) => {
          console.warn('Speech recognition notice:', err?.error);
          setIsRecording(false);
          setVoiceNotice('Microphone access restricted in this iframe. Try clicking one of the quick speaking prompts below!');
          setTimeout(() => setVoiceNotice(null), 4000);
        };

        recognition.onend = () => {
          setIsRecording(false);
        };

        recognitionRef.current = recognition;
      } catch (err) {
        console.warn('SpeechRecognition init error:', err);
      }
    }
  }, []);

  if (!isOpen) return null;

  // Speak Chinese text aloud using SpeechSynthesis
  const speakText = (text: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      // Clean markdown tags for natural speech
      const clean = text.replace(/[*_#`]/g, '').trim();
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.lang = 'zh-CN';
      utterance.rate = 0.9;
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  const stopSpeaking = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      setVoiceNotice('Voice recognition is not supported in this browser. You can click any quick voice prompt below!');
      setTimeout(() => setVoiceNotice(null), 4000);
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (err) {
        setIsRecording(false);
        setVoiceNotice('Unable to start mic. Click any speaking prompt below instead!');
        setTimeout(() => setVoiceNotice(null), 3500);
      }
    }
  };

  const handleClearHistory = () => {
    const initial: Message[] = [
      {
        role: 'assistant',
        content:
          "Chat history cleared! Ask a question or pick a topic below to start practicing.",
      },
    ];
    setMessages(initial);
    setSessionId(null);
    setAwaitingAnswer(false);
    setCanAdvance(false);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(initial));
    } catch (e) {}
  };

  const handleSend = async (userText?: string) => {
    const textToSend = userText || input;
    if (!textToSend.trim() || isLoading || !sessionId || !awaitingAnswer) return;

    const newMessages: Message[] = [...messages, { role: 'user', content: textToSend }];
    setMessages(newMessages);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch(`/api/v1/teaching/sessions/${sessionId}/answers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answer: textToSend,
        }),
      });

      if (res.ok) {
        applyTeachingStep(await res.json());
      } else {
        throw new Error('Server returned non-200');
      }
    } catch (err) {
      console.error('Answer submission failed:', err);
      setMessages([...newMessages, { role: 'assistant', content: 'Answer submission failed. Please retry.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAdvance = async () => {
    if (!sessionId || !canAdvance || isLoading) return;
    setIsLoading(true);
    try {
      const response = await fetch(`/api/v1/teaching/sessions/${sessionId}/next`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error(`Failed to advance session (${response.status})`);
      applyTeachingStep(await response.json());
    } catch (error) {
      console.error('Unable to advance teaching session:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Beginner Quick Practice Prompts
  const quickPrompts = ['她会说汉语。', '我能说一点儿汉语。'];

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-zinc-950/40 backdrop-blur-xs select-none animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-md h-full shadow-2xl flex flex-col border-l-2 border-zinc-950 animate-in slide-in-from-right duration-300">
        {/* Header with Coach Baobao & Reset Button */}
        <div className="px-5 py-4 border-b-2 border-zinc-200 bg-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <PandaMascot mood="cheering" size={46} />
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-base font-black text-zinc-950">Coach Bǎobao</h3>
                <span className="text-[10px] font-black bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                  30y SLA Expert
                </span>
              </div>
              <p className="text-xs font-bold text-zinc-400">
                Corrects first · Links to concepts · HSK 1
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleClearHistory}
              className="p-2 text-zinc-400 hover:text-zinc-700 rounded-xl hover:bg-zinc-100 transition-colors"
              title="Reset Conversation History"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-zinc-900 rounded-xl hover:bg-zinc-100 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Mode Switch: Text vs Voice */}
        <div className="px-5 py-2.5 bg-zinc-50 border-b border-zinc-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setInteractionMode('text');
                stopSpeaking();
              }}
              className={`px-3 py-1 rounded-xl text-xs font-black transition-all ${
                interactionMode === 'text'
                  ? 'bg-white text-zinc-900 shadow-xs border border-zinc-200'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              Text Mode
            </button>
            <button
              onClick={() => setInteractionMode('voice')}
              className={`flex items-center gap-1 px-3 py-1 rounded-xl text-xs font-black transition-all ${
                interactionMode === 'voice'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Voice / TTS</span>
            </button>
          </div>

          {isSpeaking && (
            <button
              onClick={stopSpeaking}
              className="flex items-center gap-1 text-[11px] font-bold text-rose-600 hover:underline"
            >
              <VolumeX className="w-3.5 h-3.5" />
              <span>Stop Speaking</span>
            </button>
          )}
        </div>

        {/* Voice Notice Alert if Mic permission is restricted */}
        {voiceNotice && (
          <div className="mx-4 mt-2 p-2.5 bg-amber-50 border border-amber-200 rounded-xl text-[11px] font-bold text-amber-900 flex items-center gap-1.5 animate-in fade-in">
            <Lightbulb className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{voiceNotice}</span>
          </div>
        )}

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[88%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-emerald-600 text-white font-bold rounded-tr-xs shadow-xs'
                    : 'bg-zinc-100 text-zinc-800 font-medium rounded-tl-xs border border-zinc-200'
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>

                {/* Speak button on assistant responses */}
                {m.role === 'assistant' && (
                  <div className="mt-2 pt-2 border-t border-zinc-200 flex items-center justify-between">
                    <button
                      onClick={() => speakText(m.content)}
                      className="flex items-center gap-1 text-[10px] font-black text-emerald-700 hover:text-emerald-900"
                    >
                      <Volume2 className="w-3 h-3" />
                      <span>Play Pronunciation</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-start gap-2">
              <PandaMascot mood="thinking" size={32} />
              <div className="bg-zinc-100 rounded-2xl px-4 py-3 border border-zinc-200 text-xs font-bold text-zinc-500 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" />
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.2s]" />
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce [animation-delay:0.4s]" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggested answers */}
        {awaitingAnswer && <div className="px-5 py-2 border-t border-zinc-100 bg-zinc-50 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          <span className="text-[10px] font-black text-zinc-400 shrink-0">Try:</span>
          {quickPrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => handleSend(p)}
              className="shrink-0 px-2.5 py-1 bg-white hover:bg-zinc-200 border border-zinc-300 rounded-lg text-[11px] font-bold text-zinc-700 active:scale-95 transition-all"
            >
              {p}
            </button>
          ))}
        </div>}

        {canAdvance && (
          <div className="px-5 py-3 border-t border-zinc-100 bg-zinc-50">
            <button
              type="button"
              onClick={handleAdvance}
              disabled={isLoading}
              className="w-full px-4 py-2.5 bg-emerald-500 text-zinc-950 rounded-xl border-2 border-zinc-950 text-xs font-black disabled:opacity-50"
            >
              Continue
            </button>
          </div>
        )}

        {/* Input Bar */}
        <div className="p-4 border-t-2 border-zinc-200 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            {/* Voice Mic Toggle */}
            <button
              type="button"
              onClick={toggleRecording}
              className={`p-3 rounded-2xl border-2 transition-all shrink-0 cursor-pointer ${
                isRecording
                  ? 'bg-rose-500 border-zinc-950 text-white shadow-[0_2px_0_#9f1239] animate-pulse'
                  : 'bg-zinc-100 border-zinc-200 text-zinc-600 hover:bg-zinc-200'
              }`}
              title={isRecording ? 'Listening... click to send' : 'Click to speak Chinese'}
            >
              {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>

            <input
              type="text"
              disabled={!awaitingAnswer}
              placeholder={
                awaitingAnswer
                  ? isRecording ? 'Listening in Chinese...' : 'Type your answer...'
                  : 'Continue to the next teaching action'
              }
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 px-4 py-3 bg-zinc-50 border-2 border-zinc-200 focus:border-emerald-600 rounded-2xl text-xs font-bold focus:outline-none transition-all"
            />

            <button
              type="submit"
              disabled={!input.trim() || isLoading || !awaitingAnswer}
              className="p-3 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-zinc-950 rounded-2xl border-2 border-zinc-950 font-black shadow-[0_2px_0_#15803d] active:translate-y-0.5 active:shadow-none transition-all shrink-0 cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
