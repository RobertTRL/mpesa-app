import { supabase } from '../lib/supabase'

export function waitForPayment(checkoutId, timeoutMs = 60000) {
    
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      subscription.unsubscribe()
      reject(new Error('Payment confirmation timed out. Check your M-Pesa messages.'))
    }, timeoutMs)
    const subscription = supabase
      .channel(`payment-${checkoutId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'mpesa_payments',
          filter: `checkout_request_id=eq.${checkoutId}`,
        },
        (payload) => {
          clearTimeout(timeout)
          subscription.unsubscribe()
          resolve(payload.new)
        }
      )
      .subscribe()
  })
}