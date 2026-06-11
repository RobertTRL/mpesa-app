import { supabase } from '../lib/supabase.js'

export function waitForPayment(checkoutId, timeoutMs = 60000) {
  return new Promise(async (resolve, reject) => {

    // 1. Check if payment already landed before we subscribe
    const { data: existing } = await supabase
      .from('mpesa_payments')
      .select('*')
      .eq('checkout_request_id', checkoutId)
      .maybeSingle()

    if (existing) {
      resolve(existing)
      return
    }

    // 2. Not there yet — subscribe and wait
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