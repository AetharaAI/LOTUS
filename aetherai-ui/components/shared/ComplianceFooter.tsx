/**
 * Compliance Footer Component
 *
 * Displays DoD readiness and CMMC 2.0 compliance badges.
 */

'use client';

import Link from 'next/link';

interface ComplianceFooterProps {
  className?: string;
}

export function ComplianceFooter({ className = '' }: ComplianceFooterProps) {
  return (
    <footer
      className={`border-t border-aether-indigo-light bg-aether-bg-card ${className}`}
    >
      <div className="max-w-4xl mx-auto px-4 py-3">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
          {/* Compliance Badges */}
          <div className="flex items-center gap-3 flex-wrap justify-center md:justify-start">
            <span className="flex items-center gap-1.5 text-aether-text font-semibold">
              🇺🇸 100% US-Based Infrastructure
            </span>
            <span className="hidden md:inline text-aether-text-muted">|</span>
            <span className="flex items-center gap-1.5 text-aether-purple-light font-semibold">
              DoD-Ready
            </span>
            <span className="hidden md:inline text-aether-text-muted">|</span>
            <span className="flex items-center gap-1.5 text-aether-purple-light font-semibold">
              CMMC 2.0 Compliant
            </span>
          </div>

          {/* Compliance Link */}
          <Link
            href="/compliance"
            className="text-aether-text-muted hover:text-aether-purple-light transition-colors underline"
          >
            View Compliance Details →
          </Link>
        </div>

        {/* Additional Info */}
        <div className="mt-2 text-center md:text-left text-[10px] text-aether-text-muted">
          Your data never leaves US soil. All models hosted on CONUS infrastructure.
        </div>
      </div>
    </footer>
  );
}
