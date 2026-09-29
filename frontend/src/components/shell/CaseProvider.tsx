"use client";

import { createContext, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react";
import {
  clearActiveId,
  getActiveId,
  getServerActiveId,
  setActiveId as storeSetActiveId,
  subscribeActiveId,
} from "@/lib/caseStore";

/**
 * Holds the one verification ID that every stage of the workflow works on.
 *
 * The stages are standalone pages (documents, compliance, evidence, audit…),
 * so the selected case has to survive navigation. It is kept in localStorage
 * rather than a store library — that is the entire requirement, and a context
 * provider is enough.
 */

interface CaseContextValue {
  activeId: string | null;
  setActiveId: (id: string | null) => void;
  clearActiveId: () => void;
}

const CaseContext = createContext<CaseContextValue>({
  activeId: null,
  setActiveId: () => {},
  clearActiveId: () => {},
});

export function CaseProvider({ children }: { children: ReactNode }) {
  const activeId = useSyncExternalStore(subscribeActiveId, getActiveId, getServerActiveId);

  const value = useMemo<CaseContextValue>(
    () => ({
      activeId,
      setActiveId: storeSetActiveId,
      clearActiveId,
    }),
    [activeId],
  );

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
}

export function useActiveCase() {
  return useContext(CaseContext);
}
