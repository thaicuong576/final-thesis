import { Fragment, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

export interface Crumb {
  label: string;
  to?: string;
}

/** Top-bar location line: plain sentence-case crumbs, the last one is the current page. */
export function PageCrumbs({ items, aside }: { items: Crumb[]; aside?: ReactNode }) {
  return (
    <div className="flex w-full min-w-0 items-center justify-between gap-4">
      <nav aria-label="Vị trí" className="flex min-w-0 items-center gap-1.5 text-[13px]">
        {items.map((item, idx) => {
          const last = idx === items.length - 1;
          return (
            <Fragment key={`${item.label}-${idx}`}>
              {idx > 0 && <ChevronRight className="size-3.5 shrink-0 text-ink-tertiary" aria-hidden="true" />}
              {item.to && !last ? (
                <Link to={item.to} className="shrink-0 text-ink-secondary transition-colors hover:text-ink">
                  {item.label}
                </Link>
              ) : (
                <span
                  className={last ? 'truncate font-semibold text-ink' : 'shrink-0 text-ink-secondary'}
                  aria-current={last ? 'page' : undefined}
                >
                  {item.label}
                </span>
              )}
            </Fragment>
          );
        })}
      </nav>
      {aside && <div className="hidden shrink-0 items-center sm:flex">{aside}</div>}
    </div>
  );
}

export function StatusPill({ tone, children }: { tone: 'ready' | 'warning' | 'neutral'; children: ReactNode }) {
  const styles = {
    ready: 'bg-ready-soft text-text-success border-ready/30',
    warning: 'bg-warning-soft text-text-warning border-warning/30',
    neutral: 'bg-surface-secondary text-ink-secondary border-border-default'
  }[tone];
  const dot = { ready: 'bg-ready', warning: 'bg-warning', neutral: 'bg-ink-tertiary' }[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium ${styles}`}>
      <span className={`size-1.5 rounded-full ${dot}`} aria-hidden="true" />
      {children}
    </span>
  );
}
