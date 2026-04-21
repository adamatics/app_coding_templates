import { zodResolver } from '@hookform/resolvers/zod';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import {
  useDeleteDepartment,
  useDepartment,
  useUpdateDepartment,
} from '../../api/departments';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { FormField } from '../../components/FormField';

export const Route = createFileRoute('/departments/$id')({
  component: DepartmentDetail,
});

const schema = z.object({
  name: z.string().min(1, 'Required').max(100),
  code: z
    .string()
    .regex(/^[A-Z]{2,10}$/, 'Must be 2-10 uppercase letters'),
  description: z.string().max(500).optional().nullable(),
});

type FormValues = z.infer<typeof schema>;

function DepartmentDetail() {
  const { id } = Route.useParams();
  const departmentId = Number(id);
  const navigate = useNavigate();
  const { data, isPending, error } = useDepartment(departmentId);
  const update = useUpdateDepartment(departmentId);
  const del = useDeleteDepartment();
  const [confirmOpen, setConfirmOpen] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: data
      ? {
          name: data.name,
          code: data.code,
          description: data.description,
        }
      : undefined,
  });

  if (isPending) return <p>Loading…</p>;
  if (error) return <p style={{ color: 'var(--color-danger)' }}>Error: {error.message}</p>;
  if (!data) return <p>Not found.</p>;

  const onSubmit = handleSubmit(async (values) => {
    await update.mutateAsync({
      name: values.name,
      code: values.code,
      description: values.description?.length ? values.description : null,
    });
  });

  const onDelete = async () => {
    await del.mutateAsync(departmentId);
    setConfirmOpen(false);
    navigate({ to: '/departments' });
  };

  return (
    <>
      <form onSubmit={onSubmit}>
        <h1>{data.name}</h1>
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
        title="Delete department?"
        message={`Delete "${data.name}"? Employees will block this if any reference it.`}
        confirmLabel="Delete"
        onConfirm={onDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
