export interface ModelOption {
  slug: string;
  label: string;
  tier: "cheap" | "mid" | "premium";
}

export const MODEL_OPTIONS: ModelOption[] = [
  { slug: "anthropic/claude-haiku-4-5", label: "Haiku 4.5", tier: "cheap" },
  { slug: "google/gemini-2.5-flash", label: "Gemini 2.5 Flash", tier: "cheap" },
  { slug: "openai/gpt-4o-mini", label: "GPT-4o mini", tier: "cheap" },
  { slug: "anthropic/claude-sonnet-4-6", label: "Sonnet 4.6", tier: "mid" },
  { slug: "openai/gpt-4o", label: "GPT-4o", tier: "mid" },
  { slug: "anthropic/claude-opus-4-7", label: "Opus 4.7", tier: "premium" },
];

export const CYCLE_OPTIONS: { value: string; label: string }[] = [
  { value: "off", label: "Off (paused)" },
  { value: "on_demand", label: "On demand only" },
  { value: "hourly", label: "Hourly" },
  { value: "every_4h", label: "Every 4 hours" },
  { value: "daily", label: "Daily (overnight)" },
];

export function modelLabel(slug: string): string {
  return MODEL_OPTIONS.find((m) => m.slug === slug)?.label ?? slug;
}
