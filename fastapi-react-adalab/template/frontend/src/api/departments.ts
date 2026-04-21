import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type {
  Department,
  DepartmentCreate,
  DepartmentUpdate,
} from '../types/department';
import { apiClient } from './client';

const KEY = ['departments'] as const;

export function useDepartments() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => apiClient.get<Department[]>('/departments'),
  });
}

export function useDepartment(id: number) {
  return useQuery({
    queryKey: [...KEY, id],
    queryFn: () => apiClient.get<Department>(`/departments/${id}`),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useCreateDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DepartmentCreate) =>
      apiClient.post<Department>('/departments', data),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateDepartment(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DepartmentUpdate) =>
      apiClient.patch<Department>(`/departments/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEY });
      qc.invalidateQueries({ queryKey: [...KEY, id] });
    },
  });
}

export function useDeleteDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => apiClient.delete<void>(`/departments/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
