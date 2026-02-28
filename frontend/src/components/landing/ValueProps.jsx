import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Cpu } from 'lucide-react'

const AutomationDemo = () => {
    const [step, setStep] = React.useState(0)
    const steps = [
        { label: 'Analyzing Resume', status: 'Extracting skills...', color: 'bg-blue-500' },
        { label: 'Semantic Matching', status: 'Matching index: 94%', color: 'bg-purple-500' },
        { label: 'Smart Scheduling', status: 'Syncing calendars...', color: 'bg-green-500' },
        { label: 'Final Decision', status: 'Recommendation: PASS', color: 'bg-orange-500' }
    ]

    React.useEffect(() => {
        const timer = setInterval(() => {
            setStep((prev) => (prev + 1) % steps.length)
        }, 3000)
        return () => clearInterval(timer)
    }, [])

    return (
        <div className="relative w-full max-w-lg mx-auto bg-gray-900 rounded-[2.5rem] p-8 shadow-2xl border border-white/10 overflow-hidden">
            {/* App Header Mockup */}
            <div className="flex items-center justify-between mb-8 pb-4 border-b border-white/5">
                <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
                </div>
                <div className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Agent Console v2.0</div>
            </div>

            <div className="space-y-6">
                {/* Status Bar */}
                <div className="flex items-center justify-between bg-white/5 p-4 rounded-2xl border border-white/5">
                    <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${steps[step].color} animate-pulse`} />
                        <span className="text-sm font-bold text-white">{steps[step].label}</span>
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{steps[step].status}</span>
                </div>

                {/* Visualizer Area */}
                <div className="relative h-48 bg-black/40 rounded-3xl border border-white/5 flex items-center justify-center overflow-hidden">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={step}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 1.1 }}
                            className="text-center p-6"
                        >
                            {step === 0 && (
                                <div className="space-y-4">
                                    <div className="flex gap-2 justify-center">
                                        {[...Array(3)].map((_, i) => (
                                            <motion.div
                                                key={i}
                                                animate={{ y: [0, -10, 0] }}
                                                transition={{ delay: i * 0.1, repeat: Infinity }}
                                                className="w-10 h-14 bg-white/10 rounded-lg border border-white/10"
                                            />
                                        ))}
                                    </div>
                                    <div className="text-xs text-blue-400 font-mono">SCANNING_PDF_BLOBS...</div>
                                </div>
                            )}
                            {step === 1 && (
                                <div className="relative">
                                    <div className="text-4xl font-black text-purple-400 mb-2">94%</div>
                                    <div className="text-[10px] text-gray-500 uppercase tracking-widest">Semantic Score</div>
                                    <motion.div
                                        animate={{ scale: [1, 1.2, 1] }}
                                        transition={{ repeat: Infinity }}
                                        className="absolute -top-4 -right-4 w-8 h-8 bg-purple-500/20 rounded-full blur-xl"
                                    />
                                </div>
                            )}
                            {step === 2 && (
                                <div className="space-y-3">
                                    <div className="flex gap-1 justify-center">
                                        {[...Array(5)].map((_, i) => (
                                            <div key={i} className="w-8 h-8 bg-green-500/20 rounded-md border border-green-500/20" />
                                        ))}
                                    </div>
                                    <div className="text-[10px] text-green-400 font-bold uppercase tracking-widest">Slot Confirmed: Mon 10AM</div>
                                </div>
                            )}
                            {step === 3 && (
                                <motion.div
                                    initial={{ rotate: -10, scale: 0.5 }}
                                    animate={{ rotate: 0, scale: 1 }}
                                    className="bg-orange-500 text-white px-8 py-3 rounded-2xl text-xl font-black shadow-lg shadow-orange-500/40"
                                >
                                    HIRED
                                </motion.div>
                            )}
                        </motion.div>
                    </AnimatePresence>

                    {/* Background Grid Decoration */}
                    <div className="absolute inset-0 grid grid-cols-6 grid-rows-4 opacity-5 pointer-events-none">
                        {[...Array(24)].map((_, i) => (
                            <div key={i} className="border border-white/20" />
                        ))}
                    </div>
                </div>

                {/* Log Window */}
                <div className="bg-black/20 rounded-2xl p-4 border border-white/5 font-mono text-[9px] text-gray-500 leading-relaxed uppercase h-[90px]">
                    <div>{">"} INIT AGENT_CORE... OK</div>
                    {step >= 0 && <div className="text-blue-500/80">{">"} PROCESSING CANDIDATE_ID: 9X2J</div>}
                    {step >= 1 && <div className="text-purple-500/80">{">"} VECTOR_SEARCH_COMPLETED</div>}
                    {step >= 2 && <div className="text-green-500/80">{">"} CALENDAR_WEBHOOK: EVENT_CREATED</div>}
                </div>
            </div>
        </div>
    )
}

export default function ValueProps() {
    return (
        <section id="pillars" className="py-24 px-4 sm:px-6 lg:px-8 bg-white relative overflow-hidden">
            <div className="max-w-7xl mx-auto">
                <div className="flex flex-col lg:flex-row items-center justify-between mb-24 gap-16">
                    <div className="max-w-2xl">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            className="text-blue-600 font-black uppercase tracking-[0.3em] text-xs mb-4"
                        >
                            The Intelligence Layer
                        </motion.div>
                        <h2 className="text-5xl md:text-7xl font-black text-gray-900 tracking-tight leading-[0.9] mb-8">
                            The Future of <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">Recruitment</span>
                        </h2>
                        <p className="text-xl text-gray-500 font-medium leading-relaxed mb-10 max-w-lg">
                            Traditional software manages data. Our AI Agent manages your growth by taking ownership of the hiring pipeline with sub-second precision.
                        </p>
                        <div className="flex flex-wrap gap-4">
                            <div className="px-6 py-3 bg-gray-50 rounded-2xl border border-gray-100 text-sm font-bold text-gray-900 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                Better Parsing Accuracy
                            </div>
                            <div className="px-6 py-3 bg-gray-50 rounded-2xl border border-gray-100 text-sm font-bold text-gray-900 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                                Auto-Scheduling Active
                            </div>
                        </div>
                    </div>

                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                        className="w-full lg:w-1/2"
                    >
                        <AutomationDemo />
                    </motion.div>
                </div>

            </div>

            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-blue-50 rounded-full blur-[120px] -mr-96 -mt-96 opacity-50" />
            <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-purple-50 rounded-full blur-[100px] -ml-80 -mb-80 opacity-50" />
        </section>
    )
}
