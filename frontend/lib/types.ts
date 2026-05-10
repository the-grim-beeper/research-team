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
