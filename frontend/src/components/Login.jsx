import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { Mail, Lock, User, Loader2, AlertCircle, CheckCircle, Eye, EyeOff, ChevronDown, Github } from 'lucide-react'
import { useGoogleLogin } from '@react-oauth/google'
import meetingImg from '../assets/meeting.jpg'

export default function Login() {
  const auth = useAuth()
  const [isLogin, setIsLogin] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [roleOpen, setRoleOpen] = useState(false)
  const roleDropdownRef = useRef(null)

  const roles = [
    { value: 'recruiter', label: 'Recruiter' },
    { value: 'interviewer', label: 'Interviewer' },
    { value: 'candidate', label: 'Candidate' },
    { value: 'super_admin', label: 'Admin' }
  ]

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    username: '',
    role: 'recruiter'
  })

  useEffect(() => {
    // Handle outside click for role dropdown
    function handleClickOutside(event) {
      if (roleDropdownRef.current && !roleDropdownRef.current.contains(event.target)) {
        setRoleOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)

    // Handle GitHub OAuth callback
    const urlParams = new URLSearchParams(window.location.search)
    const code = urlParams.get('code')
    if (code) {
      // Clear code from URL to prevent re-execution
      window.history.replaceState({}, document.title, window.location.pathname)
      handleGithubCallback(code)
    }

    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleGithubCallback = async (code) => {
    setLoading(true)
    setError('')
    try {
      const data = await auth.loginSocial(code, 'github', formData.role)
      setSuccess('GitHub login successful!')
      const role = data?.user?.role || (auth.user && auth.user.role)
      const rolePaths = {
        recruiter: '/recruiter',
        interviewer: '/interviewer',
        candidate: '/candidate',
        super_admin: '/admin'
      }
      const target = rolePaths[role] || '/dashboard'
      window.location.href = target
    } catch (err) {
      setError(err.message || 'GitHub login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    if (isLogin) {
      handleLogin(e)
    } else {
      handleRegister(e)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    setError('')
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await auth.login(formData.email, formData.password)
      setSuccess('Login successful!')
      const role = data?.user?.role || (auth.user && auth.user.role)
      const rolePaths = {
        recruiter: '/recruiter',
        interviewer: '/interviewer',
        candidate: '/candidate',
        super_admin: '/admin'
      }
      const target = rolePaths[role] || '/dashboard'
      window.location.href = target
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await auth.register(formData.username, formData.email, formData.password, formData.role)
      setSuccess('Registration successful!')
      const role = data?.user?.role || formData.role
      const rolePaths = {
        recruiter: '/recruiter',
        interviewer: '/interviewer',
        candidate: '/candidate',
        super_admin: '/admin'
      }
      const target = rolePaths[role] || '/dashboard'
      window.location.href = target
    } catch (err) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setLoading(true)
      setError('')
      try {
        const data = await auth.loginSocial(tokenResponse.access_token, 'google', formData.role)
        setSuccess('Google login successful!')
        const role = data?.user?.role || (auth.user && auth.user.role)
        const rolePaths = {
          recruiter: '/recruiter',
          interviewer: '/interviewer',
          candidate: '/candidate',
          super_admin: '/admin'
        }
        const target = rolePaths[role] || '/dashboard'
        window.location.href = target
      } catch (err) {
        setError(err.message || 'Google login failed')
      } finally {
        setLoading(false)
      }
    },
    onError: error => {
      setError('Google Login Failed')
      console.error(error)
    }
  })

  const handleSocialLogin = async (provider) => {
    if (provider === 'google') {
      googleLogin()
    } else if (provider === 'github') {
      const clientId = "Ov23liLdm7eOHKd3nbmo"
      const redirectUri = window.location.origin + '/login'
      const ghAuthUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=user:email`
      window.location.href = ghAuthUrl
    } else {
      setError(`${provider} login is currently under development.`);
    }
  };

  const handlePlaceholderClick = (feature) => {
    alert(`${feature} is a visual preview for this demo. Authenticate to access the full recruitment engine.`);
  };


  return (
    <div className="min-h-screen bg-mesh flex items-center justify-center p-4 sm:p-6 lg:p-8">
      {/* Main Glass Container */}
      <div className="w-full max-w-6xl glass-container rounded-[2.5rem] overflow-hidden flex flex-col md:flex-row shadow-2xl animate-fade-up">

        {/* Left Side - Form */}
        <div className="w-full md:w-[45%] p-8 sm:p-12 lg:p-16 flex flex-col justify-between">
          <div>
            {/* Logo */}
            <div className="mb-12">
              <div className="inline-flex items-center px-4 py-2 bg-white/50 backdrop-blur-sm rounded-full border border-white/50 shadow-sm">
                <span className="text-sm font-bold tracking-tight text-gray-800">HRAutomate</span>
              </div>
            </div>

            {/* Header */}
            <div className="mb-10">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {isLogin ? 'Welcome back' : 'Create an account'}
              </h1>
              <p className="text-gray-500 text-sm">
                {isLogin ? 'Sign in to your account to continue' : 'Sign up and get 30 day free trial'}
              </p>
            </div>

            {/* Status Messages */}
            {error && (
              <div className="mb-6 p-4 bg-red-50/50 backdrop-blur-sm border border-red-100 rounded-2xl flex items-start gap-3 animate-fade-up">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-red-700 text-xs font-medium">{error}</p>
              </div>
            )}
            {success && (
              <div className="mb-6 p-4 bg-green-50/50 backdrop-blur-sm border border-green-100 rounded-2xl flex items-start gap-3 animate-fade-up">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <p className="text-green-700 text-xs font-medium">{success}</p>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {!isLogin && (
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 ml-1">Full name</label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    placeholder="Amélie Laurent"
                    className="w-full px-5 py-3.5 bg-white/60 border border-transparent rounded-2xl text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-100 transition-all shadow-sm"
                    required
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 ml-1">Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="amélielaurent7622@gmail.com"
                  className="w-full px-5 py-3.5 bg-white/60 border border-transparent rounded-2xl text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-100 transition-all shadow-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 ml-1">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••••••••••"
                    className="w-full px-5 py-3.5 bg-white/60 border border-transparent rounded-2xl text-gray-900 placeholder-gray-400 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-100 transition-all shadow-sm pr-12"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {!isLogin && (
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 ml-1">Role</label>
                  <div className="relative" ref={roleDropdownRef}>
                    <button
                      type="button"
                      onClick={() => setRoleOpen(!roleOpen)}
                      className="w-full px-5 py-3.5 bg-white/60 border border-transparent rounded-2xl text-gray-900 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-100 transition-all shadow-sm flex items-center justify-between"
                    >
                      <span className="font-medium text-sm">{roles.find(r => r.value === formData.role)?.label}</span>
                      <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${roleOpen ? 'rotate-180' : ''}`} />
                    </button>
                    {roleOpen && (
                      <div className="absolute top-full left-0 right-0 mt-2 bg-white/90 backdrop-blur-md border border-white/50 rounded-2xl shadow-xl z-50 overflow-hidden animate-fade-up">
                        {roles.map((role) => (
                          <button
                            key={role.value}
                            type="button"
                            onClick={() => {
                              setFormData(prev => ({ ...prev, role: role.value }))
                              setRoleOpen(false)
                            }}
                            className={`w-full px-5 py-3 text-left transition-all text-sm font-medium ${formData.role === role.value ? 'bg-blue-500 text-white' : 'hover:bg-blue-50 text-gray-900'
                              }`}
                          >
                            {role.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-4 bg-yellow-400 hover:bg-yellow-500 active:scale-[0.98] disabled:bg-gray-200 disabled:text-gray-400 text-gray-900 font-bold rounded-2xl transition-all shadow-lg shadow-yellow-200/50 flex items-center justify-center gap-2 mt-4"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (isLogin ? 'Sign in' : 'Submit')}
              </button>
            </form>

            {/* Social Logins */}
            <div className="mt-6 grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => handleSocialLogin('github')}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-white/50 border border-gray-100 rounded-2xl hover:bg-white transition-all shadow-sm text-sm font-medium"
              >
                <Github className="w-5 h-5" />
                GitHub
              </button>
              <button
                type="button"
                onClick={() => handleSocialLogin('google')}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-white/50 border border-gray-100 rounded-2xl hover:bg-white transition-all shadow-sm text-sm font-medium"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" /><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" /><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" /><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 12-5.38z" /></svg>
                Google
              </button>
            </div>
          </div>

          {/* Footer Toggle */}
          <div className="mt-12 flex items-center justify-between text-xs font-medium border-t border-gray-100 pt-6">
            <div className="text-gray-400">
              {isLogin ? "Don't have an account? " : "Have an account? "}
              <button
                onClick={() => setIsLogin(!isLogin)}
                className="text-blue-600 font-semibold hover:text-blue-700 hover:underline transition-colors"
              >
                {isLogin ? 'Sign up' : 'Sign in'}
              </button>
            </div>
            <button onClick={() => handlePlaceholderClick('Terms & Conditions')} className="text-gray-400 hover:text-gray-600 transition-colors">Terms & Conditions</button>
          </div>
        </div>

        {/* Right Side - Visual */}
        <div className="hidden md:block w-[55%] relative overflow-hidden bg-gray-200">
          <img
            src={meetingImg}
            alt="Collaborative Recruitment Team Meeting"
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-l from-transparent via-transparent to-white/10" />

          {/* Floating UI Elements */}
          <div className="absolute inset-0 p-8 flex flex-col items-end justify-start gap-6">

            {/* Task Review Card */}
            <button
              onClick={() => handlePlaceholderClick('Task Management')}
              className="glass-card p-4 rounded-2xl w-64 animate-float flex flex-col gap-2 hover:scale-105 transition-all text-left"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-orange-600 bg-orange-50 px-2 py-0.5 rounded-full">Task Review With Team</span>
                <div className="w-2 h-2 bg-orange-400 rounded-full" />
              </div>
              <span className="text-[10px] text-gray-500">09:30am-10:00am</span>
            </button>

            {/* Daily Meeting Card */}
            <button
              onClick={() => handlePlaceholderClick('Meeting Scheduler')}
              className="glass-card p-4 rounded-2xl w-64 animate-float [animation-delay:1.5s] absolute bottom-20 left-10 hover:scale-105 transition-all text-left"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-gray-800">Daily Meeting</span>
                <div className="w-2 h-2 bg-yellow-400 rounded-full" />
              </div>
              <span className="text-[10px] text-gray-500 block mb-4">12:00pm-01:00pm</span>
              <div className="flex -space-x-2">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="w-6 h-6 rounded-full border-2 border-white bg-mesh flex items-center justify-center text-[8px] font-bold">
                    {String.fromCharCode(64 + i)}
                  </div>
                ))}
              </div>
            </button>

            {/* Calendar Widget */}
            <button
              onClick={() => handlePlaceholderClick('Recruitment Calendar')}
              className="glass-card p-4 rounded-2xl w-64 animate-float [animation-delay:0.8s] absolute top-1/2 -right-10 -translate-y-1/2 hover:scale-105 transition-all text-left"
            >
              <div className="flex items-center justify-between gap-2 text-center text-[10px] font-bold text-gray-400">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                  <div key={day} className="flex flex-col gap-1">
                    <span>{day}</span>
                    <span className={day === 'Wed' ? 'text-gray-800' : ''}>
                      {day === 'Sun' ? '22' : day === 'Mon' ? '23' : day === 'Tue' ? '24' : day === 'Wed' ? '25' : day === 'Thu' ? '26' : day === 'Fri' ? '27' : '28'}
                    </span>
                  </div>
                ))}
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
