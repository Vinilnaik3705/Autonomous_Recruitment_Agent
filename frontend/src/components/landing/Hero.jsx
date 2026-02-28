import React from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, Zap, Users, BarChart3 } from 'lucide-react'

export default function Hero() {
  const floatingIcons = [
    { Icon: CheckCircle, label: 'Verification', x: -80, y: -60, color: 'from-purple-400 to-purple-600' },
    { Icon: Zap, label: 'Speed', x: 80, y: -80, color: 'from-yellow-400 to-yellow-600' },
    { Icon: Users, label: 'Collaboration', x: -100, y: 80, color: 'from-blue-400 to-blue-600' },
    { Icon: BarChart3, label: 'Analytics', x: 100, y: 60, color: 'from-orange-400 to-orange-600' },
  ]

  return (
    <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left side - Text */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 leading-tight mb-6">
              All-in-one HR
              <br />
              <span className="bg-gradient-to-r from-orange-500 to-purple-600 bg-clip-text text-transparent">
                platform
              </span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 leading-relaxed">
              Streamline your hiring process with AI-powered resume screening, intelligent interview scheduling,
              and comprehensive feedback collection. Everything you need to build great teams.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <a
                href="#pricing"
                className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-10 py-4 rounded-full font-bold hover:shadow-xl transition duration-300 uppercase tracking-widest text-sm text-center inline-block"
              >
                Start Free Trial
              </a>
            </div>
            {/* Trust badges */}
            <div className="mt-12 flex gap-6">
              <div>
                <p className="text-3xl font-bold text-gray-900">500+</p>
                <p className="text-gray-600">Companies Trust Us</p>
              </div>
              <div>
                <p className="text-3xl font-bold text-gray-900">50K+</p>
                <p className="text-gray-600">Candidates Placed</p>
              </div>
            </div>
          </motion.div>

          {/* Right side - 3D Floating Icons */}
          <motion.div
            className="relative h-96 md:h-full min-h-96"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            {/* Center element */}
            <motion.div
              className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2"
              animate={{
                y: [0, -20, 0],
              }}
              transition={{ duration: 4, repeat: Infinity }}
            >
              <div className="w-32 h-32 bg-gradient-to-br from-purple-400 to-purple-600 rounded-3xl flex items-center justify-center shadow-2xl">
                <CheckCircle size={64} className="text-white" />
              </div>
            </motion.div>

            {/* Floating icons around center */}
            {floatingIcons.map((item, idx) => (
              <motion.div
                key={idx}
                className="absolute"
                style={{
                  left: '50%',
                  top: '50%',
                  x: item.x,
                  y: item.y,
                }}
                animate={{
                  y: [item.y, item.y - 30, item.y],
                  x: [item.x, item.x + 10, item.x],
                }}
                transition={{
                  duration: 5 + idx,
                  repeat: Infinity,
                  ease: 'easeInOut',
                }}
              >
                <div className={`w-20 h-20 bg-gradient-to-br ${item.color} rounded-2xl flex items-center justify-center shadow-lg hover:shadow-xl transition`}>
                  <item.Icon size={40} className="text-white" />
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
