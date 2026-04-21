import { zodResolver } from '@hookform/resolvers/zod';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useCreateDepartment } from '../../api/departments';
import { FormField } from '../../components/FormField';

export const Route = createFileRoute('/departments/new')({
  component: NewDepartment,
});

const schema = z.object({
  name: z.string().min(1, 'Required').max(100),
  code: z
    .string()
    .regex(/^[A-Z]{2,10}$/, 'Must be 2-10 uppercase letters'),
  description: z.string().max(500).optional(),
});

type FormValues = z.infer<typeof schema>;

function NewDepartment() {
  const navigate = useNavigate();
  const create = useCreateDepartment();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (data) => {
    const created = await create.mutateAsync({
      name: data.name,
      code: data.code,
      description: data.description?.length ? data.description : null,
    });
    navigate({ to: '/departments/$id', params: { id: String(created.id) } });
  });

  return (
    <form onSubmit={onSubmit}>
      <h1>New Department</h1>
      <FormField label="Name" htmlFor="name" error={errors.name?.message}>
        <input id="name" type="text" {...register('name')} />
      </FormField>
      <FormField label="Code" htmlFor="code" error={errors.code?.message}>
        <input id="code" type="text" {...register('code')} />
      </FormField>
      <FormField
        label="Description"
        htmlFor="description"
        error={errors.description?.message}
      >
        <textarea id="description" rows={3} {...register('description')} />
      </FormField>
      {create.error && (
        <p style={{ color: 'var(--color-danger)' }}>{create.error.message}</p>
      )}
      <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
        <button type="submit" className="primary" disabled={create.isPending}>
          {create.isPending ? 'Saving…' : 'Create'}
        </button>
        <button type="button" onClick={() => navigate({ to: '/departments' })}>
          Cancel
        </button>
      </div>
    </form>
  );
}
