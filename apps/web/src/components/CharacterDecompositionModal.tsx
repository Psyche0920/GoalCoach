import React from 'react';
import { Volume2, X, Sparkles, BookOpen } from 'lucide-react';
import { CharacterEntry, ComponentDecomposition } from '../data/characterRadicals.ts';

interface CharacterDecompositionModalProps {
  entry: CharacterEntry;
  onClose: () => void;
  onPlayAudio?: (text: string) => void;
}

export const CharacterDecompositionModal: React.FC<CharacterDecompositionModalProps> = ({
  entry,
  onClose,
  onPlayAudio,
}) => {
  const handleAudio = () => {
    if (onPlayAudio) {
      onPlayAudio(entry.text);
    } else if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(entry.text);
      u.lang = 'zh-CN';
      u.rate = 0.85;
      window.speechSynthesis.speak(u);
    }
  };

  // Helper to render component sub-tree (matching HelloChinese tree layout in Image 1)
  const renderTreeBranches = (components: ComponentDecomposition[], level = 1) => {
    return (
      <div className="pl-4 border-l border-zinc-700/80 space-y-2 mt-1.5 ml-2">
        {components.map((comp, idx) => (
          <div key={`${comp.char}-${idx}`} className="text-xs space-y-0.5">
            <div className="flex items-center gap-2">
              <span className="text-zinc-500 font-mono text-[11px]">├──</span>
              <span className="font-chinese font-black text-amber-300 text-sm bg-zinc-800/80 px-1.5 py-0.5 rounded border border-zinc-700">
                {comp.char}
              </span>
              <span className="text-zinc-300 font-medium">{comp.meaningEn}</span>
            </div>
            {comp.radicalOrigin && (
              <p className="text-[10px] text-zinc-400 pl-6 italic">
                {comp.radicalOrigin}
              </p>
            )}
            {comp.components && comp.components.length > 0 && renderTreeBranches(comp.components, level + 1)}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150 select-none"
      onClick={onClose}
    >
      <div 
        className="relative bg-zinc-900 text-white rounded-3xl max-w-sm w-full p-5 border-2 border-zinc-700 shadow-2xl space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header matching HelloChinese Popover in Image 1 */}
        <div className="flex items-start justify-between">
          <div className="space-y-0.5">
            {/* Pinyin */}
            <div className="text-sm font-mono font-black text-indigo-300 tracking-wide">
              {entry.pinyin}
            </div>

            {/* Chinese Word + POS Badge */}
            <div className="flex items-center gap-3">
              <h3 className="text-3xl font-black font-chinese tracking-tight text-white">
                {entry.text}
              </h3>
              <span className="text-[11px] font-mono font-bold bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded border border-zinc-700">
                {entry.partOfSpeech}
              </span>
              <button
                onClick={handleAudio}
                className="p-1.5 rounded-full bg-zinc-800 hover:bg-zinc-700 text-indigo-300 transition-colors cursor-pointer"
                title="Pronounce"
              >
                <Volume2 className="w-4 h-4" />
              </button>
            </div>

            {/* English Main Meaning */}
            <div className="text-sm font-bold text-zinc-200 pt-0.5">
              {entry.meaningEn}
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-xl transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Divider */}
        <div className="h-px bg-zinc-800 w-full" />

        {/* Character Radical & Component Decomposition Tree (Image 1 Feature) */}
        <div className="space-y-3">
          <div className="text-[11px] font-black uppercase text-zinc-400 tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>汉字偏旁与结构解构 (Radical Breakdown)</span>
          </div>

          <div className="space-y-3 bg-zinc-950/60 rounded-2xl p-3.5 border border-zinc-800">
            {entry.breakdown.map((item, idx) => (
              <div key={`${item.char}-${idx}`} className="space-y-1">
                {/* Character Level */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-chinese font-black text-xl text-white">
                      {item.char}
                    </span>
                    {item.pinyin && (
                      <span className="text-[11px] font-mono text-indigo-300 font-bold">
                        {item.pinyin}
                      </span>
                    )}
                    <span className="text-xs font-bold text-zinc-300">
                      {item.meaningEn}
                    </span>
                  </div>
                </div>

                {item.radicalOrigin && (
                  <p className="text-[11px] text-zinc-400 italic pl-1 leading-relaxed">
                    💡 {item.radicalOrigin}
                  </p>
                )}

                {/* Sub-components / Radicals Tree */}
                {item.components && item.components.length > 0 && (
                  renderTreeBranches(item.components)
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Mnemonic Story / Memory Anchor */}
        {entry.mnemonicStory && (
          <div className="bg-indigo-950/40 border border-indigo-800/50 rounded-2xl p-3 text-xs text-indigo-200 flex items-start gap-2">
            <BookOpen className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-black text-indigo-300">会意拆字象形速记：</span>
              <span className="text-zinc-300">{entry.mnemonicStory}</span>
            </div>
          </div>
        )}

        {/* Footer tip */}
        <div className="text-center pt-1">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold text-zinc-200 transition-colors cursor-pointer"
          >
            知道了 (Got it)
          </button>
        </div>
      </div>
    </div>
  );
};
