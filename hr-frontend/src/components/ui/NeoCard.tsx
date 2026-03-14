import React, { HTMLAttributes } from 'react';

interface Props extends HTMLAttributes<HTMLDivElement> {
  color?: string;
  shadow?: 'sm' | 'md' | 'lg' | 'none';
  padding?: string;
}

const shadowMap = {
  sm: 'shadow-neo-sm',
  md: 'shadow-neo',
  lg: 'shadow-neo-lg',
  none: '',
};

export const NeoCard = ({
  color = 'bg-white',
  shadow = 'md',
  padding = 'p-4',
  className = '',
  children,
  ...rest
}: Props) => (
  <div
    {...rest}
    className={`border-2 border-neo-black ${color} ${shadowMap[shadow]} ${padding} ${className}`}
  >
    {children}
  </div>
);
