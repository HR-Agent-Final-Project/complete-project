import React, { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}
interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

const labelClass = 'block font-mono font-semibold text-xs uppercase tracking-wider text-neo-black mb-1';
const inputClass = 'w-full border-2 border-neo-black bg-white px-3 py-2 font-mono text-sm text-neo-black outline-none focus:ring-2 focus:ring-neo-yellow focus:ring-offset-0 placeholder:text-gray-400 rounded-none disabled:bg-gray-100 disabled:cursor-not-allowed';
const errorClass = 'mt-1 font-mono text-xs text-neo-coral';

export const NeoInput = ({ label, error, className = '', ...rest }: InputProps) => (
  <div className="w-full">
    {label && <label className={labelClass}>{label}</label>}
    <input {...rest} className={`${inputClass} ${error ? 'border-neo-coral' : ''} ${className}`} />
    {error && <p className={errorClass}>{error}</p>}
  </div>
);

export const NeoTextarea = ({ label, error, className = '', ...rest }: TextareaProps) => (
  <div className="w-full">
    {label && <label className={labelClass}>{label}</label>}
    <textarea {...rest} className={`${inputClass} resize-y min-h-[80px] ${error ? 'border-neo-coral' : ''} ${className}`} />
    {error && <p className={errorClass}>{error}</p>}
  </div>
);

export const NeoSelect = ({ label, error, options, className = '', ...rest }: SelectProps) => (
  <div className="w-full">
    {label && <label className={labelClass}>{label}</label>}
    <select {...rest} className={`${inputClass} cursor-pointer ${error ? 'border-neo-coral' : ''} ${className}`}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
    {error && <p className={errorClass}>{error}</p>}
  </div>
);
