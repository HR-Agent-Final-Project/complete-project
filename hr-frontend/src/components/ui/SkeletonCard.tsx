import React from 'react';

export const SkeletonCard = ({ className = '' }: { className?: string }) => (
  <div className={`border-2 border-neo-black p-4 bg-white shadow-neo ${className}`}>
    <div className="skeleton h-4 w-1/3 mb-3 rounded" />
    <div className="skeleton h-8 w-1/2 mb-2 rounded" />
    <div className="skeleton h-3 w-2/3 rounded" />
  </div>
);

export const SkeletonRow = ({ cols = 4 }: { cols?: number }) => (
  <tr>
    {Array.from({ length: cols }).map((_, i) => (
      <td key={i} className="border border-neo-black p-3">
        <div className="skeleton h-4 w-full rounded" />
      </td>
    ))}
  </tr>
);
