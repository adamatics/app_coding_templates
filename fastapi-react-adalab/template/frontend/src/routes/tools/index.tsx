import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/tools/')({
  component: () => (
    <p className="muted">Tools UI arrives next commit — file upload + CSV/Excel download.</p>
  ),
});
