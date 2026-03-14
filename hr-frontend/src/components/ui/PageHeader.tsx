import React, { ReactNode } from 'react';
import { ChevronRight } from 'lucide-react';

interface Props {
  title: string;
  breadcrumbs?: { label: string; href?: string }[];
  action?: ReactNode;
}

export const PageHeader = ({ title, breadcrumbs, action }: Props) => (
  <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4 md:mb-6">
    <div className="min-w-0">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <div className="flex items-center gap-1 mb-1">
          {breadcrumbs.map((b, i) => (
            <React.Fragment key={i}>
              {i > 0 && <ChevronRight size={12} className="text-gray-400" />}
              <span className="font-mono text-xs text-gray-500 uppercase tracking-wider">{b.label}</span>
            </React.Fragment>
          ))}
        </div>
      )}
      <h1 className="font-display font-bold text-2xl md:text-3xl text-neo-black">{title}</h1>
    </div>
    {action && <div className="flex-shrink-0">{action}</div>}
  </div>
);
