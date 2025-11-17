/**
 * AetherAI Logo
 *
 * CRITICAL: Logo MUST always pulse - never static!
 * Purple gradient with electrical current effect.
 */

interface LogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export function Logo({ size = 'lg', className = '' }: LogoProps) {
  const sizeClasses = {
    sm: 'text-xl',
    md: 'text-2xl',
    lg: 'text-4xl',
    xl: 'text-5xl',
  };

  return (
    <div className={`${sizeClasses[size]} ${className}`}>
      <h1 className="font-bold text-gradient-aether animate-pulse-glow">
        AetherAI
      </h1>
    </div>
  );
}

/**
 * Logo with tagline
 */
export function LogoWithTagline() {
  return (
    <div className="flex flex-col items-center gap-2">
      <Logo size="xl" />
      <p className="text-sm text-aether-text-muted text-center">
        The American Standard for Sovereign AI
      </p>
    </div>
  );
}

/**
 * Compact logo for sidebar
 */
export function LogoCompact() {
  return (
    <div className="flex items-center gap-3">
      <Logo size="md" />
      <span className="text-xs text-aether-text-muted">🇺🇸</span>
    </div>
  );
}
