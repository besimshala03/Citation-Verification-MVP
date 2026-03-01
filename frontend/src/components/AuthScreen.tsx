import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'

export function AuthScreen() {
  const login = useAppStore((s) => s.login)
  const register = useAppStore((s) => s.register)
  const authLoading = useAppStore((s) => s.authLoading)
  const appError = useAppStore((s) => s.appError)

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const submit = async () => {
    if (!email.trim() || password.length < 8) return
    if (mode === 'login') {
      await login(email.trim(), password)
    } else {
      await register(email.trim(), password)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen flex items-center justify-center p-6"
    >
      <div className="glass-card w-full max-w-md p-6 space-y-4">
        <h1 className="text-2xl font-semibold text-white">Citation Verifier</h1>
        <p className="text-sm text-gray-400">
          {mode === 'login' ? 'Sign in to your account' : 'Create a secure account'}
        </p>

        <div className="flex gap-2">
          <button
            onClick={() => setMode('login')}
            className={`px-3 py-1.5 rounded text-sm ${
              mode === 'login' ? 'bg-amber-500 text-black' : 'bg-white/5 text-gray-300'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => setMode('register')}
            className={`px-3 py-1.5 rounded text-sm ${
              mode === 'register' ? 'bg-amber-500 text-black' : 'bg-white/5 text-gray-300'
            }`}
          >
            Register
          </button>
        </div>

        <div className="space-y-3">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password (min 8 chars)"
            className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white"
          />
        </div>

        {appError && <p className="text-sm text-red-300">{appError}</p>}

        <button
          onClick={submit}
          disabled={authLoading || !email.trim() || password.length < 8}
          className="w-full px-4 py-2 rounded bg-amber-500 text-black font-medium disabled:opacity-50"
        >
          {authLoading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create account'}
        </button>
      </div>
    </motion.div>
  )
}
