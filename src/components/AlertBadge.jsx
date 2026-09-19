export default function AlertBadge({ type, size = 'md' }) {
  const styles = {
    red: 'bg-red-100 text-emergency border-red-200',
    yellow: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    green: 'bg-green-100 text-success border-green-200',
    unknown: 'bg-gray-100 text-text-secondary border-gray-300',
  };

  const sizes = {
    sm: 'text-[10px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-3 py-1.5',
  };

  const safeType = styles[type] ? type : 'unknown';
  const dotColor =
    safeType === 'red' ? 'bg-emergency' : safeType === 'yellow' ? 'bg-yellow-600' : safeType === 'green' ? 'bg-success' : 'bg-gray-400';

  return (
    <span className={`inline-flex items-center font-semibold rounded-full border uppercase tracking-wide ${styles[safeType]} ${sizes[size]}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${dotColor}`} />
      {safeType}
    </span>
  );
}