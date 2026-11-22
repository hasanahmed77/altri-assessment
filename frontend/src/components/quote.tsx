export function Quote({ quote, source }: { quote?: string | null; source?: string | null }) {
  if (!quote) return null;
  return (
    <span className="text-muted-foreground block text-xs">
      “{quote}”{source && <span> · {source}</span>}
    </span>
  );
}
