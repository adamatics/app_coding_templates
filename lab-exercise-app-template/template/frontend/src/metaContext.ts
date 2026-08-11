import { createContext, useContext } from "react";
import type { Meta } from "./api";

export const MetaContext = createContext<Meta | null>(null);

/** The exercise metadata (schema, titles, open cohort). Guaranteed non-null inside the app
 * shell, which does not render children until meta has loaded. */
export function useMeta(): Meta {
  const meta = useContext(MetaContext);
  if (!meta) throw new Error("useMeta used outside the loaded app shell");
  return meta;
}
