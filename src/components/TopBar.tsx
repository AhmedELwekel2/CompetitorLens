"use client";

import { Search, Bell, UserCircle } from "lucide-react";

export default function TopBar({ placeholder = "Search insights or reports...", hideActions = false, hideSearch = true }: { placeholder?: string; hideActions?: boolean; hideSearch?: boolean }) {
  return (
    <header className="sticky top-0 z-30 -mx-5 lg:-mx-8 px-5 lg:px-8 py-3 bg-bg-main/80 backdrop-blur-md border-b border-border/50 mb-6">
      <div className="flex items-center justify-between gap-4">
        {/* Spacer for mobile hamburger */}
        <div className="w-10 lg:hidden" />
        
        {/* Search */}
        {!hideSearch && <div className="flex-1 max-w-xl">
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted"
            />
            <input
              type="text"
              placeholder={placeholder}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-white text-[13.5px] text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all"
            />
          </div>
        </div>}

        {/* Actions */}
        {!hideActions && (
          <div className="flex items-center gap-2">
            <button className="relative p-2.5 rounded-xl hover:bg-white transition-colors text-text-secondary hover:text-text-primary">
              <Bell size={19} strokeWidth={1.8} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full" />
            </button>
            <button className="p-2.5 rounded-xl hover:bg-white transition-colors text-text-secondary hover:text-text-primary">
              <UserCircle size={19} strokeWidth={1.8} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
}