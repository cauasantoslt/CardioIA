import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

const STORAGE_TOKEN_KEY = 'cardioia_token';
const STORAGE_USER_KEY = 'cardioia_user';

const MOCK_JWT_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiRHIuIENhdcOMIFNhbnRvcyIsImVtYWlsIjoibWVkaWNvQGNhcmRpb2lhLmNvbSIsInJvbGUiOiJDYXJkaW9sb2dpc3RhIiwicm0iOiI1NjY1OTkifQ.fake_signature_cardioia_hash_2026';

const MOCK_USER_PROFILE = {
  id: 'usr_001',
  name: 'Dr. Cauã Santos',
  email: 'medico@cardioia.com',
  crm: 'CRM/SP 241.982',
  specialty: 'Cardiologia Clínica & Inteligência Artificial',
  rm: '566599',
  avatar: 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=150&auto=format&fit=crop&q=80',
};

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_TOKEN_KEY));
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem(STORAGE_USER_KEY);
    return savedUser ? JSON.parse(savedUser) : (token ? MOCK_USER_PROFILE : null);
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) {
      localStorage.setItem(STORAGE_TOKEN_KEY, token);
      if (user) {
        localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user));
      }
    } else {
      localStorage.removeItem(STORAGE_TOKEN_KEY);
      localStorage.removeItem(STORAGE_USER_KEY);
    }
  }, [token, user]);

  const login = async (email, password) => {
    setLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 500));

    if (email.trim().toLowerCase() === 'medico@cardioia.com' && password === 'cardio123') {
      const generatedToken = MOCK_JWT_TOKEN;
      setToken(generatedToken);
      setUser(MOCK_USER_PROFILE);
      localStorage.setItem(STORAGE_TOKEN_KEY, generatedToken);
      localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(MOCK_USER_PROFILE));
      setLoading(false);
      return { success: true };
    } else {
      setLoading(false);
      throw new Error('Credenciais inválidas. Use medico@cardioia.com e senha cardio123');
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
  };

  const isAuthenticated = Boolean(token);

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser utilizado dentro de um AuthProvider');
  }
  return context;
}
