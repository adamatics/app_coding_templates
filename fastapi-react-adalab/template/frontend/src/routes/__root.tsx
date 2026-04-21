import type { QueryClient } from '@tanstack/react-query';
import { Outlet, createRootRouteWithContext } from '@tanstack/react-router';

import { AppHeader } from '../components/AppHeader';

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: Root,
});

function Root() {
  return (
    <>
      <AppHeader />
      <main style={{ maxWidth: 1100, margin: '0 auto', padding: 'var(--space-xl)' }}>
        <Outlet />
      </main>
    </>
  );
}
