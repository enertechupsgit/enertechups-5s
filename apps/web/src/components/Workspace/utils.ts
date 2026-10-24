import { useEffect, useState } from "react";
export const pillars = [
  { key: "sort_seiri", name: "Sort", label: "1S · Sort", score: "sort_score" },
  {
    key: "set_in_order_seiton",
    name: "Set in order",
    label: "2S · Set in order",
    score: "set_in_order_score",
  },
  {
    key: "shine_seiso",
    name: "Shine",
    label: "3S · Shine",
    score: "shine_score",
  },
  {
    key: "standardize_seiketsu",
    name: "Standardize",
    label: "4S · Standardize",
    score: "standardize_score",
  },
  {
    key: "sustain_shitsuke",
    name: "Sustain",
    label: "5S · Sustain",
    score: "sustain_score",
  },
] as const;
export const dateLabel = (date?: string | null) =>
  date
    ? new Date(date).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
      })
    : "No due date";
export const isComplete = (status: string) =>
  ["approved", "completed"].includes(status);

export function useNow() {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(timer);
  }, []);
  return now;
}
