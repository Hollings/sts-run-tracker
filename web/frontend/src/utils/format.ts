/**
 * Format a game ID like "CARD.STRIKE_IRONCLAD" into "Strike Ironclad".
 * Splits on first dot, replaces underscores with spaces, title-cases.
 */
export function formatGameId(id: string): string {
  if (!id || id === "NONE.NONE") return "";
  const dotIndex = id.indexOf(".");
  const name = dotIndex >= 0 ? id.slice(dotIndex + 1) : id;
  return name
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Format seconds into human-readable duration like "1h 23m 45s".
 */
export function formatDuration(seconds: number): string {
  if (seconds <= 0) return "0s";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const parts: string[] = [];
  if (h > 0) parts.push(`${h}h`);
  if (m > 0) parts.push(`${m}m`);
  if (s > 0 || parts.length === 0) parts.push(`${s}s`);
  return parts.join(" ");
}

/**
 * Format a Unix timestamp into a readable date string.
 */
export function formatDate(timestamp: number): string {
  if (!timestamp) return "";
  const d = new Date(timestamp * 1000);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Get a color class for room/floor types.
 * Shared by RunDetail and any other component that needs room-type colors.
 */
export function roomTypeColor(roomType: string): string {
  switch (roomType) {
    case "monster":
      return "text-red-400";
    case "elite":
      return "text-amber-400";
    case "boss":
      return "text-purple-400";
    case "ancient":
      return "text-purple-300";
    case "rest_site":
      return "text-green-400";
    case "treasure":
      return "text-yellow-400";
    case "shop":
      return "text-emerald-400";
    case "event":
    case "unknown":
      return "text-blue-400";
    default:
      return "text-sts-text-dim";
  }
}

/**
 * Get a background color class for room/floor types.
 */
export function roomTypeBg(roomType: string): string {
  switch (roomType) {
    case "monster":
      return "bg-red-900/25";
    case "elite":
      return "bg-amber-900/25";
    case "boss":
      return "bg-purple-900/25";
    case "ancient":
      return "bg-purple-900/20";
    case "rest_site":
      return "bg-green-900/20";
    case "treasure":
      return "bg-yellow-900/20";
    case "shop":
      return "bg-emerald-900/20";
    case "event":
    case "unknown":
      return "bg-blue-900/20";
    default:
      return "bg-sts-card";
  }
}
