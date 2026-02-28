import React from 'react'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'

const integrations = [
  {
    name: 'n8n',
    label: 'Workflow Automation',
    logo: '/logos/n8n-color.png'
  },
  {
    name: 'Google Meet',
    label: 'Seamless Video Meetings',
    logo: '/logos/google-meet.svg'
  },
  {
    name: 'Brevo',
    label: 'Marketing Automation',
    logo: '/logos/Brevo_idgQGSgZ6E_1.png'
  },
  {
    name: 'Microsoft Teams',
    label: 'Enterprise Collaboration',
    logo: '/logos/microsoft_office_teams_logo_icon_145726.png'
  },
  {
    name: 'Gmail',
    label: 'Email Notifications',
    logo: '/logos/gmail.svg'
  },
  {
    name: 'Slack',
    label: 'Team Communication',
    logo: '/logos/slack.svg'
  },
]

export default function Integrations() {
  const [rotationOffset, setRotationOffset] = React.useState(0)
  const [hoveredIndex, setHoveredIndex] = React.useState(null)
  const rotationActive = React.useRef(true)

  // Continuous rotation loop
  React.useEffect(() => {
    let animationFrameId;
    const animate = () => {
      if (rotationActive.current) {
        setRotationOffset(prev => (prev + 0.1) % 360)
      }
      animationFrameId = requestAnimationFrame(animate)
    }
    animate()
    return () => cancelAnimationFrame(animationFrameId)
  }, [])

  // Calculate center index based on rotation
  const centerIndex = React.useMemo(() => {
    const total = integrations.length
    const angleStep = 360 / total

    let closestIdx = 0
    let maxDiff = -1000

    for (let i = 0; i < total; i++) {
      const angle = (i * angleStep + rotationOffset) % 360
      const rad = (angle - 90) * (Math.PI / 180)
      const y = Math.sin(rad)
      if (y > maxDiff) {
        maxDiff = y
        closestIdx = i
      }
    }
    return closestIdx
  }, [rotationOffset])

  // Displayed info is prioritized by manual hover
  const activeIndex = hoveredIndex !== null ? hoveredIndex : centerIndex

  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8 bg-white overflow-hidden">
      <div className="max-w-7xl mx-auto text-center relative">
        <div className="flex justify-center mb-10">
          <div className="w-14 h-14 bg-white rounded-2xl border border-gray-100 flex items-center justify-center p-3 shadow-sm hover:shadow-md transition-shadow">
            <div className="w-full h-full bg-orange-50 rounded-xl flex items-center justify-center">
              <Zap size={24} className="text-orange-500 fill-orange-500" />
            </div>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="mb-24"
        >
          <h2 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 tracking-tight leading-tight">
            Integrate with your existing<br />tools in seconds
          </h2>
        </motion.div>

        <div
          className="relative h-[850px] flex items-end justify-center perspective-2000"
          onMouseLeave={() => setHoveredIndex(null)}
        >
          <div className="absolute inset-0 flex items-center justify-center -translate-y-20">
            {integrations.map((item, idx) => {
              const total = integrations.length
              const angleStep = 360 / total
              const currentAngle = (idx * angleStep + rotationOffset) % 360
              const angleRad = (currentAngle - 90) * (Math.PI / 180)

              const radiusX = 500
              const radiusY = 200

              const x = Math.cos(angleRad) * radiusX
              const y = Math.sin(angleRad) * radiusY

              // Enhanced Visibility: Back items are now brighter (opacity min 0.4)
              const opacity = Math.sin(angleRad) > 0 ? 1 : 0.4
              const zIndex = Math.floor(Math.sin(angleRad) * 100) + 100
              const isActive = activeIndex === idx

              return (
                <motion.div
                  key={idx}
                  style={{ x, y, zIndex, opacity }}
                  animate={{
                    // Decreased size for a more subtle look
                    scale: isActive ? 1.25 : 0.85,
                    rotateY: x * 0.05,
                  }}
                  whileHover={{ scale: 1.35 }}
                  className="absolute cursor-pointer"
                  onMouseEnter={() => {
                    setHoveredIndex(idx)
                    rotationActive.current = false
                  }}
                  onMouseLeave={() => {
                    setHoveredIndex(null)
                    rotationActive.current = true
                  }}
                >
                  <div className={`
                    w-40 h-40 bg-white/95 rounded-[3rem] border border-gray-100 
                    flex items-center justify-center p-8 transition-all duration-300
                    ${isActive ? 'shadow-[0_40px_80px_-15px_rgba(0,0,0,0.12)] border-white ring-4 ring-gray-50/20' : 'shadow-lg'}
                  `}>
                    <img
                      src={item.logo}
                      alt={item.name}
                      onError={(e) => {
                        e.target.src = `https://ui-avatars.com/api/?name=${item.name}&background=random&color=fff&size=512`
                      }}
                      className={`w-full h-full object-contain transition-all duration-300 ${isActive ? 'scale-110' : ''}`}
                    />
                  </div>
                </motion.div>
              )
            })}

            {/* Labels centered in the middle of the carousel */}
            <motion.div
              key={activeIndex}
              initial={{ opacity: 0, scale: 0.9, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="absolute pointer-events-none text-center"
            >
              <h3 className="text-4xl md:text-5xl font-extrabold text-gray-900 mb-2 tracking-tight">
                {integrations[activeIndex].name}
              </h3>
              <p className="text-gray-500 text-xl font-medium">
                {integrations[activeIndex].label}
              </p>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  )
}
