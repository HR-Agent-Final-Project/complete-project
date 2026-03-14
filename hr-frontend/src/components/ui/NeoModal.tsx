import React, { ReactNode, useEffect } from 'react';
import { X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: string;
  headerColor?: string;
}

export const NeoModal = ({ open, onClose, title, children, width = 'max-w-lg', headerColor = 'bg-neo-yellow' }: Props) => {
  useEffect(() => {
    const handle = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (open) document.addEventListener('keydown', handle);
    return () => document.removeEventListener('keydown', handle);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className={`relative w-full ${width} border-2 border-neo-black shadow-neo-lg bg-white max-h-[95vh] flex flex-col sm:max-h-[90vh]`}>
        <div className={`${headerColor} border-b-2 border-neo-black px-4 py-3 flex items-center justify-between flex-shrink-0`}>
          <h2 className="font-display font-bold text-base md:text-lg text-neo-black">{title}</h2>
          <button
            onClick={onClose}
            className="p-1 border-2 border-neo-black bg-white hover:translate-x-[1px] hover:translate-y-[1px] shadow-neo-sm hover:shadow-none transition-all"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-4 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  );
};
