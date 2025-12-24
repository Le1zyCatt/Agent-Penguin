import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

type ToastVariant = 'info' | 'success' | 'error';

interface ToastState {
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  show: (message: string, variant?: ToastVariant) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export const ToastProvider = ({ children }: { children: ReactNode }) => {
  const [toast, setToast] = useState<ToastState | null>(null);

  const show = useCallback((message: string, variant: ToastVariant = 'info') => {
    setToast({ message, variant });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(timer);
  }, [toast]);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      {toast && (
        <div
          className="toast"
          style={{
            background: toast.variant === 'error' ? '#dc2626' : toast.variant === 'success' ? '#16a34a' : '#1f6ec4',
          }}
        >
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return ctx;
};
