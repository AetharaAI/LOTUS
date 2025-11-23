'use client';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  showText?: boolean;
}

export function Logo({ size = 'md', className = '', showText = true }: LogoProps) {
  const sizeClasses = {
    sm: 'h-8',
    md: 'h-12',
    lg: 'h-16',
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/logo.png"
        alt="AetherAI"
        className={`${sizeClasses[size]} w-auto`}
      />
      {showText && (
        <span className="text-xl font-bold bg-gradient-to-r from-aether-purple-light to-aether-orange bg-clip-text text-transparent">
          AetherAI
        </span>
      )}
    </div>
  );
}

export function LogoWithTagline({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-col items-center ${className}`}>
      <img src="/logo.png" alt="AetherAI" className="h-24 w-auto mb-4" />
      <h1 className="text-3xl font-bold bg-gradient-to-r from-aether-purple-light to-aether-orange bg-clip-text text-transparent">
        AetherAI
      </h1>
      <p className="text-aether-text-muted text-sm mt-2">
        The American Standard for Sovereign AI
      </p>
    </div>
  );
}
