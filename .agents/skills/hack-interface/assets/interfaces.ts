/**
 * Interfaces: the contracts between the parts of this project.
 * Single source of truth for data passed between modules and what each part offers.
 * Keep it small. Every change adds one line to docs/decisions.md in the same commit.
 * Additive changes can happen in a feature branch; breaking changes go in a small
 * iface/ pull request that updates all callers. The compiler is the contract test:
 * `npx tsc --noEmit` must pass. See $hack-interface.
 */

/** One input row after loading and validation. Rename to the domain object. */
export interface DomainRecord {
  id: string;
  value: number;
}

/** Result of applying the domain rules to one record. */
export interface Finding {
  recordId: string;
  status: "ok" | "warning" | "fail";
  /** Plain-language explanation shown to the user. */
  reason: string;
}

/** Reads raw input and returns validated records. Throws Error with a user-readable message. */
export interface Loader {
  load(source: File | string): Promise<DomainRecord[]>;
}

/** Applies the domain rules. Thresholds come from config/, not code. */
export interface RuleEngine {
  /** Exactly one Finding per record, in the same order. */
  evaluate(records: DomainRecord[]): Finding[];
}
