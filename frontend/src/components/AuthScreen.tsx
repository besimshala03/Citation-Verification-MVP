import { useState } from 'react'
import { motion } from 'framer-motion'
import { useAppStore } from '../stores/useAppStore'

export function AuthScreen() {
  const login = useAppStore((s) => s.login)
  const register = useAppStore((s) => s.register)
  const verifyEmail = useAppStore((s) => s.verifyEmail)
  const resendVerification = useAppStore((s) => s.resendVerification)
  const authLoading = useAppStore((s) => s.authLoading)
  const appError = useAppStore((s) => s.appError)
  const pendingVerificationEmail = useAppStore((s) => s.pendingVerificationEmail)

  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [verificationCode, setVerificationCode] = useState('')

  const submit = async () => {
    if (!email.trim() || password.length < 8) return
    if (mode === 'login') {
      await login(email.trim(), password)
    } else {
      await register(email.trim(), password)
    }
  }

  const submitVerification = async () => {
    if (!pendingVerificationEmail || !verificationCode.trim()) return
    await verifyEmail(pendingVerificationEmail, verificationCode.trim())
  }

  if (pendingVerificationEmail) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen flex items-center justify-center p-6"
      >
        <div className="glass-card w-full max-w-md p-6 space-y-4">
          <h1 className="text-2xl font-semibold text-white">Verify your email</h1>
          <p className="text-sm text-gray-400">
            We sent a verification code to <span className="text-gray-200">{pendingVerificationEmail}</span>.
          </p>

          <input
            type="text"
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
            placeholder="Verification code"
            className="w-full bg-white/5 border border-white/10 rounded px-3 py-2 text-white"
          />

          {appError && <p className="text-sm text-red-300">{appError}</p>}

          <div className="flex gap-2">
            <button
              onClick={submitVerification}
              disabled={authLoading || !verificationCode.trim()}
              className="flex-1 px-4 py-2 rounded bg-amber-500 text-black font-medium disabled:opacity-50"
            >
              {authLoading ? 'Please wait...' : 'Verify Email'}
            </button>
            <button
              onClick={() => resendVerification(pendingVerificationEmail)}
              disabled={authLoading}
              className="px-4 py-2 rounded bg-white/10 text-gray-200 hover:bg-white/20 disabled:opacity-50"
            >
              Resend
            </button>
          </div>
        </div>
      </motion.div>
    )
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
