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
