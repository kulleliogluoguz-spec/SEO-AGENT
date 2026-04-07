'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function TaxReportsRedirect() {
  const router = useRouter()
  useEffect(() => {
    router.replace('/dashboard/finance')
  }, [router])
  return (
    <div className="p-6 text-sm text-gray-500">
      Redirecting to Finance Intelligence…
    </div>
  )
}
