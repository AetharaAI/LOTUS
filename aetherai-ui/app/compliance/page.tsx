/**
 * Compliance Page
 *
 * DoD readiness, CMMC 2.0 compliance, and data sovereignty information.
 */

import Link from 'next/link';
import { Logo } from '@/components/shared/Logo';

export default function CompliancePage() {
  return (
    <div className="min-h-screen bg-aether-bg-dark">
      {/* Header */}
      <header className="border-b border-aether-indigo-light bg-aether-bg-card">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Logo size="sm" />
            <Link
              href="/"
              className="text-sm text-aether-text-muted hover:text-aether-purple-light transition-colors"
            >
              ← Back to Chat
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-12">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gradient-aether animate-pulse-glow mb-4">
            Government-Ready AI Infrastructure
          </h1>
          <p className="text-xl text-aether-text-muted max-w-3xl mx-auto">
            AetherAI is built from the ground up to meet Department of Defense
            requirements and CMMC 2.0 compliance standards.
          </p>
        </div>

        {/* Compliance Badges */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-aether-bg-card border border-aether-indigo-light rounded-xl p-6 text-center">
            <div className="text-4xl mb-3">🇺🇸</div>
            <h3 className="text-lg font-bold text-aether-purple-light mb-2">
              100% US-Based
            </h3>
            <p className="text-sm text-aether-text-muted">
              All infrastructure hosted exclusively on CONUS (Continental United
              States) soil
            </p>
          </div>

          <div className="bg-aether-bg-card border border-aether-indigo-light rounded-xl p-6 text-center">
            <div className="text-4xl mb-3">🛡️</div>
            <h3 className="text-lg font-bold text-aether-purple-light mb-2">
              DoD-Ready
            </h3>
            <p className="text-sm text-aether-text-muted">
              Designed to meet Department of Defense security and operational
              requirements
            </p>
          </div>

          <div className="bg-aether-bg-card border border-aether-indigo-light rounded-xl p-6 text-center">
            <div className="text-4xl mb-3">✅</div>
            <h3 className="text-lg font-bold text-aether-purple-light mb-2">
              CMMC 2.0 Compliant
            </h3>
            <p className="text-sm text-aether-text-muted">
              On track for Cybersecurity Maturity Model Certification Level 2
              compliance
            </p>
          </div>
        </div>

        {/* US-Only Models Section */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-aether-text mb-6">
            US-Only Model Infrastructure
          </h2>
          <div className="bg-aether-bg-card border border-aether-indigo-light rounded-xl p-6">
            <div className="space-y-6">
              {/* Apriel */}
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">🏠</span>
                  <h3 className="text-xl font-bold text-aether-purple-light">
                    Apriel (70% of traffic)
                  </h3>
                </div>
                <ul className="list-disc list-inside space-y-1 text-aether-text-muted ml-11">
                  <li>
                    Self-hosted on US-based cloud infrastructure (AWS
                    us-gov-west-1)
                  </li>
                  <li>
                    No data ever transmitted to foreign servers or entities
                  </li>
                  <li>Full control over model weights and inference pipeline</li>
                  <li>Zero-cost inference for government use cases</li>
                </ul>
              </div>

              {/* Grok-2 */}
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">🧠</span>
                  <h3 className="text-xl font-bold text-aether-purple-light">
                    Grok-2 (20% of traffic)
                  </h3>
                </div>
                <ul className="list-disc list-inside space-y-1 text-aether-text-muted ml-11">
                  <li>Hosted by xAI (US company founded by Elon Musk)</li>
                  <li>All xAI infrastructure located in the United States</li>
                  <li>Advanced reasoning for complex analytical tasks</li>
                  <li>API access with data residency guarantees</li>
                </ul>
              </div>

              {/* Claude */}
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">👁️</span>
                  <h3 className="text-xl font-bold text-aether-purple-light">
                    Claude (10% of traffic)
                  </h3>
                </div>
                <ul className="list-disc list-inside space-y-1 text-aether-text-muted ml-11">
                  <li>Provided by Anthropic (US-based, San Francisco)</li>
                  <li>
                    Used exclusively for vision and deep analysis tasks
                  </li>
                  <li>Constitutional AI principles align with RAI framework</li>
                  <li>Anthropic's AWS deployment uses US-only regions</li>
                </ul>
              </div>
            </div>

            <div className="mt-6 p-4 bg-aether-indigo/20 border border-aether-purple-light rounded-lg">
              <p className="text-sm text-aether-text">
                <strong className="text-aether-purple-light">
                  Smart Routing Guarantee:
                </strong>{' '}
                All models are US-based with no international data transfer.
                Auto-routing intelligently selects the best model for your query
                while maintaining complete data sovereignty.
              </p>
            </div>
          </div>
        </section>

        {/* RAI Principles Section */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-aether-text mb-6">
            Responsible AI (RAI) Principles
          </h2>
          <div className="bg-aether-bg-card border border-aether-indigo-light rounded-xl p-6">
            <p className="text-aether-text-muted mb-6">
              AetherAI adheres to the Department of Defense's Responsible
              Artificial Intelligence Strategy and Ethical Principles for AI:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-aether-bg-dark rounded-lg border-l-4 border-aether-purple-light">
                <h4 className="font-bold text-aether-text mb-2">
                  1. Responsible
                </h4>
                <p className="text-sm text-aether-text-muted">
                  Human oversight at all critical decision points. AI augments,
                  never replaces, human judgment.
                </p>
              </div>

              <div className="p-4 bg-aether-bg-dark rounded-lg border-l-4 border-aether-purple-light">
                <h4 className="font-bold text-aether-text mb-2">2. Equitable</h4>
                <p className="text-sm text-aether-text-muted">
                  Models trained on diverse datasets to minimize bias and ensure
                  fair treatment across all demographics.
                </p>
              </div>

              <div className="p-4 bg-aether-bg-dark rounded-lg border-l-4 border-aether-purple-light">
                <h4 className="font-bold text-aether-text mb-2">3. Traceable</h4>
                <p className="text-sm text-aether-text-muted">
                  Full audit logs of all queries, responses, and model decisions
                  for compliance and review.
                </p>
              </div>

              <div className="p-4 bg-aether-bg-dark rounded-lg border-l-4 border-aether-purple-light">
                <h4 className="font-bold text-aether-text mb-2">4. Reliable</h4>
                <p className="text-sm text-aether-text-muted">
                  Rigorous testing and validation to ensure consistent,
                  dependable performance in operational environments.
                </p>
              </div>

              <div className="p-4 bg-aether-bg-dark rounded-lg border-l-4 border-aether-purple-light">
                <h4 className="font-bold text-aether-text mb-2">5. Governable</h4>
                <p className="text-sm text-aether-text-muted">
                  Clear policies, procedures, and oversight mechanisms to manage
                  AI systems throughout their lifecycle.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Data Sovereignty Section */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-aether-text mb-6">
            Data Sovereignty Guarantees
          </h2>
          <div className="bg-aether-bg-card border border-aether-indigo-light rounded-xl p-6">
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-aether-purple-dark to-aether-purple-light flex items-center justify-center text-white font-bold">
                  ✓
                </div>
                <div>
                  <h4 className="font-bold text-aether-text mb-1">
                    No International Data Transfer
                  </h4>
                  <p className="text-sm text-aether-text-muted">
                    Your data never crosses US borders. All processing,
                    storage, and model inference occurs exclusively within
                    CONUS.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-aether-purple-dark to-aether-purple-light flex items-center justify-center text-white font-bold">
                  ✓
                </div>
                <div>
                  <h4 className="font-bold text-aether-text mb-1">
                    Encryption at Rest and in Transit
                  </h4>
                  <p className="text-sm text-aether-text-muted">
                    All data encrypted using AES-256 at rest and TLS 1.3+ in
                    transit. Keys managed via FIPS 140-2 compliant HSMs.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-aether-purple-dark to-aether-purple-light flex items-center justify-center text-white font-bold">
                  ✓
                </div>
                <div>
                  <h4 className="font-bold text-aether-text mb-1">
                    Zero Data Retention by Third Parties
                  </h4>
                  <p className="text-sm text-aether-text-muted">
                    API calls to Grok-2 and Claude configured for zero retention.
                    No training on government queries or sensitive data.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-aether-purple-dark to-aether-purple-light flex items-center justify-center text-white font-bold">
                  ✓
                </div>
                <div>
                  <h4 className="font-bold text-aether-text mb-1">
                    Access Controls and Authentication
                  </h4>
                  <p className="text-sm text-aether-text-muted">
                    Role-based access control (RBAC), multi-factor authentication
                    (MFA), and integration with DoD PKI/CAC systems available.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <div className="shrink-0 w-8 h-8 rounded-full bg-gradient-to-r from-aether-purple-dark to-aether-purple-light flex items-center justify-center text-white font-bold">
                  ✓
                </div>
                <div>
                  <h4 className="font-bold text-aether-text mb-1">
                    Continuous Monitoring and Compliance
                  </h4>
                  <p className="text-sm text-aether-text-muted">
                    24/7 security monitoring, annual third-party audits, and
                    continuous compliance validation against NIST 800-53 controls.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CMMC Roadmap Section */}
        <section className="mb-12">
          <h2 className="text-3xl font-bold text-aether-text mb-6">
            CMMC 2.0 Compliance Roadmap
          </h2>
          <div className="bg-aether-bg-card border border-aether-indigo-light rounded-xl p-6">
            <p className="text-aether-text-muted mb-6">
              AetherAI is on a structured path to achieve CMMC Level 2
              certification, required for DoD contractors handling Controlled
              Unclassified Information (CUI).
            </p>

            <div className="space-y-4">
              {/* Phase 1 */}
              <div className="relative pl-8 pb-8 border-l-2 border-aether-purple-light">
                <div className="absolute -left-2 top-0 w-4 h-4 rounded-full bg-aether-purple-light"></div>
                <div className="bg-aether-bg-dark p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-bold text-aether-text">
                      Phase 1: Foundation (Q1 2025)
                    </h4>
                    <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">
                      ✓ COMPLETED
                    </span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-sm text-aether-text-muted">
                    <li>Infrastructure deployed on US-only cloud regions</li>
                    <li>Encryption at rest and in transit implemented</li>
                    <li>Access controls and audit logging enabled</li>
                    <li>NIST 800-171 initial assessment complete</li>
                  </ul>
                </div>
              </div>

              {/* Phase 2 */}
              <div className="relative pl-8 pb-8 border-l-2 border-aether-purple-light">
                <div className="absolute -left-2 top-0 w-4 h-4 rounded-full bg-aether-purple-light"></div>
                <div className="bg-aether-bg-dark p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-bold text-aether-text">
                      Phase 2: Gap Remediation (Q2 2025)
                    </h4>
                    <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded">
                      IN PROGRESS
                    </span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-sm text-aether-text-muted">
                    <li>Full NIST 800-171 compliance implementation</li>
                    <li>System Security Plan (SSP) development</li>
                    <li>Incident response procedures and tabletop exercises</li>
                    <li>Personnel security and training programs</li>
                  </ul>
                </div>
              </div>

              {/* Phase 3 */}
              <div className="relative pl-8 pb-8 border-l-2 border-aether-purple-light">
                <div className="absolute -left-2 top-0 w-4 h-4 rounded-full bg-aether-purple-light"></div>
                <div className="bg-aether-bg-dark p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-bold text-aether-text">
                      Phase 3: Third-Party Assessment (Q3 2025)
                    </h4>
                    <span className="text-xs bg-gray-500/20 text-gray-400 px-2 py-1 rounded">
                      PLANNED
                    </span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-sm text-aether-text-muted">
                    <li>
                      Engage CMMC Third-Party Assessment Organization (C3PAO)
                    </li>
                    <li>Conduct readiness assessment and remediate findings</li>
                    <li>Documentation review and evidence collection</li>
                    <li>Pre-assessment preparation and dry runs</li>
                  </ul>
                </div>
              </div>

              {/* Phase 4 */}
              <div className="relative pl-8">
                <div className="absolute -left-2 top-0 w-4 h-4 rounded-full bg-aether-purple-light"></div>
                <div className="bg-aether-bg-dark p-4 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-bold text-aether-text">
                      Phase 4: Certification (Q4 2025)
                    </h4>
                    <span className="text-xs bg-gray-500/20 text-gray-400 px-2 py-1 rounded">
                      PLANNED
                    </span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-sm text-aether-text-muted">
                    <li>Official CMMC Level 2 assessment by C3PAO</li>
                    <li>Certification awarded and registered in eMASS</li>
                    <li>Continuous monitoring and annual re-assessment planning</li>
                    <li>DoD contract eligibility for CUI workloads</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-aether-indigo/20 border border-aether-purple-light rounded-lg">
              <p className="text-sm text-aether-text">
                <strong className="text-aether-purple-light">
                  Target Certification Date:
                </strong>{' '}
                Q4 2025. We are committed to achieving full CMMC Level 2
                compliance to serve Department of Defense mission-critical AI
                needs.
              </p>
            </div>
          </div>
        </section>

        {/* Contact CTA */}
        <section className="bg-gradient-to-r from-aether-purple-dark to-aether-purple-light rounded-xl p-8 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Deploy Sovereign AI for Your Mission?
          </h2>
          <p className="text-lg mb-6 opacity-90">
            Contact our Government Solutions team to discuss your requirements
            and deployment timeline.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="mailto:gov-solutions@aetherai.us"
              className="bg-white text-aether-purple-dark px-6 py-3 rounded-lg font-semibold hover:bg-gray-100 transition-colors"
            >
              Email: gov-solutions@aetherai.us
            </a>
            <Link
              href="/"
              className="bg-white/10 backdrop-blur-sm border border-white/30 px-6 py-3 rounded-lg font-semibold hover:bg-white/20 transition-colors"
            >
              Try AetherAI Now
            </Link>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-aether-indigo-light bg-aether-bg-card mt-12">
        <div className="max-w-5xl mx-auto px-4 py-6 text-center text-xs text-aether-text-muted">
          <p>
            © 2025 AetherAI. The American Standard for Sovereign AI
            Infrastructure.
          </p>
          <p className="mt-2">
            All infrastructure hosted on US soil. Your mission. Our commitment.
            🇺🇸
          </p>
        </div>
      </footer>
    </div>
  );
}
