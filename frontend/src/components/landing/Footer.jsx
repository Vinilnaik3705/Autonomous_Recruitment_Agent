import React from 'react'
import { Github, Twitter, Linkedin, Instagram, ArrowUpRight } from 'lucide-react'

export default function Footer() {
  const currentYear = new Date().getFullYear()

  const sections = [
    {
      title: 'Product',
      links: [
        { label: 'Platform', href: '#product' },
        { label: 'Features', href: '#features' },
        { label: 'Pricing', href: '#pricing' },
        { label: 'Marketplace', href: '#' }
      ]
    },
    {
      title: 'Resources',
      links: [
        { label: 'Documentation', href: 'https://docs.n8n.io/', external: true },
        { label: 'API Reference', href: 'https://fastapi.tiangolo.com/', external: true },
        { label: 'Community', href: '#' },
        { label: 'Support', href: 'mailto:support@hrautomate.com' }
      ]
    }
  ]

  const socials = [
    { icon: Instagram, href: '#', label: 'Instagram' },
    { icon: Twitter, href: '#', label: 'X (Twitter)' },
    { icon: Linkedin, href: '#', label: 'LinkedIn' },
    { icon: Github, href: '#', label: 'GitHub' }
  ]

  return (
    <footer className="bg-white border-t border-gray-100 pt-24 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-12 mb-16">
          {/* Brand Column */}
          <div className="col-span-2 lg:col-span-2">
            <span className="text-2xl font-black bg-gradient-to-r from-orange-500 to-pink-600 bg-clip-text text-transparent mb-6 block">
              HRAutomate
            </span>
            <p className="text-gray-500 font-medium leading-relaxed max-w-sm mb-8">
              The intelligence layer for modern hiring teams. We automate the repetitive, so you can focus on the human.
            </p>
            <div className="flex items-center gap-4">
              {socials.map((social, idx) => (
                <a
                  key={idx}
                  href={social.href}
                  aria-label={social.label}
                  className="w-10 h-10 rounded-xl bg-gray-50 flex items-center justify-center text-gray-400 hover:bg-orange-500 hover:text-white transition-all duration-300 shadow-sm"
                >
                  <social.icon size={18} />
                </a>
              ))}
            </div>
          </div>

          {/* Nav Columns */}
          {sections.map((section, idx) => (
            <div key={idx}>
              <h5 className="text-sm font-black text-gray-900 uppercase tracking-widest mb-6">
                {section.title}
              </h5>
              <ul className="space-y-4">
                {section.links.map((link, lidx) => (
                  <li key={lidx}>
                    <a
                      href={link.href}
                      target={link.external ? "_blank" : undefined}
                      rel={link.external ? "noopener noreferrer" : undefined}
                      className="text-gray-500 hover:text-orange-600 font-semibold transition-colors flex items-center gap-1 group"
                    >
                      {link.label}
                      {link.external && (
                        <ArrowUpRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                      )}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-gray-50 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-gray-400 text-sm font-medium">
            © {currentYear} HRAutomate. All rights reserved. Built with precision.
          </p>
          <div className="flex items-center gap-8 text-sm font-medium text-gray-400">
            <a href="#" className="hover:text-gray-900 transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-gray-900 transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-gray-900 transition-colors">Cookies</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
