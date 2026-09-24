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
    sm: 'w-10 h-10',
    md: 'w-12 h-12',
    lg: 'w-14 h-14',
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
      <div
        className={`${iconSizes[size]} shrink-0 relative transition-transform duration-200 group-hover:scale-105 active:scale-95`}
      >
        <svg
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="h-full w-full drop-shadow-sm"
        >
          <circle cx="17" cy="17" r="9" fill="#17201c" />
          <circle cx="47" cy="17" r="9" fill="#17201c" />
          <circle cx="32" cy="34" r="25" fill="#fff" stroke="#a7f3d0" strokeWidth="2" />
          <ellipse cx="21.5" cy="32" rx="6.5" ry="8" fill="#17201c" transform="rotate(18 21.5 32)" />
          <ellipse cx="42.5" cy="32" rx="6.5" ry="8" fill="#17201c" transform="rotate(-18 42.5 32)" />
          <circle cx="22" cy="31" r="2" fill="#fff" />
          <circle cx="42" cy="31" r="2" fill="#fff" />
          <ellipse cx="32" cy="40" rx="3.5" ry="2.7" fill="#17201c" />
          <path d="M32 42.5C29.5 46 27 44.5 27 44.5M32 42.5C34.5 46 37 44.5 37 44.5" stroke="#17201c" strokeWidth="1.8" strokeLinecap="round" />
          <path d="M39 9C43 3 50 5 50 5C49 11 45 14 39 13Z" fill="#22c55e" />
          <path d="M39 13L45 7" stroke="#15803d" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>

      {/* Brand Typography */}
      <div className="flex flex-col">
        <div
          className={`font-black tracking-tight text-zinc-900 ${textSizes[size]} leading-none flex items-center gap-1 group-hover:text-emerald-700 transition-colors`}
        >
          <span>Goal</span>
          <span className="text-emerald-600 font-extrabold">Coach</span>
        </div>
        {showSubtitle && (
          <span className="text-[10px] font-semibold text-zinc-500 tracking-normal mt-0.5">
            Your adaptive Mandarin coach
          </span>
        )}
      </div>
    </div>
  );
};
