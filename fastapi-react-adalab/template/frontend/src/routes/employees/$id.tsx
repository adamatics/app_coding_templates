import { zodResolver } from '@hookform/resolvers/zod';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useDepartments } from '../../api/departments';
import {
  useDeleteEmployee,
  useEmployee,
  useUpdateEmployee,
} from '../../api/employees';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { FormField } from '../../components/FormField';

export const Route = createFileRoute('/employees/$id')({
  component: EmployeeDetail,
});

const schema = z.object({
  first_name: z.string().min(1, 'Required').max(50),
  last_name: z.string().min(1, 'Required').max(50),
  email: z.string().email('Must be a valid email'),
  title: z.string().min(1, 'Required').max(100),
  department_id: z.coerce.number().int().positive('Pick a department'),
  hire_date: z.string().min(1, 'Required'),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

function EmployeeDetail() {
  const { id } = Route.useParams();
  const employeeId = Number(id);
  const navigate = useNavigate();
  const { data, isPending, error } = useEmployee(employeeId);
  const update = useUpdateEmployee(employeeId);
  const del = useDeleteEmployee();
  const departments = useDepartments();
  const [confirmOpen, setConfirmOpen] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? {
          first_name: data.first_name,
          last_name: data.last_name,
          email: data.email,
          title: data.title,
          department_id: data.department_id,
          hire_date: data.hire_date,
          is_active: data.is_active,
        }
      : undefined,
  });

  if (isPending) return <p>Loading…</p>;
  if (error) return <p style={{ color: 'var(--color-danger)' }}>Error: {error.message}</p>;
  if (!data) return <p>Not found.</p>;

  const onSubmit = handleSubmit(async (values) => {
    await update.mutateAsync(values);
  });

  const onDelete = async () => {
    await del.mutateAsync(employeeId);
    setConfirmOpen(false);
    navigate({ to: '/employees' });
  };

  return (
    <>
      <form onSubmit={onSubmit}>
        <h1>
          {data.first_name} {data.last_name}
        </h1>
        <FormField label="First name" htmlFor="first_name" error={errors.first_name?.message}>
          <input id="first_name" type="text" {...register('first_name')} />
        </FormField>
        <FormField label="Last name" htmlFor="last_name" error={errors.last_name?.message}>
          <input id="last_name" type="text" {...register('last_name')} />
        </FormField>
        <FormField label="Email" htmlFor="email" error={errors.email?.message}>
          <input id="email" type="email" {...register('email')} />
        </FormField>
        <FormField label="Title" htmlFor="title" error={errors.title?.message}>
          <input id="title" type="text" {...register('title')} />
        </FormField>
        <FormField label="Department" htmlFor="department_id" error={errors.department_id?.message}>
          <select id="department_id" {...register('department_id')}>
            {(departments.data ?? []).map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.code})
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Hire date" htmlFor="hire_date" error={errors.hire_date?.message}>
          <input id="hire_date" type="date" {...register('hire_date')} />
        </FormField>
        <FormField label="Active" htmlFor="is_active">
          <input id="is_active" type="checkbox" {...register('is_active')} />
        </FormField>
        {update.error && (
          <p style={{ color: 'var(--color-danger)' }}>{update.error.message}</p>
        )}
        <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
          <button type="submit" className="primary" disabled={update.isPending}>
            {update.isPending ? 'Saving…' : 'Save changes'}
          </button>
          <button
            type="button"
            className="danger"
            onClick={() => setConfirmOpen(true)}
          >
            Delete
          </button>
        </div>
      </form>
      <ConfirmDialog
        open={confirmOpen}
        title="Delete employee?"
        message={`Delete "${data.first_name} ${data.last_name}"?`}
        confirmLabel="Delete"
        onConfirm={onDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
