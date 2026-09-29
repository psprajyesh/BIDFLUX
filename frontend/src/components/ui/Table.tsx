import type { KeyboardEvent, ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right" | "center";
  width?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyMessage = "No records.",
  rowClassName,
  onRowClick,
  tableLabel,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyMessage?: string;
  rowClassName?: (row: T) => string | undefined;
  onRowClick?: (row: T) => void;
  tableLabel?: string;
}) {
  const alignClass = {
    left: "text-left",
    right: "text-right",
    center: "text-center",
  } as const;

  const onKeyDown = (row: T) => (event: KeyboardEvent<HTMLTableRowElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRowClick?.(row);
    }
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse" aria-label={tableLabel}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={`th ${alignClass[column.align ?? "left"]}`}
                style={column.width ? { width: column.width } : undefined}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-8 text-center text-slate-500">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                className={`tr ${rowClassName?.(row) ?? ""}`}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={onRowClick ? onKeyDown(row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? "row" : undefined}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`td ${alignClass[column.align ?? "left"]}`}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function KeyValue({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-[11px] font-medium uppercase tracking-[0.04em] text-slate-500">
            {item.label}
          </dt>
          <dd
            className="mt-0.5 truncate text-[13px] text-slate-900"
            title={typeof item.value === "string" ? item.value : undefined}
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
