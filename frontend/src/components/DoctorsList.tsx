import React, { useState } from 'react';
import type { Doctor } from '../types';
import { Stethoscope, Calendar, Clock } from 'lucide-react';
import { formatCustomDate } from '../utils/dateFormatter';

interface DoctorsListProps {
  doctors: Doctor[];
  isLoading: boolean;
}

export const DoctorsList: React.FC<DoctorsListProps> = ({ doctors, isLoading }) => {
  const [selectedDateIndex, setSelectedDateIndex] = useState<number>(0);

  const availableDates: string[] = doctors[0]?.available_dates || [];
  const selectedDateStr = availableDates[selectedDateIndex] || '';

  return (
    <div className="bg-[#F1E8D6] rounded-[14px] border border-[#B7A89A] overflow-hidden shadow-none">
      {/* Header & Date Selector */}
      <div className="p-4 sm:p-5 border-b border-[#B7A89A]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3.5">
          <div className="flex items-center space-x-2.5">
            <Stethoscope className="w-4 h-4 text-[#722F37]" />
            <h2 className="text-base font-serif font-bold text-[#722F37] tracking-tight">
              Doctors & Available Slots
            </h2>
            <span className="text-xs text-[#6E5A54] font-medium">
              ({doctors.length} specialists)
            </span>
          </div>

          <div className="flex items-center space-x-1.5 text-xs text-[#6E5A54]">
            <Calendar className="w-3.5 h-3.5 text-[#722F37]" />
            <span className="font-medium">Select Date:</span>
          </div>
        </div>

        {/* Date Tabs: Active burgundy fill, inactive transparent with --line border */}
        {availableDates.length > 0 && (
          <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-none">
            {availableDates.map((dateStr, idx) => {
              const isSelected = selectedDateIndex === idx;
              const formattedDate = formatCustomDate(dateStr);

              return (
                <button
                  key={dateStr}
                  onClick={() => setSelectedDateIndex(idx)}
                  className={`px-3 py-1.5 rounded-[8px] text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-[#722F37] text-[#F5EEDF] shadow-xs'
                      : 'bg-transparent text-[#3A1F23] hover:bg-[#DDD0B8] border border-[#B7A89A]'
                  }`}
                >
                  {formattedDate}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Doctor Cards List - Natural vertical flow without nested scrollbox */}
      <div className="divide-y divide-[#B7A89A]/40">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-[#6E5A54]">
            Loading doctors and availability schedule...
          </div>
        ) : doctors.length === 0 ? (
          <div className="p-8 text-center text-xs text-[#6E5A54]">
            No doctors found in clinic database.
          </div>
        ) : (
          doctors.map((doctor) => {
            const currentSlots = (doctor.slots_by_date && doctor.slots_by_date[selectedDateStr]) || [];

            return (
              <div key={doctor.id} className="p-4 sm:p-5 hover:bg-[#DDD0B8]/30 transition-colors">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  {/* Doctor Info */}
                  <div className="space-y-1 min-w-0 flex-1">
                    {/* Name on ONE line with speciality pill beside it */}
                    <div className="flex items-center space-x-2.5 flex-nowrap">
                      <h3 className="text-sm font-serif font-bold text-[#722F37] tracking-tight whitespace-nowrap shrink-0">
                        {doctor.name}
                      </h3>
                      <span className="text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-[#DDD0B8] text-[#3A1F23] border border-[#B7A89A] shrink-0">
                        {doctor.speciality}
                      </span>
                    </div>

                    {/* Room and experience in one muted line */}
                    <div className="text-xs text-[#6E5A54]">
                      <span>{doctor.room}</span>
                      <span className="mx-1.5 opacity-60">•</span>
                      <span>{doctor.experience} experience</span>
                    </div>

                    {/* Description kept to one truncated line */}
                    {doctor.bio && (
                      <p className="text-xs text-[#6E5A54] truncate max-w-md pt-0.5">
                        {doctor.bio}
                      </p>
                    )}
                  </div>

                  {/* Available Slots: 3-column grid so 6 slots form 3+3 and 5 slots form 3+2 */}
                  <div className="lg:text-right shrink-0">
                    <div className="text-[11px] text-[#6E5A54] font-medium mb-1.5 flex items-center lg:justify-end space-x-1">
                      <Clock className="w-3 h-3 text-[#722F37]" />
                      <span>
                        {currentSlots.length > 0
                          ? `${currentSlots.length} slots open`
                          : 'Fully booked'}
                      </span>
                    </div>

                    {currentSlots.length > 0 ? (
                      <div className="grid grid-cols-3 gap-1.5 w-full sm:w-[230px]">
                        {currentSlots.map((slot) => (
                          <span
                            key={slot}
                            className="px-1.5 py-0.5 text-center text-[11px] font-sans font-medium rounded-[5px] bg-transparent border border-[#B7A89A] text-[#3A1F23] hover:bg-[#722F37] hover:text-[#F5EEDF] hover:border-[#722F37] transition-colors cursor-default whitespace-nowrap"
                          >
                            {slot}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-xs italic text-[#6E5A54]">
                        No open slots for this date
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
