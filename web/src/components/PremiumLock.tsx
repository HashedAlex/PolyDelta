"use client"

import { useUser, SignInButton } from '@clerk/nextjs'
import { ReactNode } from 'react'

interface PremiumLockProps {
  children: ReactNode
  blurStrength?: number  // Default 6px
  ctaText?: string       // Custom CTA text
}

export function PremiumLock({
  children,
  blurStrength = 6,
  ctaText = "Sign in to view Profit & Analysis"
}: PremiumLockProps) {
  const { isSignedIn, isLoaded } = useUser()

  // While loading, show blurred content (safer default)
  if (!isLoaded) {
    return (
      <div className="relative">
        <div
          style={{
            filter: `blur(${blurStrength}px)`,
            pointerEvents: 'none',
            userSelect: 'none'
          }}
        >
          {children}
        </div>
      </div>
    )
  }

  // If signed in, show content normally
  if (isSignedIn) {
    return <>{children}</>
  }

  // If signed out, show blurred content with CTA overlay
  return (
    <div className="relative">
      {/* Blurred Content */}
      <div
        style={{
          filter: `blur(${blurStrength}px)`,
          pointerEvents: 'none',
          userSelect: 'none'
        }}
      >
        {children}
      </div>

      {/* CTA Overlay */}
      <div className="absolute inset-0 flex items-center justify-center bg-[#0d1117]/60 backdrop-blur-sm rounded-lg">
        <div className="text-center p-6">
          <div className="text-2xl mb-3">🔒</div>
          <p className="text-[#e6edf3] font-medium mb-4">{ctaText}</p>
          <SignInButton mode="modal">
            <button className="px-6 py-3 bg-[#238636] hover:bg-[#2ea043] text-white font-medium rounded-lg transition-colors flex items-center gap-2 mx-auto">
              <span>Sign In</span>
              <span>→</span>
            </button>
          </SignInButton>
        </div>
      </div>
    </div>
  )
}
