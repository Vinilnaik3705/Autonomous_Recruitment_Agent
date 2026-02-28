import React, { useState } from 'react'
import { motion } from 'framer-motion'

export default function ScrollingCarousel() {
  const [activeIndex, setActiveIndex] = useState(0)

  // Sample team member data with gradients instead of images
  const teamMembers = [
    {
      name: 'Sarah Johnson',
      role: 'HR Director',
      company: 'Tech Solutions Inc',
      color: 'from-blue-400 to-cyan-500',
      testimonial: 'Transformed our hiring process completely',
    },
    {
      name: 'Michael Chen',
      role: 'Recruitment Manager',
      company: 'Global enterprises',
      color: 'from-purple-400 to-pink-500',
      testimonial: 'Best investment for our recruitment team',
    },
    {
      name: 'Emily Rodriguez',
      role: 'Talent Acquisition Lead',
      company: 'Innovation Corp',
      color: 'from-green-400 to-emerald-500',
      testimonial: 'Reduced hiring time by 60%',
    },
    {
      name: 'David Kim',
      role: 'HR Operations Manager',
      company: 'Digital Pioneers',
      color: 'from-orange-400 to-red-500',
      testimonial: 'Exceptional customer support',
    },
    {
      name: 'Lisa Anderson',
      role: 'Chief People Officer',
      company: 'Future Systems',
      color: 'from-yellow-400 to-orange-500',
      testimonial: 'Seamless integration with our workflow',
    },
  ]

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
            Trusted by Leading Companies
          </h2>
          <p className="text-xl text-gray-600">
            Join hundreds of HR teams using HRAutomate
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left side - Scrolling carousel */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="relative h-[400px] md:h-[600px] overflow-hidden rounded-2xl"
          >
            <div className="relative w-full h-full p-4 overflow-hidden">
              {/* Image container with scroll effect */}
              <motion.div
                animate={{ y: -activeIndex * 280 }}
                transition={{ type: 'spring', stiffness: 100, damping: 15 }}
                className="space-y-6"
              >
                {teamMembers.map((member, idx) => (
                  <motion.div
                    key={idx}
                    className="w-full"
                    whileHover={{ scale: 1.02 }}
                  >
                    {/* Profile card with gradient background instead of image */}
                    <div className={`relative rounded-2xl overflow-hidden h-64 w-full cursor-pointer group border-4 transition-all duration-300 ${activeIndex === idx ? 'border-orange-500 shadow-xl' : 'border-transparent opacity-60 hover:opacity-100'}`}
                      onClick={() => setActiveIndex(idx)}
                    >
                      {/* Gradient background */}
                      <div className={`absolute inset-0 bg-gradient-to-br ${member.color}`} />

                      {/* Overlay */}
                      <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition duration-300" />

                      {/* Initials */}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-6xl font-bold text-white opacity-30">
                          {member.name.split(' ').map(n => n[0]).join('')}
                        </span>
                      </div>

                      {/* Info at bottom */}
                      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 text-white">
                        <h3 className="text-lg font-bold">{member.name}</h3>
                        <p className="text-sm text-gray-200">{member.role}</p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>

              {/* Scroll indicators */}
              <div className="absolute right-2 top-4 bottom-4 w-1.5 bg-gray-100 rounded-full overflow-hidden">
                <motion.div
                  animate={{ top: `${(activeIndex / (teamMembers.length - 1)) * 85}%` }}
                  transition={{ type: 'spring', stiffness: 100, damping: 15 }}
                  className="absolute w-full h-12 bg-gradient-to-b from-orange-500 to-purple-600 rounded-full shadow-sm"
                />
              </div>
            </div>
          </motion.div>

          {/* Right side - Current member details and navigation */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="space-y-6"
          >
            <motion.div
              key={activeIndex}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className={`w-16 h-16 bg-gradient-to-br ${teamMembers[activeIndex].color} rounded-lg mb-6`} />
              <h3 className="text-3xl font-bold text-gray-900 mb-2">
                {teamMembers[activeIndex].name}
              </h3>
              <p className="text-lg text-gray-600 mb-1">
                {teamMembers[activeIndex].role}
              </p>
              <p className="text-gray-500 mb-6">
                at {teamMembers[activeIndex].company}
              </p>

              {/* Rating */}
              <div className="flex items-center gap-2 mb-6">
                {[...Array(5)].map((_, i) => (
                  <span key={i} className="text-2xl text-yellow-400">★</span>
                ))}
                <span className="text-gray-600 ml-2">5.0</span>
              </div>

              {/* Testimonial */}
              <p className="text-xl text-gray-700 leading-relaxed mb-8 italic">
                "{teamMembers[activeIndex].testimonial}"
              </p>
            </motion.div>

            {/* Navigation dots */}
            <div className="flex gap-2 pt-6">
              {teamMembers.map((_, idx) => (
                <motion.button
                  key={idx}
                  onClick={() => setActiveIndex(idx)}
                  className={`w-3 h-3 rounded-full transition-all duration-300 ${idx === activeIndex
                      ? 'bg-gradient-to-r from-orange-500 to-purple-600 w-8'
                      : 'bg-gray-300 hover:bg-gray-400'
                    }`}
                  whileHover={{ scale: 1.2 }}
                  whileTap={{ scale: 0.9 }}
                />
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
