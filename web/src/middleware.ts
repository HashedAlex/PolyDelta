import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

// Define public routes that don't require authentication
const isPublicRoute = createRouteMatcher([
  '/',
  '/api/(.*)',
  '/match/(.*)',
])

export default clerkMiddleware(async (auth, request) => {
  // Allow public access to all routes for now
  // The protection is handled at component level via PremiumLock
  if (!isPublicRoute(request)) {
    // Future: can add route-level protection here
  }
})

export const config = {
  matcher: [
    // Skip Next.js internals and all static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}
