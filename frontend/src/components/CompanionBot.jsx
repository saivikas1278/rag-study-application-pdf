import React, { useState } from 'react';

/**
 * Sparky the Study Droid - Pure SVG/CSS Vector Animated Mascot
 * Supports 6 distinct animated mood states:
 * - idle: gentle levitation hover, natural LED blinks
 * - thinking: radar sweep on visor, pulsating antenna
 * - speaking: soundwave equalizer mouth waves
 * - eureka: glowing golden star eyes, illuminated antenna
 * - puzzled: tilted questioning eye and floating '?'
 * - celebrating: happy arc eyes, joyful bounce, confetti sparkles
 */
export default function CompanionBot({
  mood = 'idle',
  size = 'md',
  showBubble = false,
  bubbleText = '',
  bubbleAlign = 'center',
  interactive = true,
  onClick = null,
  className = ''
}) {
  const [isHovered, setIsHovered] = useState(false);
  const [clickedBounce, setClickedBounce] = useState(false);

  const handleClick = (e) => {
    if (interactive) {
      setClickedBounce(true);
      setTimeout(() => setClickedBounce(false), 600);
      if (onClick) onClick(e);
    }
  };

  // Dimensions based on size preset
  const sizeMap = {
    sm: { width: 32, height: 36, scale: 0.4 },
    md: { width: 56, height: 64, scale: 0.7 },
    lg: { width: 88, height: 100, scale: 1.1 },
    xl: { width: 120, height: 136, scale: 1.5 }
  };

  const currentSize = sizeMap[size] || sizeMap.md;

  // Active animation classes based on mood
  const getContainerAnimation = () => {
    if (clickedBounce) return 'scale-110 -translate-y-2 transition-transform duration-200';
    if (mood === 'celebrating') return 'animate-celebrate-bounce';
    if (mood === 'thinking') return 'animate-bot-hover-fast';
    return 'animate-bot-hover';
  };

  return (
    <div 
      className={`relative inline-flex flex-col items-center select-none ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Dynamic Speech Bubble */}
      {(showBubble || (isHovered && bubbleText)) && bubbleText && (
        <div 
          className={`absolute -top-12 z-30 pointer-events-none animate-fadeIn ${
            bubbleAlign === 'right' 
              ? 'right-0 left-auto translate-x-0' 
              : 'left-1/2 -translate-x-1/2'
          }`}
        >
          <div className="relative px-3 py-1.5 rounded-xl bg-slate-900 text-white text-[11px] font-medium shadow-md flex items-center gap-1.5 border border-slate-700 max-w-[210px] sm:max-w-[250px] whitespace-normal leading-snug text-left">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse shrink-0" />
            <span className="line-clamp-2">{bubbleText}</span>
            {/* Speech bubble arrow pointer */}
            <div 
              className={`absolute top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-slate-900 ${
                bubbleAlign === 'right'
                  ? 'right-5 left-auto'
                  : 'left-1/2 -translate-x-1/2'
              }`} 
            />
          </div>
        </div>
      )}

      {/* Floating Sparkles for Eureka / Celebrating */}
      {(mood === 'eureka' || mood === 'celebrating') && (
        <div className="absolute -top-3 inset-x-0 flex justify-between pointer-events-none z-20">
          <span className="text-amber-400 text-xs animate-float-particle">✦</span>
          <span className="text-teal-400 text-[10px] animate-float-particle [animation-delay:0.3s]">★</span>
          <span className="text-emerald-400 text-xs animate-float-particle [animation-delay:0.7s]">✦</span>
        </div>
      )}

      {/* SVG Vector Droid */}
      <div 
        onClick={handleClick}
        className={`relative cursor-pointer transition-transform duration-200 ${getContainerAnimation()}`}
        style={{ width: currentSize.width, height: currentSize.height }}
        title="Sparky - AI Study Droid"
        role="img"
        aria-label={`Study Droid mood: ${mood}`}
      >
        <svg
          viewBox="0 0 100 114"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full drop-shadow-xs"
        >
          {/* DEFINITIONS & GRADIENTS */}
          <defs>
            {/* Chassis Body Gradient */}
            <linearGradient id="chassisGrad" x1="20" y1="20" x2="80" y2="90" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#FFFFFF" />
              <stop offset="45%" stopColor="#F1F5F9" />
              <stop offset="100%" stopColor="#E2E8F0" />
            </linearGradient>

            {/* Dark Visor Screen */}
            <linearGradient id="visorGrad" x1="24" y1="36" x2="76" y2="68" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#090D16" />
              <stop offset="100%" stopColor="#0F172A" />
            </linearGradient>

            {/* Cyan Thruster Flame */}
            <radialGradient id="thrusterGrad" cx="50" cy="94" r="16" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.9" />
              <stop offset="50%" stopColor="#0D9488" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#0D9488" stopOpacity="0" />
            </radialGradient>

            {/* Golden Star Gradient for Eureka */}
            <linearGradient id="goldStarGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#FDE047" />
              <stop offset="100%" stopColor="#F59E0B" />
            </linearGradient>
          </defs>

          {/* 1. THRUSTER PLASMA GLOW */}
          <ellipse cx="50" cy="97" rx="14" ry="7" fill="url(#thrusterGrad)" className="animate-pulse" />
          <ellipse cx="50" cy="95" rx="7" ry="3.5" fill="#5EEAD4" />

          {/* 2. ANTENNA */}
          <path d="M50 20 L50 8" stroke="#94A3B8" strokeWidth="3" strokeLinecap="round" />
          {/* Antenna Glowing Tip */}
          <circle
            cx="50"
            cy="7"
            r="4.5"
            fill={
              mood === 'eureka'
                ? '#F59E0B'
                : mood === 'thinking'
                ? '#14B8A6'
                : '#0D9488'
            }
            className={mood === 'thinking' || mood === 'eureka' ? 'animate-antenna-pulse' : ''}
          />
          {mood === 'eureka' && (
            <circle cx="50" cy="7" r="8" fill="#F59E0B" fillOpacity="0.3" className="animate-ping" />
          )}

          {/* 3. HEAD / CHASSIS */}
          <rect
            x="18"
            y="20"
            width="64"
            height="58"
            rx="24"
            fill="url(#chassisGrad)"
            stroke="#CBD5E1"
            strokeWidth="2.5"
          />

          {/* Subtle Chassis Gloss Highlight */}
          <path
            d="M26 25 Q50 21 74 25"
            stroke="#FFFFFF"
            strokeWidth="2"
            strokeLinecap="round"
            strokeOpacity="0.9"
          />

          {/* 4. SIDE CYBER EARS */}
          {/* Left Ear */}
          <rect x="12" y="38" width="6" height="22" rx="3" fill="#94A3B8" />
          <circle cx="15" cy="49" r="2" fill="#0D9488" />
          {/* Right Ear */}
          <rect x="82" y="38" width="6" height="22" rx="3" fill="#94A3B8" />
          <circle cx="85" cy="49" r="2" fill="#0D9488" />

          {/* 5. VISOR SCREEN */}
          <rect
            x="24"
            y="32"
            width="52"
            height="34"
            rx="14"
            fill="url(#visorGrad)"
            stroke="#334155"
            strokeWidth="1.5"
          />

          {/* 6. DYNAMIC FACIAL EXPRESSIONS ON VISOR */}

          {/* === A. IDLE MOOD: Calm Glowing Cyan Eyes with Blinks === */}
          {mood === 'idle' && (
            <g className="animate-eye-blink">
              {/* Left Eye */}
              <rect x="34" y="44" width="9" height="11" rx="4.5" fill="#2DD4BF" />
              <circle cx="36.5" cy="46.5" r="1.5" fill="#FFFFFF" />
              {/* Right Eye */}
              <rect x="57" y="44" width="9" height="11" rx="4.5" fill="#2DD4BF" />
              <circle cx="59.5" cy="46.5" r="1.5" fill="#FFFFFF" />
              {/* Subtle smile line */}
              <path d="M46 56 Q50 58 54 56" stroke="#2DD4BF" strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
            </g>
          )}

          {/* === B. THINKING MOOD: Circular Radar Sweep Visor === */}
          {mood === 'thinking' && (
            <g>
              {/* Outer Radar Ring */}
              <circle cx="50" cy="49" r="11" stroke="#0D9488" strokeWidth="1" strokeDasharray="2 2" />
              {/* Radar Sweeping Beam */}
              <g className="animate-radar-sweep" style={{ transformOrigin: '50px 49px' }}>
                <line x1="50" y1="49" x2="61" y2="49" stroke="#5EEAD4" strokeWidth="2" strokeLinecap="round" />
                <circle cx="50" cy="49" r="2.5" fill="#5EEAD4" />
              </g>
              {/* Small scanning nodes */}
              <circle cx="43" cy="45" r="1.5" fill="#14B8A6" className="animate-ping" />
              <circle cx="57" cy="52" r="1" fill="#2DD4BF" />
            </g>
          )}

          {/* === C. SPEAKING MOOD: Voice Waveform Equalizer Visor === */}
          {mood === 'speaking' && (
            <g>
              {/* Attentive Eyes */}
              <circle cx="38" cy="42" r="3.5" fill="#2DD4BF" />
              <circle cx="62" cy="42" r="3.5" fill="#2DD4BF" />

              {/* Animated Soundwave Equalizer Bars */}
              <g transform="translate(50, 54)">
                {/* Bar 1 */}
                <rect x="-12" y="-5" width="3" height="10" rx="1.5" fill="#5EEAD4" className="animate-mouth-wave-1" />
                {/* Bar 2 */}
                <rect x="-6" y="-7" width="3" height="14" rx="1.5" fill="#2DD4BF" className="animate-mouth-wave-2" />
                {/* Center Bar */}
                <rect x="-1.5" y="-8" width="3" height="16" rx="1.5" fill="#FFFFFF" className="animate-mouth-wave-3" />
                {/* Bar 4 */}
                <rect x="3" y="-7" width="3" height="14" rx="1.5" fill="#2DD4BF" className="animate-mouth-wave-1" />
                {/* Bar 5 */}
                <rect x="9" y="-5" width="3" height="10" rx="1.5" fill="#5EEAD4" className="animate-mouth-wave-2" />
              </g>
            </g>
          )}

          {/* === D. EUREKA / SUGGESTIONS MOOD: Radiant Star Eyes === */}
          {mood === 'eureka' && (
            <g>
              {/* Left Star Eye */}
              <path
                d="M38 41 L40 46 L45 48 L40 50 L38 55 L36 50 L31 48 L36 46 Z"
                fill="url(#goldStarGrad)"
              />
              {/* Right Star Eye */}
              <path
                d="M62 41 L64 46 L69 48 L64 50 L62 55 L60 50 L55 48 L60 46 Z"
                fill="url(#goldStarGrad)"
              />
              {/* Wide Happy Mouth */}
              <path d="M44 56 Q50 62 56 56" stroke="#FDE047" strokeWidth="2" strokeLinecap="round" fill="none" />
            </g>
          )}

          {/* === E. PUZZLED / LOW-CONTEXT MOOD: Questioning Eye & Floating '?' === */}
          {mood === 'puzzled' && (
            <g>
              {/* Left Inquisitive Big Eye */}
              <ellipse cx="37" cy="48" rx="5" ry="6" fill="#2DD4BF" />
              <circle cx="39" cy="46" r="1.5" fill="#FFFFFF" />
              {/* Right Squinting Slanted Eye */}
              <line x1="57" y1="47" x2="65" y2="50" stroke="#2DD4BF" strokeWidth="3" strokeLinecap="round" />
              {/* Floating Question Mark inside screen */}
              <text x="47" y="44" fill="#F59E0B" fontSize="10" fontWeight="bold" fontFamily="sans-serif">?</text>
              {/* Wavy Puzzled Mouth */}
              <path d="M45 57 Q48 55 51 57 Q54 59 56 57" stroke="#2DD4BF" strokeWidth="1.5" strokeLinecap="round" fill="none" />
            </g>
          )}

          {/* === F. CELEBRATING MOOD: Curved Arc Eyes and Joyful Grin === */}
          {mood === 'celebrating' && (
            <g>
              {/* Left Happy Curved Arc */}
              <path d="M33 49 Q38 42 43 49" stroke="#5EEAD4" strokeWidth="3" strokeLinecap="round" fill="none" />
              {/* Right Happy Curved Arc */}
              <path d="M57 49 Q62 42 67 49" stroke="#5EEAD4" strokeWidth="3" strokeLinecap="round" fill="none" />
              {/* Big Joyful Smile */}
              <path d="M44 55 Q50 63 56 55" stroke="#2DD4BF" strokeWidth="2.5" strokeLinecap="round" fill="#0D9488" />
              {/* Rosy Cheeks */}
              <ellipse cx="31" cy="53" rx="2.5" ry="1.5" fill="#F472B6" opacity="0.8" />
              <ellipse cx="69" cy="53" rx="2.5" ry="1.5" fill="#F472B6" opacity="0.8" />
            </g>
          )}

          {/* 7. LOWER CHASSIS BELT & STATUS LIGHT */}
          <rect x="36" y="80" width="28" height="6" rx="3" fill="#E2E8F0" stroke="#CBD5E1" strokeWidth="1" />
          <circle
            cx="50"
            cy="83"
            r="2"
            fill={mood === 'thinking' ? '#14B8A6' : mood === 'eureka' ? '#F59E0B' : '#0D9488'}
          />
        </svg>
      </div>
    </div>
  );
}
