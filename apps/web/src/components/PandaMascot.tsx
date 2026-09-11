import React from 'react';

export type PandaMood = 'idle' | 'happy' | 'thinking' | 'cheering' | 'studying' | 'celebrating';

interface PandaMascotProps {
  mood?: PandaMood;
  size?: number;
  className?: string;
  speech?: string;
  showNameBadge?: boolean;
}

export const PandaMascot: React.FC<PandaMascotProps> = ({
  mood = 'idle',
  size = 120,
  className = '',
  speech,
  showNameBadge = false,
}) => {
  return (
    <div className={`inline-flex items-center gap-3 select-none ${className}`}>
      <div
        style={{ width: size, height: size }}
        className="relative shrink-0 transition-transform duration-300 hover:scale-105 filter drop-shadow-sm"
      >
        <svg
          viewBox="0 0 200 200"
          className="w-full h-full"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Soft gradients for modern kawaii look */}
            <linearGradient id="pandaBodyGrad" x1="100" y1="110" x2="100" y2="190" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="100%" stopColor="#f1f5f9" />
            </linearGradient>
            <linearGradient id="pandaBlackGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#27272a" />
              <stop offset="100%" stopColor="#18181b" />
            </linearGradient>
            <radialGradient id="blushGrad" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#fda4af" stopOpacity="0.85" />
              <stop offset="100%" stopColor="#fda4af" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="sproutGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4ade80" />
              <stop offset="100%" stopColor="#16a34a" />
            </linearGradient>
            <linearGradient id="goldGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#fde047" />
              <stop offset="100%" stopColor="#f59e0b" />
            </linearGradient>
          </defs>

          {/* Panda Round Fluffy Ears */}
          <g>
            {/* Left Ear */}
            <ellipse cx="50" cy="46" rx="28" ry="26" fill="url(#pandaBlackGrad)" transform="rotate(-12 50 46)" />
            <ellipse cx="52" cy="48" rx="14" ry="12" fill="#3f3f46" opacity="0.6" transform="rotate(-12 52 48)" />
            
            {/* Right Ear */}
            <ellipse cx="150" cy="46" rx="28" ry="26" fill="url(#pandaBlackGrad)" transform="rotate(12 150 46)" />
            <ellipse cx="148" cy="48" rx="14" ry="12" fill="#3f3f46" opacity="0.6" transform="rotate(12 148 48)" />
          </g>

          {/* Chubby Round Panda Body */}
          <path
            d="M 52 145 C 50 185 150 185 148 145 C 145 130 55 130 52 145 Z"
            fill="url(#pandaBodyGrad)"
            stroke="#e2e8f0"
            strokeWidth="1.5"
          />
          {/* Belly Shadow/Texture */}
          <ellipse cx="100" cy="165" rx="36" ry="18" fill="#e2e8f0" opacity="0.4" />

          {/* Little Cute Paws on Body */}
          {mood === 'cheering' || mood === 'celebrating' ? (
            <>
              {/* Arms raised in pure joy */}
              <ellipse cx="40" cy="115" rx="16" ry="22" fill="url(#pandaBlackGrad)" transform="rotate(-35 40 115)" />
              <ellipse cx="160" cy="115" rx="16" ry="22" fill="url(#pandaBlackGrad)" transform="rotate(35 160 115)" />
              {/* Pink paw pads */}
              <circle cx="34" cy="108" r="6" fill="#fb7185" />
              <circle cx="166" cy="108" r="6" fill="#fb7185" />
            </>
          ) : mood === 'thinking' ? (
            <>
              {/* One hand on hip, one paw on chin */}
              <ellipse cx="48" cy="148" rx="15" ry="18" fill="url(#pandaBlackGrad)" transform="rotate(20 48 148)" />
              <ellipse cx="125" cy="120" rx="15" ry="18" fill="url(#pandaBlackGrad)" transform="rotate(-25 125 120)" />
            </>
          ) : (
            <>
              {/* Natural cute resting paws */}
              <ellipse cx="48" cy="148" rx="16" ry="19" fill="url(#pandaBlackGrad)" transform="rotate(22 48 148)" />
              <ellipse cx="152" cy="148" rx="16" ry="19" fill="url(#pandaBlackGrad)" transform="rotate(-22 152 148)" />
            </>
          )}

          {/* Chubby Round Head */}
          <ellipse cx="100" cy="95" rx="66" ry="56" fill="url(#pandaBodyGrad)" stroke="#f1f5f9" strokeWidth="2" />

          {/* Kawaii Cute Eye Patches */}
          <ellipse cx="68" cy="90" rx="20" ry="24" fill="url(#pandaBlackGrad)" transform="rotate(-15 68 90)" />
          <ellipse cx="132" cy="90" rx="20" ry="24" fill="url(#pandaBlackGrad)" transform="rotate(15 132 90)" />

          {/* Cute Big Sparkling Eyes */}
          {mood === 'happy' || mood === 'celebrating' ? (
            <>
              {/* Joyful crescent eye arcs */}
              <path d="M 58 92 Q 68 80 78 92" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" />
              <path d="M 122 92 Q 132 80 142 92" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" />
            </>
          ) : (
            <>
              {/* Big Anime Eyes with Double Sparkles */}
              <circle cx="69" cy="90" r="10" fill="#0f172a" />
              <circle cx="131" cy="90" r="10" fill="#0f172a" />
              {/* Primary Highlight */}
              <circle cx="67" cy="87" r="4.5" fill="#ffffff" />
              <circle cx="129" cy="87" r="4.5" fill="#ffffff" />
              {/* Secondary Bottom Reflection */}
              <circle cx="72" cy="93" r="2.2" fill="#ffffff" opacity="0.9" />
              <circle cx="134" cy="93" r="2.2" fill="#ffffff" opacity="0.9" />
            </>
          )}

          {/* Soft Rosy Peach Blush Cheeks */}
          <circle cx="50" cy="110" r="14" fill="url(#blushGrad)" />
          <circle cx="150" cy="110" r="14" fill="url(#blushGrad)" />

          {/* Mini Cute Button Nose */}
          <path
            d="M 95 101 C 95 98 105 98 105 101 C 105 105 95 105 95 101 Z"
            fill="#18181b"
          />

          {/* Sweet Happy Mouth */}
          {mood === 'cheering' || mood === 'celebrating' ? (
            <path
              d="M 92 108 Q 100 120 108 108"
              fill="#f43f5e"
              stroke="#18181b"
              strokeWidth="2"
              strokeLinecap="round"
            />
          ) : mood === 'thinking' ? (
            <path
              d="M 96 110 Q 102 113 106 109"
              stroke="#18181b"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          ) : (
            <path
              d="M 93 108 Q 97 113 100 109 Q 103 113 107 108"
              fill="none"
              stroke="#18181b"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
          )}

          {/* Cute Mini Sprout (嫩竹芽) on Head */}
          <g transform="translate(100, 39)">
            {/* Sprout Stem */}
            <path d="M 0 0 Q -2 -14 0 -18" stroke="#16a34a" strokeWidth="3" strokeLinecap="round" fill="none" />
            {/* Left Leaf */}
            <path
              d="M 0 -16 C -12 -22 -14 -10 0 -8 Z"
              fill="url(#sproutGrad)"
            />
            {/* Right Tiny Bud Leaf */}
            <path
              d="M 0 -18 C 10 -22 12 -12 0 -10 Z"
              fill="url(#sproutGrad)"
            />
          </g>

          {/* Mood Special Accessories */}
          {mood === 'studying' && (
            // Cute round gold glasses
            <g>
              <circle cx="68" cy="90" r="18" fill="none" stroke="#d97706" strokeWidth="2.5" />
              <circle cx="132" cy="90" r="18" fill="none" stroke="#d97706" strokeWidth="2.5" />
              <path d="M 86 90 L 114 90" stroke="#d97706" strokeWidth="2.5" strokeLinecap="round" />
            </g>
          )}

          {mood === 'celebrating' && (
            // Shiny little crown on head
            <g transform="translate(100, 36)">
              <polygon points="-16,0 -20,-16 -8,-8 0,-20 8,-8 20,-16 16,0" fill="url(#goldGrad)" stroke="#d97706" strokeWidth="1.5" />
              <circle cx="-20" cy="-16" r="2.5" fill="#f43f5e" />
              <circle cx="0" cy="-20" r="3" fill="#3b82f6" />
              <circle cx="20" cy="-16" r="2.5" fill="#10b981" />
            </g>
          )}

          {mood === 'cheering' && (
            // Sparkling golden stars around
            <g>
              <path d="M 30 70 L 32 75 L 37 75 L 33 78 L 35 83 L 30 80 L 25 83 L 27 78 L 23 75 L 28 75 Z" fill="#fbbf24" />
              <path d="M 170 70 L 172 75 L 177 75 L 173 78 L 175 83 L 170 80 L 165 83 L 167 78 L 163 75 L 168 75 Z" fill="#fbbf24" />
            </g>
          )}
        </svg>
      </div>

      {/* Optional Speech Bubble */}
      {speech && (
        <div className="relative bg-white/95 backdrop-blur-xs border border-emerald-200/80 rounded-2xl px-3.5 py-2 text-xs font-semibold text-zinc-800 shadow-sm max-w-[210px] animate-in fade-in slide-in-from-left-2">
          {/* Triangle pointer */}
          <div className="absolute top-1/2 -left-2 -translate-y-1/2 w-0 h-0 border-t-6 border-t-transparent border-b-6 border-b-transparent border-r-8 border-r-white" />
          <div className="text-[10px] font-black text-emerald-600 uppercase tracking-wider mb-0.5">
            Coach Baobao
          </div>
          <div className="leading-snug text-zinc-700">{speech}</div>
        </div>
      )}

      {/* Name Badge */}
      {showNameBadge && !speech && (
        <div className="text-left">
          <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-[11px] font-black text-emerald-700">
            <span>🐼 Coach Baobao</span>
          </div>
        </div>
      )}
    </div>
  );
};
