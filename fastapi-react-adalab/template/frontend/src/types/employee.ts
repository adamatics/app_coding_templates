export interface Employee {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  title: string;
  department_id: number;
  hire_date: string;
  is_active: boolean;
  created_at: string;
}

export interface EmployeeCreate {
  first_name: string;
  last_name: string;
  email: string;
  title: string;
  department_id: number;
  hire_date: string;
  is_active: boolean;
}

export interface EmployeeUpdate {
  first_name?: string;
  last_name?: string;
  email?: string;
  title?: string;
  department_id?: number;
  hire_date?: string;
  is_active?: boolean;
}
