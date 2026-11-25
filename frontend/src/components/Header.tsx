import React from 'react';
import { Phone, RotateCcw } from 'lucide-react';

interface HeaderProps {
  backendOnline: boolean;
  onStartCall: () => void;
  onResetDb: () => void;
  isResetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  backendOnline,
  onStartCall,
  onResetDb,
  isResetting
}) => {
  return (
    <header className="border-b border-[#B7A89A] bg-[#E8DCC6] m-0 p-0 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-5 pb-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Brand & Clinic Identity */}
        <div className="flex items-center space-x-3.5">
          <div className="w-10 h-10 rounded-[10px] bg-[#722F37] flex items-center justify-center text-[#F5EEDF] font-serif font-bold text-xl tracking-tight shrink-0 shadow-xs">
            A
          </div>
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-base sm:text-lg font-serif font-bold text-[#722F37] tracking-tight">
                Apollo Healthcare Clinic
              </h1>
              <span className="text-[11px] font-sans font-medium px-2 py-0.5 rounded bg-[#DDD0B8] text-[#3A1F23] border border-[#B7A89A]">
                Voice Reception Desk
              </span>
            </div>
            <p className="text-xs text-[#6E5A54] mt-0.5">
              Automated Doctor Appointments & Schedule Assistant
            </p>
          </div>
        </div>

        {/* Status Indicators & Actions */}
        <div className="flex items-center space-x-3">
          {/* Live Indicator: Small burgundy dot with 'Live' */}
          <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-[#F1E8D6] border border-[#B7A89A] text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                backendOnline ? 'bg-[#722F37]' : 'bg-[#D98A7A]'
              }`}
            />
            <span className="text-[#3A1F23] font-medium">
              {backendOnline ? 'Live' : 'Offline'}
            </span>
          </div>

          {/* Secondary Action: Transparent with a 1px --line border and burgundy text */}
          <button
            onClick={onResetDb}
            disabled={isResetting}
            title="Reset appointments and doctors to initial demo state"
            className="flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-[#722F37] bg-transparent hover:bg-[#DDD0B8] border border-[#B7A89A] rounded-[8px] transition-colors disabled:opacity-50 cursor-pointer"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            <span>Reset Data</span>
          </button>

          {/* Primary Action: Burgundy fill, cream text */}
          <button
            onClick={onStartCall}
            className="flex items-center space-x-2 px-4 py-1.5 text-xs font-semibold text-[#F5EEDF] bg-[#722F37] hover:bg-[#5E242C] active:bg-[#4D1C23] rounded-[8px] transition-colors cursor-pointer tracking-tight shadow-xs"
          >
            <Phone className="w-3.5 h-3.5 text-[#F5EEDF]" />
            <span>Try Call</span>
          </button>
        </div>
      </div>
    </header>
  );
};
