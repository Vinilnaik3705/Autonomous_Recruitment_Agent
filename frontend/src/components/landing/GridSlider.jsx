import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

// Integration items with real logos and names - move outside to avoid re-creation
const gridItems = [
  { name: 'n8n', color: 'from-orange-400 to-red-500', logo: '/logos/n8n-color.png' },
  { name: 'Google Meet', color: 'from-blue-400 to-cyan-500', logo: '/logos/google-meet.svg' },
  { name: 'Brevo', color: 'from-blue-500 to-indigo-600', logo: '/logos/Brevo_idgQGSgZ6E_1.png' },
  { name: 'Gmail', color: 'from-red-400 to-pink-500', logo: '/logos/gmail.svg' },
  { name: 'Slack', color: 'from-purple-400 to-pink-500', logo: '/logos/slack.svg' },
  { name: 'Teams', color: 'from-indigo-400 to-blue-500', logo: '/logos/microsoft_office_teams_logo_icon_145726.png' },
  { name: 'Zoom', color: 'from-blue-400 to-blue-600', logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Zoom_Video_Communications_logo.svg/512px-Zoom_Video_Communications_logo.svg.png' },
  { name: 'WhatsApp', color: 'from-green-400 to-emerald-500', logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/WhatsApp.svg/512px-WhatsApp.svg.png' },
  { name: 'LinkedIn', color: 'from-blue-600 to-blue-800', logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/LinkedIn_logo_initials.png/480px-LinkedIn_logo_initials.png' },
]

export default function GridSlider() {
  const [rotationIndex, setRotationIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setRotationIndex((prev) => (prev + 1) % gridItems.length)
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  const getItemIndex = (baseIdx) => (baseIdx + rotationIndex) % gridItems.length

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, scale: 0.8 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: { duration: 0.6 },
    },
  }

  return (
    <section id="gallery" className="py-24 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-white to-gray-50/50">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 tracking-tight">
            Build for Everyone
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Our platform seamlessly integrates with the tools your team already uses to manage recruitment and communication.
          </p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-2 md:grid-cols-3 gap-6 md:gap-10"
        >
          {/* 3x3 Grid with sliding effect */}
          {Array.from({ length: 9 }).map((_, idx) => {
            const itemIdx = getItemIndex(idx)
            const item = gridItems[itemIdx]
            return (
              <motion.div
                key={idx} // STABLE KEY FIX
                variants={itemVariants}
                whileHover={{
                  y: -12,
                  transition: { duration: 0.3 },
                }}
              >
                <div className={`relative aspect-square bg-gradient-to-br ${item.color} rounded-[2.5rem] overflow-hidden group cursor-pointer shadow-lg hover:shadow-2xl transition-all duration-300 border-4 border-white/20 p-8`}>
                  {/* Animated background elements */}
                  <div className="absolute inset-0 bg-grid-pattern opacity-10" />

                  {/* Icon/Logo */}
                  <div className="absolute inset-0 flex items-center justify-center group-hover:scale-110 transition-transform duration-300 p-10">
                    <motion.img
                      key={item.name} // Allows content change animation within the stable slot
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.5 }}
                      src={item.logo}
                      alt={item.name}
                      className="w-full h-full object-contain filter drop-shadow-xl"
                      onError={(e) => {
                        e.target.src = `https://ui-avatars.com/api/?name=${item.name}&background=random&color=fff&size=512`
                      }}
                    />
                  </div>

                  {/* Tool Name Label (visible on hover) */}
                  <div className="absolute bottom-4 left-0 right-0 text-center translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300">
                    <span className="text-white font-bold text-sm uppercase tracking-widest bg-black/20 backdrop-blur-sm px-3 py-1 rounded-full">
                      {item.name}
                    </span>
                  </div>

                  {/* Overlay on hover */}
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors duration-300" />

                  {/* Shine effect */}
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent opacity-0 group-hover:opacity-100"
                    animate={{ x: ['-200%', '200%'] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                  />
                </div>
              </motion.div>
            )
          })}
        </motion.div>

        {/* Carousel indicators */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          viewport={{ once: true }}
          className="flex justify-center gap-2 mt-12"
        >
          {Array.from({ length: Math.ceil(gridItems.length / 3) }).map((_, idx) => (
            <motion.button
              key={idx}
              onClick={() => setRotationIndex(idx * 3)}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${idx === Math.floor(rotationIndex / 3)
                ? 'bg-gradient-to-r from-orange-500 to-purple-600 w-6'
                : 'bg-gray-300 hover:bg-gray-400'
                }`}
              whileHover={{ scale: 1.3 }}
            />
          ))}
        </motion.div>
      </div>

      <style>{`
        @keyframes slide {
          0%, 100% { transform: translateX(0); }
          50% { transform: translateX(10px); }
        }

        .bg-grid-pattern {
          background-image: 
            linear-gradient(0deg, transparent 24%, rgba(255, 255, 255, 0.05) 25%, rgba(255, 255, 255, 0.05) 26%, transparent 27%, transparent 74%, rgba(255, 255, 255, 0.05) 75%, rgba(255, 255, 255, 0.05) 76%, transparent 77%, transparent),
            linear-gradient(90deg, transparent 24%, rgba(255, 255, 255, 0.05) 25%, rgba(255, 255, 255, 0.05) 26%, transparent 27%, transparent 74%, rgba(255, 255, 255, 0.05) 75%, rgba(255, 255, 255, 0.05) 76%, transparent 77%, transparent);
          background-size: 50px 50px;
        }
      `}</style>
    </section>
  )
}
