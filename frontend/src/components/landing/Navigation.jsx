import React, { useState } from 'react'
import { Menu, X } from 'lucide-react'

export default function Navigation() {
  const [isOpen, setIsOpen] = useState(false)
  const handleSignIn = () => {
    // navigate to the existing login page (no react-router required)
    window.location.href = '/login'
  }

  const handleRequestDemo = () => {
    alert('Demo request feature - contact support@hrautomation.com')
  }

  return (
    <nav className="fixed w-full bg-white/95 backdrop-blur-md z-50 border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex-shrink-0">
            <span className="text-2xl font-bold bg-gradient-to-r from-orange-500 to-purple-600 bg-clip-text text-transparent">
              HRAutomate
            </span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <a href="#product" className="text-gray-700 hover:text-gray-900 transition">
              Product
            </a>
            <a href="#features" className="text-gray-700 hover:text-gray-900 transition">
              Features
            </a>
            <a href="#pricing" className="text-gray-700 hover:text-gray-900 transition">
              Pricing
            </a>
            <a href="#resources" className="text-gray-700 hover:text-gray-900 transition">
              Resources
            </a>
          </div>

          {/* Right side buttons */}
          <div className="hidden md:flex items-center space-x-4">
            <button
              onClick={handleSignIn}
              className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-8 py-3 rounded-full font-bold hover:shadow-xl transition duration-300 uppercase tracking-widest text-xs"
            >
              Sign In
            </button>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="text-gray-700 hover:text-gray-900"
            >
              {isOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden pb-4 space-y-2">
            <a href="#product" className="block px-4 py-2 text-gray-700 hover:bg-gray-100 rounded">
              Product
            </a>
            <a href="#features" className="block px-4 py-2 text-gray-700 hover:bg-gray-100 rounded">
              Features
            </a>
            <a href="#pricing" className="block px-4 py-2 text-gray-700 hover:bg-gray-100 rounded">
              Pricing
            </a>
            <a href="#resources" className="block px-4 py-2 text-gray-700 hover:bg-gray-100 rounded">
              Resources
            </a>
            <button
              onClick={handleSignIn}
              className="w-full bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-2 rounded-full font-bold uppercase tracking-widest text-xs mt-2"
            >
              Sign In
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}
