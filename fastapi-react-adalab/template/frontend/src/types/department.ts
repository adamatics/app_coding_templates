export interface Department {
  id: number;
  name: string;
  code: string;
  description: string | null;
  created_at: string;
}

export interface DepartmentCreate {
  name: string;
  code: string;
  description?: string | null;
}

export interface DepartmentUpdate {
  name?: string;
  code?: string;
  description?: string | null;
}
