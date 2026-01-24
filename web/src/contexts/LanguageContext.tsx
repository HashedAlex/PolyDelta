"use client"

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import en from '@/locales/en.json'
import zh from '@/locales/zh.json'

type Language = 'en' | 'zh'

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  toggleLanguage: () => void
  t: (key: string) => string
}

const translations = { en, zh }

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>('en')

  // Load language preference from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('polydelta-lang') as Language
    if (saved && (saved === 'en' || saved === 'zh')) {
      setLanguageState(saved)
    }
  }, [])

  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
    localStorage.setItem('polydelta-lang', lang)
  }

  const toggleLanguage = () => {
    const newLang = language === 'en' ? 'zh' : 'en'
    setLanguage(newLang)
  }

  // Translation function with dot notation support
  const t = (key: string): string => {
    const keys = key.split('.')
    let result: unknown = translations[language]

    for (const k of keys) {
      if (result && typeof result === 'object' && k in result) {
        result = (result as Record<string, unknown>)[k]
      } else {
        // Fallback to English if key not found
        result = translations.en
        for (const fallbackKey of keys) {
          if (result && typeof result === 'object' && fallbackKey in result) {
            result = (result as Record<string, unknown>)[fallbackKey]
          } else {
            return key // Return key if not found in any language
          }
        }
        break
      }
    }

    return typeof result === 'string' ? result : key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}

// Shorthand hook for translation only
export function useTranslation() {
  const { t, language } = useLanguage()
  return { t, language }
}
