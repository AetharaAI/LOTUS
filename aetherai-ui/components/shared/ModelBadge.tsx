/**
 * Model Badge Component
 *
 * Shows which model generated the response.
 */

interface ModelBadgeProps {
  model: string;
  className?: string;
}

const modelInfo: Record<string, { name: string; icon: string; color: string }> = {
  apriel: {
    name: 'Apriel',
    icon: '🏠',
    color: 'from-aether-purple-dark to-aether-purple-light',
  },
  grok: {
    name: 'Grok-2',
    icon: '🧠',
    color: 'from-aether-indigo to-aether-purple-dark',
  },
  claude: {
    name: 'Claude',
    icon: '👁️',
    color: 'from-aether-indigo-light to-aether-indigo',
  },
  auto: {
    name: 'Auto',
    icon: '⚡',
    color: 'from-aether-purple-dark to-aether-purple-light',
  },
};

export function ModelBadge({ model, className = '' }: ModelBadgeProps) {
  const info = modelInfo[model] || modelInfo.auto;

  return (
    <div
      className={`model-badge bg-gradient-to-r ${info.color} ${className}`}
      title={`Powered by ${info.name}`}
    >
      <span>{info.icon}</span>
      <span>{info.name}</span>
    </div>
  );
}
