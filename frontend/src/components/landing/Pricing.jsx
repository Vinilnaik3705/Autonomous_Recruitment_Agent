import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, Sparkles } from 'lucide-react'

const plans = [
    {
        name: 'Starter',
        price: { USD: '0', INR: '0' },
        description: 'Perfect for small teams starting their automation journey.',
        features: [
            'Up to 100 resumes / month',
            'AI Resume Parsing',
            'Basic Email Integration',
            'Standard Support'
        ],
        cta: 'Get Started',
        highlight: false,
        color: 'gray'
    },
    {
        name: 'Professional',
        price: { USD: '49', INR: '3,999' },
        description: 'Advanced features for scaling recruitment teams.',
        features: [
            'Unlimited resumes',
            'Semantic Match Scoring',
            'Automated Scheduling',
            'Priority Support',
            'Full Integration Suite'
        ],
        cta: 'Start Free Trial',
        highlight: true,
        color: 'blue'
    },
    {
        name: 'Enterprise',
        price: 'Custom',
        description: 'Dedicated infrastructure and custom AI models.',
        features: [
            'Custom AI Model Training',
            'Dedicated Account Manager',
            'SLA & Security Audit',
            'On-premise Deployment',
            'API Access'
        ],
        cta: 'Contact Sales',
        highlight: false,
        color: 'gray'
    }
]

