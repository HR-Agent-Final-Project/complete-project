import React, { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  width?: string;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
  keyField?: keyof T;
}

export function DataTable<T extends Record<string, any>>({
  columns, data, onRowClick, loading, emptyMessage = 'No data found.', keyField = 'id' as keyof T,
}: Props<T>) {
  if (loading) {
    return (
      <div className="border-2 border-neo-black overflow-hidden">
        <table className="neo-table">
          <thead>
            <tr>{columns.map(c => <th key={c.key}>{c.header}</th>)}</tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => (
              <tr key={i}>
                {columns.map(c => (
                  <td key={c.key}><div className="skeleton h-4 w-full rounded" /></td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="border-2 border-neo-black overflow-x-auto">
      <table className="neo-table">
        <thead>
          <tr>
            {columns.map(c => (
              <th key={c.key} style={c.width ? { width: c.width } : {}}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-center py-8 text-gray-500 font-mono text-sm">
                {emptyMessage}
              </td>
            </tr>
          ) : data.map((row, i) => (
            <tr
              key={String(row[keyField] ?? i)}
              onClick={() => onRowClick?.(row)}
              className={onRowClick ? 'cursor-pointer' : ''}
            >
              {columns.map(c => (
                <td key={c.key} className="font-mono text-sm">
                  {c.render ? c.render(row) : String(row[c.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
