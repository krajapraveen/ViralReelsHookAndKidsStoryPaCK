import React, { useEffect, useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { authAPI } from '../utils/api';
import { Sparkles, CheckCircle, XCircle, Loader2, Mail, ArrowRight } from 'lucide-react';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');

  useEffect(() => {
    if (token) {
      verifyEmail();
    } else {
      setStatus('error');
      setMessage('Invalid verification link');
    }
  }, [token]);

  useEffect(() => {
    if (status === 'success') {
      const timer = setTimeout(() => {
        navigate('/login');
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [status, navigate]);

  const verifyEmail = async () => {
    try {
      const response = await authAPI.verifyEmail({ token });
      if (response.data.success) {
        setStatus('success');
        setMessage(response.data.message || 'Email verified successfully!');
        setEmail(response.data.email || '');
      } else {
        setStatus('error');
        setMessage(response.data.message || 'Verification failed');
      }
    } catch (error) {
      setStatus('error');
      setMessage(error.response?.data?.detail || 'Verification failed. The link may have expired.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950 to-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 rounded-2xl p-10 shadow-2xl text-center">
          <div className="inline-flex items-center gap-2 mb-8">
            <Sparkles className="w-8 h-8 text-indigo-500" />
            <span className="text-2xl font-bold text-white">CreatorStudio AI</span>
          </div>
          
          {status === 'verifying' && (
            <>
              <div className="w-20 h-20 bg-indigo-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Verifying Your Email</h2>
              <p className="text-slate-400">Please wait while we verify your email address...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-10 h-10 text-green-500" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Email Verified!</h2>
              <p className="text-slate-400 mb-2">{message}</p>
              {email && <p className="text-indigo-400 font-medium mb-6">{email}</p>}
              
              <div className="bg-slate-800/50 rounded-xl p-4 mb-6">
                <p className="text-slate-300 text-sm">
                  You will be redirected to the login page in 5 seconds...
                </p>
              </div>
              
              <Link to="/login">
                <Button className="bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 text-white px-8 py-6 text-lg rounded-xl">
                  Go to Login
                  <ArrowRight className="w-5 h-5 ml-2" />
                </Button>
              </Link>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <XCircle className="w-10 h-10 text-red-500" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-3">Verification Failed</h2>
              <p className="text-slate-400 mb-6">{message}</p>
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/login">
                  <Button variant="outline" className="border-slate-700 text-slate-300 hover:bg-slate-800">
                    <Mail className="w-4 h-4 mr-2" />
                    Back to Login
                  </Button>
                </Link>
                <Link to="/signup">
                  <Button className="bg-indigo-500 hover:bg-indigo-600">
                    Create New Account
                  </Button>
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
