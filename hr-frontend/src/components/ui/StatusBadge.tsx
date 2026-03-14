import React from 'react';

type BadgeVariant =
  | 'active' | 'on_leave' | 'inactive'
  | 'pending' | 'approved' | 'rejected'
  | 'present' | 'absent' | 'late' | 'half_day'
  | 'applied' | 'screening' | 'interview' | 'offered'
  | 'open' | 'closed' | 'draft'
  | 'scheduled' | 'completed';

const variantStyles: Record<BadgeVariant, string> = {
  active: 'bg-neo-teal text-neo-black',
  on_leave: 'bg-neo-yellow text-neo-black',
  inactive: 'bg-neo-coral text-neo-black',
  pending: 'bg-neo-yellow text-neo-black',
  approved: 'bg-neo-teal text-neo-black',
  rejected: 'bg-neo-coral text-neo-black',
  present: 'bg-neo-teal text-neo-black',
  absent: 'bg-neo-coral text-neo-black',
  late: 'bg-neo-yellow text-neo-black',
  half_day: 'bg-neo-blue text-white',
  applied: 'bg-gray-200 text-neo-black',
  screening: 'bg-neo-blue text-white',
  interview: 'bg-neo-yellow text-neo-black',
  offered: 'bg-neo-teal text-neo-black',
  open: 'bg-neo-teal text-neo-black',
  closed: 'bg-gray-400 text-white',
  draft: 'bg-neo-yellow text-neo-black',
  scheduled: 'bg-neo-blue text-white',
  completed: 'bg-neo-teal text-neo-black',
};

const labels: Record<BadgeVariant, string> = {
  active: 'Active', on_leave: 'On Leave', inactive: 'Inactive',
  pending: 'Pending', approved: 'Approved', rejected: 'Rejected',
  present: 'Present', absent: 'Absent', late: 'Late', half_day: 'Half Day',
  applied: 'Applied', screening: 'Screening', interview: 'Interview', offered: 'Offered',
  open: 'Open', closed: 'Closed', draft: 'Draft',
  scheduled: 'Scheduled', completed: 'Completed',
};

interface Props {
  status: BadgeVariant | string;
  className?: string;
}

export const StatusBadge = ({ status, className = '' }: Props) => {
  const variant = status as BadgeVariant;
  const style = variantStyles[variant] || 'bg-gray-200 text-neo-black';
  const label = labels[variant] || status;
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-mono font-semibold border-2 border-neo-black ${style} ${className}`}>
      {label}
    </span>
  );
};
