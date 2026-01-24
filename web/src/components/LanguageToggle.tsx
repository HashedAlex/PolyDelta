"use client"

import { useLanguage } from '@/contexts/LanguageContext'

interface LanguageToggleProps {
  className?: string
}

export function LanguageToggle({ className = '' }: LanguageToggleProps) {
  const { language, toggleLanguage } = useLanguage()

  return (
    <button
      onClick={toggleLanguage}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#21262d] hover:bg-[#30363d] border border-[#30363d] transition-colors text-sm ${className}`}
      title={language === 'en' ? 'Switch to Chinese' : '切换到英文'}
    >
      <span className="text-base">🌐</span>
      <span className="text-[#8b949e] font-medium">
        {language === 'en' ? 'EN' : '中'}
      </span>
    </button>
  )
}
