import React from 'react'
import { motion } from 'framer-motion'
import { Zap as ZapIcon, Database, Layout, Rocket, ExternalLink } from 'lucide-react'

const resources = [
    {
        id: 'n8n',
        icon: ZapIcon,
        title: 'n8n Automation',
        description: 'Official n8n documentation for nodes, workflows, and production deployments.',
        linkText: 'n8n Docs',
        url: 'https://docs.n8n.io/',
        color: 'blue'
    },
    {
        id: 'fastapi',
        icon: Rocket,
        title: 'FastAPI Backend',
        description: 'Explore the high-performance Python framework powering our recruitment API.',
        linkText: 'FastAPI Docs',
        url: 'https://fastapi.tiangolo.com/',
        color: 'purple'
    },
    {
        id: 'postgres',
        icon: Database,
        title: 'PostgreSQL',
        description: 'Reference documentation for the advanced relational database used for candidate data.',
        linkText: 'Postgres Docs',
        url: 'https://www.postgresql.org/docs/',
        color: 'orange'
    },
    {
        id: 'ui',
        icon: Layout,
        title: 'UI Components',
        description: 'Official documentation for Framer Motion, Lucide Icons, and React.',
        linkText: 'Framer Docs',
        url: 'https://www.framer.com/motion/',
        color: 'pink'
    }
]

const colorMap = {
    blue: { bg: 'bg-blue-50', text: 'text-blue-600', border: 'border-blue-100' },
    purple: { bg: 'bg-purple-50', text: 'text-purple-600', border: 'border-purple-100' },
    orange: { bg: 'bg-orange-50', text: 'text-orange-600', border: 'border-orange-100' },
    pink: { bg: 'bg-pink-50', text: 'text-pink-600', border: 'border-pink-100' }
}

export default function Resources() {
    return (
        <section id="resources" className="py-24 px-4 sm:px-6 lg:px-8 bg-white relative overflow-hidden">
            <div className="max-w-7xl mx-auto">
                <div className="flex flex-col lg:flex-row items-end justify-between mb-20 gap-8">
                    <div className="max-w-2xl">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            viewport={{ once: true }}
                            className="text-orange-600 font-black uppercase tracking-[0.3em] text-xs mb-4"
                        >
                            Developer Resources
                        </motion.div>
                        <h2 className="text-5xl md:text-6xl font-black text-gray-900 tracking-tight leading-none mb-6">
                            Official <br />
                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-pink-500">Documentation</span>
                        </h2>
                        <p className="text-xl text-gray-500 font-medium leading-relaxed max-w-lg">
                            Access the official documentation for the primary technologies powering the HRAutomate agent.
                        </p>
                    </div>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
                    {resources.map((res, idx) => {
                        const style = colorMap[res.color];
                        return (
                            <motion.a
                                key={idx}
                                href={res.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                viewport={{ once: true }}
                                className="group relative h-full block"
                            >
                                <div className="bg-white rounded-[2rem] p-8 border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-500 h-full flex flex-col">
                                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-6 border ${style.bg} ${style.text} ${style.border}`}>
                                        <res.icon size={24} />
                                    </div>
                                    <h3 className="text-xl font-black text-gray-900 mb-3 group-hover:text-orange-600 transition-colors">
                                        {res.title}
                                    </h3>
                                    <p className="text-gray-500 text-sm font-semibold leading-relaxed mb-8 flex-grow">
                                        {res.description}
                                    </p>
                                    <div className="flex items-center gap-2 text-gray-900 font-black text-xs uppercase tracking-widest group/link">
                                        {res.linkText}
                                        <ExternalLink size={14} className="group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
                                    </div>
                                </div>
                            </motion.a>
                        );
                    })}
                </div>

                {/* Newsletter Mini-CTA */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    className="mt-20 p-10 bg-gray-900 rounded-[2.5rem] flex flex-col md:flex-row items-center justify-between gap-8"
                >
                    <div className="text-center md:text-left">
                        <h4 className="text-2xl font-black text-white mb-2">Join the HR Revolution</h4>
                        <p className="text-gray-400 font-medium">Get the latest recruitment AI insights delivered to your inbox.</p>
                    </div>
                    <div className="flex w-full md:w-auto gap-3">
                        <input
                            type="email"
                            placeholder="your@email.com"
                            className="bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-white w-full md:w-64 focus:outline-none focus:border-orange-500 transition-colors"
                        />
                        <button className="bg-white text-gray-900 px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-xs hover:bg-orange-50 transition-colors">
                            Subscribe
                        </button>
                    </div>
                </motion.div>
            </div>
        </section>
    )
}
