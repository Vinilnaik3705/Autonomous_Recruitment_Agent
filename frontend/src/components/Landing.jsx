import React from 'react'
import Navigation from './landing/Navigation'
import Hero from './landing/Hero'
import Features from './landing/Features'
import ValueProps from './landing/ValueProps'
import Integrations from './landing/Integrations'
import Pricing from './landing/Pricing'
import Resources from './landing/Resources'
import Footer from './landing/Footer'

export default function Landing() {
  return (
    <div className="bg-white overflow-hidden">
      <Navigation />
      <div id="product">
        <Hero />
      </div>
      <div id="features">
        <Features />
      </div>
      <ValueProps />
      <Integrations />
      <Pricing />
      <div id="resources">
        <Resources />
      </div>
      <Footer />
    </div>
  )
}
