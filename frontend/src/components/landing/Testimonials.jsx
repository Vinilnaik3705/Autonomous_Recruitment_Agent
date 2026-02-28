import React from 'react'
import { motion } from 'framer-motion'

const testimonials = [
  { name: 'Sarah Mitchell', title: 'HR Director', text: 'CoreShift has streamlined our HR processes, making onboarding and performance tracking effortless.' },
  { name: 'James Carter', title: 'HR Manager', text: 'The platform is easy to use, keeps everything in one place, and helps our team stay on top of things.' },
  { name: 'Olivia Park', title: 'Talent Lead', text: 'Excellent analytics and quick candidate screening — a game changer for our hiring.' },
]

export default function Testimonials() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-7xl mx-auto text-center">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} viewport={{ once: true }}>
          <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">Words of Appreciation</h2>
          <p className="text-xl text-gray-600 mb-8">Thousands of businesses, from startups to enterprises, use HRAutomate to hire better.</p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((t, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: idx * 0.1 }} className="bg-white rounded-2xl p-8 shadow-lg border border-gray-100">
              <div className="text-left mb-4">
                <h3 className="text-lg font-bold">{t.name}</h3>
                <p className="text-sm text-gray-500">{t.title}</p>
              </div>
              <p className="text-gray-700 leading-relaxed">{t.text}</p>
              <div className="mt-6 flex items-center gap-3">
                {[...Array(5)].map((_, i) => <span key={i} className="text-yellow-400">★</span>)}
                <span className="text-gray-600">5.0</span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
