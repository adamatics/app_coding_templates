import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { Employee, EmployeeCreate, EmployeeUpdate } from '../types/employee';
import { apiClient } from './client';

const KEY = ['employees'] as const;

export function useEmployees() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => apiClient.get<Employee[]>('/employees'),
  });
}

export function useEmployee(id: number) {
  return useQuery({
    queryKey: [...KEY, id],
    queryFn: () => apiClient.get<Employee>(`/employees/${id}`),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useCreateEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: EmployeeCreate) =>
      apiClient.post<Employee>('/employees', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateEmployee(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: EmployeeUpdate) =>
      apiClient.patch<Employee>(`/employees/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: [...KEY, id] });
    },
  });
}

export function useDeleteEmployee() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.delete<void>(`/employees/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
