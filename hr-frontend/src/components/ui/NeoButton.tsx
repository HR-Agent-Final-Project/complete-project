import React, { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'teal' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variantStyles: Record<Variant, string> = {
  primary: 'bg-neo-yellow text-neo-black border-2 border-neo-black shadow-neo hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-neo-sm',
  secondary: 'bg-white text-neo-black border-2 border-neo-black shadow-neo hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-neo-sm',
  danger: 'bg-neo-coral text-neo-black border-2 border-neo-black shadow-neo hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-neo-sm',
  teal: 'bg-neo-teal text-neo-black border-2 border-neo-black shadow-neo hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-neo-sm',
  ghost: 'bg-transparent text-neo-black border-2 border-neo-black hover:bg-black hover:text-white',
};

const sizeStyles: Record<Size, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

export const NeoButton = ({
  variant = 'primary', size = 'md', loading, icon, children, className = '', disabled, ...rest
}: Props) => (
  <button
    {...rest}
    disabled={disabled || loading}
    className={`
      font-display font-bold transition-all duration-100 cursor-pointer
      flex items-center gap-2 justify-center
      disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:shadow-neo
      ${variantStyles[variant]} ${sizeStyles[size]} ${className}
    `}
  >
    {loading ? (
      <span className="flex gap-1">
        <span className="typing-dot w-1.5 h-1.5 bg-current rounded-full inline-block" />
        <span className="typing-dot w-1.5 h-1.5 bg-current rounded-full inline-block" />
        <span className="typing-dot w-1.5 h-1.5 bg-current rounded-full inline-block" />
      </span>
    ) : (
      <>
        {icon && <span className="flex-shrink-0">{icon}</span>}
        {children}
      </>
    )}
  </button>
);