export default function Pricing() {
    const [currency, setCurrency] = useState('USD')

    const API_BASE = '/api'

    const handlePayment = async (plan) => {
        console.log(`Payment triggered for: ${plan.name} in ${currency}`)

        if (!window.Razorpay) {
            console.error("Razorpay SDK not found")
            alert('The payment system is currently unavailable. Please reload the page or try again in a few seconds.')
            return
        }

        try {
            // Determine amount (using nominal values for Starter/Enterprise if free/custom)
            let amount = 0
            if (plan.name === 'Starter') {
                amount = currency === 'USD' ? 1 : 50 // Nominal charge to show options
            } else if (plan.name === 'Enterprise') {
                amount = currency === 'USD' ? 99 : 8000 // Nominal charge for demo
            } else {
                amount = parseInt(plan.price[currency].toString().replace(',', ''))
            }

            console.log(`Initialising checkout for ${plan.name}: ${amount} ${currency}`)

            // 1a. Fetch Key ID (through Vite proxy → FastAPI)
            const keyResponse = await fetch(`${API_BASE}/payments/key-id`)
            const keyData = await keyResponse.json()
            const razorpayKey = keyData.key_id

            // 1b. Create Order in Backend
            const response = await fetch(`${API_BASE}/payments/create-order`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    amount: amount,
                    currency: currency,
                    receipt: `receipt_${plan.name.toLowerCase()}`
                })
            })

            const order = await response.json()
            if (!response.ok) {
                console.error("Backend Error:", order)
                throw new Error(order.detail || 'Failed to create order')
            }

            if (!order.id) {
                console.error("Order ID missing:", order)
                throw new Error('Transaction failed to start. Check backend logs.')
            }

            // 2. Initialize Razorpay Checkout
            const options = {
                key: razorpayKey,
                amount: order.amount,
                currency: order.currency,
                name: 'HRAutomate',
                description: `${plan.name} Plan Activation`,
                order_id: order.id,
                handler: async function (response) {
                    console.log("Payment authorized, verifying...")
                    const verifyRes = await fetch(`${API_BASE}/payments/verify-payment`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature
                        })
                    })
                    const result = await verifyRes.json()
                    if (result.status === 'success') {
                        alert(`Success! Your ${plan.name} plan is now active.`)
                        window.location.href = '/dashboard'
                    } else {
                        alert('Payment Verification Failed.')
                    }
                },
                prefill: {
                    name: 'Demo User',
                    email: 'user@hrautomate.com',
                    contact: '9999999999'
                },
                theme: {
                    color: '#2563eb'
                },
                modal: {
                    ondismiss: () => console.log("Checkout modal closed.")
                }
            }

            const rzp = new window.Razorpay(options)
            rzp.on('payment.failed', (resp) => {
                alert(`Payment failed: ${resp.error.description}`)
            })
            rzp.open()

        } catch (error) {
            console.error('Payment Error:', error)
            alert(`Payment Error: ${error.message}. Please ensure the backend server is running.`)
        }
    }

    return (
        <section id="pricing" className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50/50 relative z-10 scroll-mt-24">
            <div className="max-w-7xl mx-auto">
                <div className="text-center mb-16">
                    <motion.div
                        initial={{ opacity: 0 }}
                        whileInView={{ opacity: 1 }}
                        viewport={{ once: true }}
                        className="text-blue-600 font-black uppercase tracking-[0.3em] text-xs mb-4"
                    >
                        Transparent Pricing
                    </motion.div>
                    <h2 className="text-5xl md:text-6xl font-black text-gray-900 tracking-tight mb-6">
                        Plans that Grow with You
                    </h2>

                    {/* Currency Toggle */}
                    <div className="flex items-center justify-center gap-4 mt-8 relative z-20">
                        <button
                            type="button"
                            onClick={() => setCurrency('USD')}
                            className={`text-sm font-black tracking-widest uppercase transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg px-2 py-1 ${currency === 'USD' ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
                        >
                            USD
                        </button>
                        <button
                            type="button"
                            onClick={() => setCurrency(prev => prev === 'USD' ? 'INR' : 'USD')}
                            aria-label="Toggle currency between USD and INR"
                            className="w-14 h-7 bg-gray-200 rounded-full relative p-1 transition-colors duration-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <motion.div
                                animate={{ x: currency === 'USD' ? 0 : 28 }}
                                className="w-5 h-5 bg-white rounded-full shadow-md"
                            />
                        </button>
                        <button
                            type="button"
                            onClick={() => setCurrency('INR')}
                            className={`text-sm font-black tracking-widest uppercase transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg px-2 py-1 ${currency === 'INR' ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'}`}
                        >
                            INR
                        </button>
                    </div>
                </div>

                <div className="grid md:grid-cols-3 gap-8 relative z-10">
                    {plans.map((plan, idx) => (
                        <motion.div
                            key={idx}
                            initial={{ opacity: 0 }}
                            whileInView={{ opacity: 1 }}
                            transition={{ delay: idx * 0.1 }}
                            viewport={{ once: true }}
                            className={`relative bg-white rounded-[2.5rem] p-10 shadow-[0_20px_50px_-12px_rgba(0,0,0,0.05)] border-2 transition-all duration-500 hover:-translate-y-2 hover:z-30 hover:shadow-2xl ${plan.highlight ? 'border-blue-600 shadow-blue-500/10 z-20' : 'border-transparent z-10'}`}
                        >
                            {plan.highlight && (
                                <div className="absolute top-0 right-10 -translate-y-1/2 bg-blue-600 text-white px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest flex items-center gap-2 shadow-xl shadow-blue-600/30">
                                    <Sparkles size={12} />
                                    Most Popular
                                </div>
                            )}

                            <div className="mb-8">
                                <h3 className="text-2xl font-black text-gray-900 mb-2">{plan.name}</h3>
                                <p className="text-gray-500 text-sm font-medium">{plan.description}</p>
                            </div>

                            <div className="mb-8 flex items-baseline">
                                <span className="text-5xl font-black text-gray-900">
                                    {plan.name === 'Enterprise' ? '' : (currency === 'USD' ? '$' : '₹')}
                                    {plan.name === 'Enterprise' ? 'Custom' : plan.price[currency]}
                                </span>
                                {plan.name !== 'Enterprise' && <span className="text-gray-400 font-bold ml-2">/month</span>}
                            </div>

                            <div className="space-y-4 mb-10">
                                {plan.features.map((feature, fIdx) => (
                                    <div key={fIdx} className="flex items-center gap-3 text-left">
                                        <div className={`w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center ${plan.highlight ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-400'}`}>
                                            <Check size={12} strokeWidth={4} />
                                        </div>
                                        <span className="text-gray-600 text-sm font-semibold">{feature}</span>
                                    </div>
                                ))}
                            </div>

                            <button
                                type="button"
                                onClick={() => handlePayment(plan)}
                                aria-label={`${plan.cta} for ${plan.name} plan`}
                                className={`w-full py-5 rounded-2xl font-black uppercase tracking-widest text-sm transition-all duration-300 active:scale-95 cursor-pointer select-none focus:outline-none focus:ring-4 focus:ring-blue-500/50 z-40 relative pointer-events-auto ${plan.highlight ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-xl shadow-blue-500/20' : 'bg-gray-900 text-white hover:bg-black shadow-xl shadow-black/10'}`}>
                                {plan.cta}
                            </button>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    )
}
