import { zodResolver } from '@hookform/resolvers/zod';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useDepartments } from '../../api/departments';
import { useCreateEmployee } from '../../api/employees';
import { FormField } from '../../components/FormField';

export const Route = createFileRoute('/employees/new')({
  component: NewEmployee,
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

function NewEmployee() {
  const navigate = useNavigate();
  const create = useCreateEmployee();
  const departments = useDepartments();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { is_active: true },
  });

  const onSubmit = handleSubmit(async (data) => {
    const created = await create.mutateAsync(data);
    navigate({ to: '/employees/$id', params: { id: String(created.id) } });
  });

  return (
    <form onSubmit={onSubmit}>
      <h1>New Employee</h1>
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
          <option value="">—</option>
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
      {create.error && (
        <p style={{ color: 'var(--color-danger)' }}>{create.error.message}</p>
      )}
      <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
        <button type="submit" className="primary" disabled={create.isPending}>
          {create.isPending ? 'Saving…' : 'Create'}
        </button>
        <button type="button" onClick={() => navigate({ to: '/employees' })}>
          Cancel
        </button>
      </div>
    </form>
  );
}
