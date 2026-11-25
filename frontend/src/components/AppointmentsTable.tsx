import React, { useState } from 'react';
import type { Appointment } from '../types';
import { CalendarDays, Search, CheckCircle2, XCircle } from 'lucide-react';
import { formatCustomDate } from '../utils/dateFormatter';

interface AppointmentsTableProps {
  appointments: Appointment[];
  isLoading: boolean;
}

export const AppointmentsTable: React.FC<AppointmentsTableProps> = ({
  appointments,
  isLoading
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  // Sort appointments with most recently created at the top
  const sortedAppointments = [...appointments].sort((a, b) => {
    if (a._justUpdated === 'booked') return -1;
    if (b._justUpdated === 'booked') return 1;
    return b.id - a.id;
  });

  const filteredAppointments = sortedAppointments.filter((apt) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const formattedDate = formatCustomDate(apt.date).toLowerCase();
    return (
      apt.patient_name?.toLowerCase().includes(term) ||
      apt.phone?.includes(term) ||
      apt.doctor_name?.toLowerCase().includes(term) ||
      apt.date?.includes(term) ||
      formattedDate.includes(term)
    );
  });

  const formatPhone = (phone: string) => {
    if (phone.length === 10) {
      return `${phone.slice(0, 5)} ${phone.slice(5)}`;
    }
    return phone;
  };

  return (
    <div className="bg-[#F1E8D6] rounded-[14px] border border-[#B7A89A] overflow-hidden shadow-none">
      {/* Table Header & Search Filter */}
      <div className="p-3.5 sm:p-4 border-b border-[#B7A89A] flex items-center justify-between gap-2">
        <div className="flex items-center space-x-2 shrink-0">
          <CalendarDays className="w-4 h-4 text-[#722F37] shrink-0" />
          <h2 className="text-sm sm:text-base font-serif font-bold text-[#722F37] tracking-tight whitespace-nowrap">
            Registered Appointments
          </h2>
          <span className="text-[11px] text-[#6E5A54] font-medium shrink-0">
            ({appointments.length})
          </span>
        </div>

        {/* Search input */}
        <div className="relative w-36 sm:w-44 shrink-0">
          <Search className="w-3.5 h-3.5 text-[#6E5A54] absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search..."
            className="w-full pl-8 pr-2.5 py-1 text-xs bg-[#DDD0B8] text-[#3A1F23] placeholder-[#6E5A54] border border-[#B7A89A] rounded-[6px] focus:outline-none focus:border-[#722F37] transition-colors"
          />
        </div>
      </div>

      {/* Table Content: No clipped columns, no ID column, whitespace-nowrap on cells */}
      <div className="w-full max-h-[640px] overflow-y-auto scrollbar-thin">
        <table className="w-full text-left text-xs table-auto">
          <thead className="bg-[#DDD0B8] border-b border-[#B7A89A] text-[#722F37] font-semibold sticky top-0 z-10">
            <tr>
              <th className="py-2.5 pl-3.5 pr-2 font-semibold whitespace-nowrap">Patient</th>
              <th className="py-2.5 px-2 font-semibold whitespace-nowrap">Phone</th>
              <th className="py-2.5 px-2 font-semibold whitespace-nowrap">Doctor</th>
              <th className="py-2.5 px-2 font-semibold whitespace-nowrap">Date</th>
              <th className="py-2.5 px-2 font-semibold whitespace-nowrap">Time</th>
              <th className="py-2.5 pl-2 pr-3.5 font-semibold text-right whitespace-nowrap">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#B7A89A]/30">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-[#6E5A54]">
                  Loading appointments...
                </td>
              </tr>
            ) : filteredAppointments.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2">
                    <CalendarDays className="w-8 h-8 text-[#B7A89A]" />
                    <p className="text-sm font-medium text-[#3A1F23]">
                      {searchTerm ? 'No matching appointments found.' : 'No appointments yet'}
                    </p>
                    <p className="text-xs text-[#6E5A54]">
                      {searchTerm ? 'Try adjusting your search criteria.' : 'Bookings made via the voice assistant will appear here.'}
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredAppointments.map((apt) => {
                const isConfirmed = apt.status === 'confirmed';
                const highlightClass =
                  apt._justUpdated === 'booked'
                    ? 'animate-highlight-added bg-[rgba(114,47,55,0.22)]'
                    : apt._justUpdated === 'cancelled'
                    ? 'animate-highlight-cancelled bg-[rgba(114,47,55,0.22)]'
                    : '';

                return (
                  <tr
                    key={apt.id}
                    className={`transition-colors hover:bg-[#DDD0B8]/40 ${highlightClass}`}
                  >
                    <td className="py-2.5 pl-3 pr-1.5 font-medium text-[#3A1F23] whitespace-nowrap">
                      {apt.patient_name || 'Caller'}
                    </td>
                    {/* Phone number: same size as other cell text (text-xs), tabular numerals */}
                    <td className="py-2.5 px-1.5 font-mono text-xs tabular-nums font-medium text-[#3A1F23] whitespace-nowrap">
                      {formatPhone(apt.phone)}
                    </td>
                    <td className="py-2.5 px-1.5 text-[#3A1F23] whitespace-nowrap">
                      {apt.doctor_name}
                    </td>
                    <td className="py-2.5 px-1.5 text-[#3A1F23] whitespace-nowrap">
                      {formatCustomDate(apt.date)}
                    </td>
                    <td className="py-2.5 px-1.5 font-medium text-[#3A1F23] whitespace-nowrap">
                      {apt.time}
                    </td>
                    <td className="py-2.5 pl-1.5 pr-3 text-right whitespace-nowrap">
                      <span
                        className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10.5px] font-medium border ${
                          isConfirmed
                            ? 'bg-[#DCE5D2] text-[#3F6B4A] border-[#3F6B4A]/30'
                            : 'bg-[#EBD3D0] text-[#722F37] border-[#722F37]/30'
                        }`}
                      >
                        {isConfirmed ? (
                          <CheckCircle2 className="w-2.5 h-2.5 text-[#3F6B4A] shrink-0" />
                        ) : (
                          <XCircle className="w-2.5 h-2.5 text-[#722F37] shrink-0" />
                        )}
                        <span>{isConfirmed ? 'Confirmed' : 'Cancelled'}</span>
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
