import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "success" | "danger" | "warning";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  disabled,
  children,
  className = "",
  ...rest
}: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`btn btn-${variant} btn-${size} ${className}`}
      {...rest}
    >
      {loading ? (
        <span
          aria-hidden
          className="h-3 w-3 rounded-full border-2 border-current border-r-transparent animate-spin"
        />
      ) : null}
      {children}
    </button>
  );
}
