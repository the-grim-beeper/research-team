export type SubjectStatus = "active" | "archived";

export interface Subject {
  id: number;
  title: string;
  brief: string;
  status: SubjectStatus;
  created_at: string;
}

export interface Me {
  id: number;
  email: string;
}

export type RoleCategory = "admin" | "expert";
export type AgentTier = "cheap" | "mid" | "premium";
export type AgentCycle = "off" | "on_demand" | "hourly" | "every_4h" | "daily";

export interface RoleEmbed {
  id: number;
  slug: string;
  display_name: string;
  category: RoleCategory;
}

export interface Role extends RoleEmbed {
  default_system_prompt: string;
  default_model: string;
  default_cycle: AgentCycle;
  default_tier: AgentTier;
  tools: string[];
  created_at: string;
}

export interface Agent {
  id: number;
  subject_id: number;
  role: RoleEmbed;
  display_name: string;
  system_prompt: string;
  model: string;
  cycle: AgentCycle;
  daily_budget_usd: string;
  spent_today_usd: string;
  last_run_at: string | null;
  created_at: string;
}

export interface AgentUpdate {
  model?: string;
  cycle?: AgentCycle;
  daily_budget_usd?: string | number;
  system_prompt_addendum?: string;
}

export type ArtifactKind =
  | "note"
  | "briefing"
  | "synthesis"
  | "critique"
  | "roundtable_post"
  | "instruction"
  | "source_summary"
  | "bibliography_comment";

export interface Artifact {
  id: number;
  subject_id: number;
  kind: ArtifactKind | string;
  author_type: "agent" | "user";
  author_id: number | null;
  parent_id: number | null;
  addressed_to: number | null;
  title: string;
  body_md: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export type SourceKind = "rss" | "arxiv" | "url" | "notes";

export interface Source {
  id: number;
  subject_id: number;
  kind: SourceKind;
  display_name: string;
  config_json: Record<string, unknown>;
  created_at: string;
}

export interface BibliographyEntry {
  id: number;
  subject_id: number;
  corpus_item_id: number;
  comments: string;
  created_at: string;
  updated_at: string;
  title: string;
  url: string | null;
  authors: string[];
  summary: string | null;
  tags: string[];
  importance: number | null;
}
