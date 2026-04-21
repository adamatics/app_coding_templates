export function getBasename(): string {
  const path = window.location.pathname;
  const proxyMatch = path.match(/^(\/jupyterhub\/user\/[^/]+\/proxy\/\d+)/);
  if (proxyMatch) return proxyMatch[1];
  const appsMatch = path.match(/^(\/apps\/[^/]+)/);
  if (appsMatch) return appsMatch[1];
  return '';
}
