import React from 'react';

interface GoalCoachLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
  className?: string;
  onClick?: () => void;
  isClickable?: boolean;
}

export const GoalCoachLogo: React.FC<GoalCoachLogoProps> = ({
  size = 'md',
  showSubtitle = false,
  className = '',
  onClick,
  isClickable = true,
}) => {
  const iconSizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
  };

  const textSizes = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl',
  };

  return (
    <div
      onClick={onClick}
      className={`inline-flex items-center gap-2.5 select-none group ${
        isClickable || onClick ? 'cursor-pointer' : ''
      } ${className}`}
      title={isClickable ? 'Click to view profile & learning goals' : undefined}
    >
      {/* Fresh, Kawaii Chibi Panda Avatar */}
      <div
        className={`${iconSizes[size]} shrink-0 relative transition-transform duration-200 group-hover:scale-105 active:scale-95`}
      >
        <svg
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full filter drop-shadow-xs"
        >
          <defs>
            <linearGradient id="logoPandaHead" x1="32" y1="12" x2="32" y2="54" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="100%" stopColor="#f8fafc" />
            </linearGradient>
            <linearGradient id="logoEars" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#27272a" />
              <stop offset="100%" stopColor="#18181b" />
            </linearGradient>
            <radialGradient id="logoBlush" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#fda4af" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#fda4af" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Cute Round Ears */}
          <circle cx="16" cy="17" r="9.5" fill="url(#logoEars)" />
          <circle cx="16" cy="17" r="4.5" fill="#3f3f46" opacity="0.6" />
          <circle cx="48" cy="17" r="9.5" fill="url(#logoEars)" />
          <circle cx="48" cy="17" r="4.5" fill="#3f3f46" opacity="0.6" />

          {/* Soft Round Panda Head */}
          <rect
            x="9"
            y="15"
            width="46"
            height="42"
            rx="21"
            fill="url(#logoPandaHead)"
            stroke="#e2e8f0"
            strokeWidth="1.2"
          />

          {/* Eye Patches */}
          <ellipse cx="21" cy="32" rx="6.5" ry="8" fill="url(#logoEars)" transform="rotate(-15 21 32)" />
          <ellipse cx="43" cy="32" rx="6.5" ry="8" fill="url(#logoEars)" transform="rotate(15 43 32)" />

          {/* Sparkly Eyes */}
          <circle cx="21" cy="31" r="3.2" fill="#ffffff" />
          <circle cx="23" cy="33.5" r="1.3" fill="#ffffff" />
          <circle cx="43" cy="31" r="3.2" fill="#ffffff" />
          <circle cx="41" cy="33.5" r="1.3" fill="#ffffff" />

          {/* Rosy Cheeks */}
          <circle cx="14" cy="40" r="4" fill="url(#logoBlush)" />
          <circle cx="50" cy="40" r="4" fill="url(#logoBlush)" />

          {/* Little Button Nose */}
          <path d="M 30 38 C 30 36 34 36 34 38 C 34 40 30 40 30 38 Z" fill="#18181b" />

          {/* Sweet W-Smile */}
          <path
            d="M 29 42 Q 30.5 44 32 42 Q 33.5 44 35 42"
            stroke="#18181b"
            strokeWidth="1.8"
            strokeLinecap="round"
            fill="none"
          />

          {/* Little green bamboo leaf bud on head */}
          <path d="M 32 15 Q 31 10 32 8" stroke="#16a34a" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M 32 9 C 26 6 25 12 32 12 Z" fill="#4ade80" />
          <path d="M 32 8 C 37 6 38 11 32 11 Z" fill="#22c55e" />
        </svg>
      </div>

      {/* Brand Typography */}
      <div className="flex flex-col">
        <div
          className={`font-black tracking-tight text-zinc-900 ${textSizes[size]} leading-none flex items-center gap-1 group-hover:text-emerald-700 transition-colors`}
        >
          <span>Goal</span>
          <span className="text-emerald-600 font-extrabold">Coach</span>
          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded-md border border-emerald-200/60 ml-1 hidden sm:inline-block">
            HSK 1
          </span>
        </div>
        {showSubtitle && (
          <span className="text-[10px] font-semibold text-zinc-500 tracking-normal mt-0.5">
            Smart Adaptive Mandarin • HSK 1 Standard
          </span>
        )}
      </div>
    </div>
  );
};
