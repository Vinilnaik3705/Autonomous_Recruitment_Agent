import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, Calendar, MessageSquare, Rocket, Brain, Shield, X, Check, ArrowRight, Sparkles } from 'lucide-react'

const featureDetails = {
  'AI Resume Screening': {
    overview: 'Find the perfect fit faster with intelligent candidate matching.',
    features: [
      'Instant ranking of candidates based on job relevance.',
      'Comprehensive skill gap analysis for every profile.',
      'Automated extraction of contact details and education history.',
      'Visual match scores to help prioritize your review queue.'
    ],
    highlights: ['Precision Matching', 'Skill Discovery', 'Instant Ranking'],
    bg: 'bg-blue-500',
    text: 'text-blue-500'
  },
  'Smart Scheduling': {
    overview: 'Eliminate the back-and-forth of interview coordination.',
    features: [
      'Synchronize with your team\'s existing calendars in real-time.',
      'Automatically find the best time slots for multi-stage interviews.',
      'Send automated meeting invites and confirmation emails.',
      'Seamlessly handle rescheduling requests without manual tracking.'
    ],
    highlights: ['Calendar Sync', 'Automated Invites', 'One-Click Rescheduling'],
    bg: 'bg-purple-500',
    text: 'text-purple-500'
  },
  'Feedback Collection': {
    overview: 'Make confident hiring decisions with structured team input.',
    features: [
      'Standardized scorecards to ensure fair and consistent evaluation.',
      'Collaborative environment for team-wide feedback sharing.',
      'Automated reminders for interviewers to submit their scores.',
      'Centralized view of all candidate evaluations and recommendations.'
    ],
    highlights: ['Structured Scoring', 'Team Alignment', 'Decision Support'],
    bg: 'bg-pink-500',
    text: 'text-pink-500'
  },
  'Onboarding Pipeline': {
    overview: 'Turn successful candidates into productive new hires.',
    features: [
      'Quickly generate professional offer letters with a single click.',
      'Track the status of every onboarding task in one central hub.',
      'Automated email notifications for both HR and new employees.',
      'Standardized workflows for a consistent new-hire experience.'
    ],
    highlights: ['Offer Automation', 'Task Tracking', 'Smooth Transitions'],
    bg: 'bg-orange-500',
    text: 'text-orange-500'
  },
  'Secure & Compliant': {
    overview: 'Your data is protected by industry-leading security standards.',
    features: [
      'Secure access controls tailored to specific team roles.',
      'End-to-end protection for sensitive candidate and company info.',
      'Reliable data storage with frequent automated backups.',
      'Privacy-first approach to handling personal candidate data.'
    ],
    highlights: ['Data Privacy', 'Role-Based Access', 'Reliable Security'],
    bg: 'bg-green-500',
    text: 'text-green-500'
  },
  'Analytics Dashboard': {
    overview: 'Measure success and optimize your hiring performance.',
    features: [
      'Real-time visibility into every stage of your hiring pipeline.',
      'Track time-to-hire and referral conversion metrics.',
      'Identify bottlenecks in the recruitment process instantly.',
      'Data-driven reports to share with stakeholders and leadership.'
    ],
    highlights: ['Pipeline Visibility', 'Performance Metrics', 'Strategic Insights'],
    bg: 'bg-red-500',
    text: 'text-red-500'
  }
}

export default function Features() {
  const [selectedFeature, setSelectedFeature] = useState(null)

  const features = [
    {
      icon: Brain,
      title: 'AI Resume Screening',
      description: 'Intelligent resume analysis with smart candidate matching and scoring',
      color: 'from-blue-400 to-blue-600',
    },
    {
      icon: Calendar,
      title: 'Smart Scheduling',
      description: 'Automated interview scheduling with calendar integration',
      color: 'from-purple-400 to-purple-600',
    },
    {
      icon: MessageSquare,
      title: 'Feedback Collection',
      description: 'Comprehensive feedback forms for all interview rounds',
      color: 'from-pink-400 to-pink-600',
    },
    {
      icon: Rocket,
      title: 'Onboarding Pipeline',
      description: 'Streamlined onboarding process for new hires',
      color: 'from-orange-400 to-orange-600',
    },
    {
      icon: Shield,
      title: 'Secure & Compliant',
      description: 'Enterprise-grade security with role-based access control',
      color: 'from-green-400 to-green-600',
    },
    {
      icon: FileText,
      title: 'Analytics Dashboard',
      description: 'Real-time insights and recruitment metrics tracking',
      color: 'from-red-400 to-red-600',
    },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, ease: [0.22, 1, 0.36, 1] },
    },
  }

  return (
    <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 bg-white overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-20"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-orange-50 text-orange-600 text-sm font-bold mb-6 tracking-wide uppercase">
            <Sparkles size={16} />
            <span>Advanced Platform Features</span>
          </div>
          <h2 className="text-5xl md:text-6xl font-black text-gray-900 mb-6 tracking-tight">
            Powerful Features Built for You
          </h2>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto font-medium leading-relaxed">
            Everything you need to streamline your entire recruitment process,
            backed by sophisticated engineering.
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-8"
        >
          {features.map((feature, idx) => (
            <motion.button
              key={idx}
              variants={itemVariants}
              whileHover={{ y: -8 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedFeature(feature.title)}
              className="group relative text-left w-full outline-none focus-visible:ring-4 focus-visible:ring-orange-500/30 rounded-[2.5rem] transition-all"
              aria-label={`Learn more about ${feature.title}`}
            >
              {/* 3D Background */}
              <div className="absolute inset-0 bg-gray-50/50 rounded-[2.5rem] border border-gray-100 transform transition-all group-hover:scale-[1.03] group-hover:bg-white duration-500 group-hover:shadow-[0_40px_80px_-15px_rgba(0,0,0,0.08)]" />

              {/* Card Content */}
              <div className="relative p-10 h-full flex flex-col">
                {/* Icon */}
                <div className={`w-16 h-16 bg-gradient-to-br ${feature.color} rounded-2xl flex items-center justify-center mb-8 shadow-lg group-hover:scale-110 group-hover:rotate-3 transition duration-500`}>
                  <feature.icon size={32} className="text-white" />
                </div>

                <h3 className="text-2xl font-black text-gray-900 mb-4 group-hover:text-orange-500 transition-colors duration-300">
                  {feature.title}
                </h3>
                <p className="text-gray-500 font-medium leading-relaxed flex-grow">
                  {feature.description}
                </p>

                <div className="mt-8 flex items-center gap-2 text-sm font-black uppercase tracking-widest text-gray-400 group-hover:text-orange-600 transition-colors duration-300">
                  <span>What's Been Done</span>
                  <ArrowRight size={16} className="transform group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </motion.button>
          ))}
        </motion.div>
      </div>

      {/* Feature Detail Overlay */}
      <AnimatePresence>
        {selectedFeature && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 lg:p-8">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedFeature(null)}
              className="absolute inset-0 bg-gray-900/60 backdrop-blur-md"
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-4xl bg-white rounded-[3rem] shadow-2xl overflow-hidden flex flex-col lg:flex-row min-h-[500px]"
            >
              {/* Left Panel: Feature Theme */}
              <div className={`lg:w-1/3 ${featureDetails[selectedFeature].bg} p-12 flex flex-col justify-between text-white relative overflow-hidden`}>
                <div className="relative z-10">
                  <div className="w-16 h-16 bg-white/20 backdrop-blur-xl rounded-2xl flex items-center justify-center mb-8">
                    {React.createElement(features.find(f => f.title === selectedFeature)?.icon || Brain, { size: 32 })}
                  </div>
                  <h2 className="text-4xl font-black leading-tight mb-4">{selectedFeature}</h2>
                  <p className="text-white/80 font-medium">{featureDetails[selectedFeature].overview}</p>
                </div>

                <div className="relative z-10 space-y-3">
                  {featureDetails[selectedFeature].highlights.map((h, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs font-black uppercase tracking-widest bg-white/10 p-3 rounded-xl border border-white/10">
                      <Check size={14} className="text-white" />
                      {h}
                    </div>
                  ))}
                </div>

                {/* Decorative circles */}
                <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
                <div className="absolute -top-24 -right-24 w-64 h-64 bg-black/10 rounded-full blur-3xl" />
              </div>

              {/* Right Panel: Content */}
              <div className="lg:w-2/3 p-12 lg:p-16 flex flex-col bg-gray-50 relative">
                <button
                  onClick={() => setSelectedFeature(null)}
                  className="absolute top-8 right-8 w-12 h-12 rounded-2xl bg-white border border-gray-100 flex items-center justify-center text-gray-400 hover:text-gray-900 hover:shadow-lg transition-all active:scale-90"
                >
                  <X size={24} />
                </button>

                <div className="flex-grow">
                  <div className="flex items-center gap-3 mb-8">
                    <div className={`w-2 h-2 rounded-full ${featureDetails[selectedFeature].bg}`} />
                    <span className="text-xs font-black uppercase tracking-[0.2em] text-gray-400">Platform Capabilities</span>
                  </div>

                  <div className="space-y-6">
                    {featureDetails[selectedFeature].features.map((item, i) => (
                      <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.1 + (i * 0.1) }}
                        key={i}
                        className="flex gap-4 group"
                      >
                        <div className="flex-shrink-0 w-8 h-8 rounded-xl bg-white border border-gray-100 shadow-sm flex items-center justify-center group-hover:scale-110 transition-transform">
                          <Check size={14} className={`${featureDetails[selectedFeature].text}`} />
                        </div>
                        <p className="text-gray-600 font-medium leading-relaxed pt-1">
                          {item}
                        </p>
                      </motion.div>
                    ))}
                  </div>
                </div>

                <div className="mt-12 pt-12 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-6">
                  <div className="text-center sm:text-left">
                    <p className="text-gray-400 text-xs font-bold uppercase tracking-widest mb-1">Status</p>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                      <span className="font-black text-gray-900 text-sm">Feature Fully Deployed</span>
                    </div>
                  </div>

                  <button
                    onClick={() => window.location.href = '/login'}
                    className={`px-8 py-4 bg-gray-900 text-white rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] hover:${featureDetails[selectedFeature].bg} transition-colors shadow-xl active:scale-95`}
                  >
                    Launch Platform
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </section>
  )
}
