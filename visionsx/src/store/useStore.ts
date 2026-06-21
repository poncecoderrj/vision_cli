// ------------------------------------------------
// Store Zustand Global State Management
// ------------------------------------------------

import { create } from 'zustand';

export const useStore = create((set) => ({
  count: 0, // Estado inicial de contagem
  user: null, // Exemplo de estado de usuário
  
  // Ações (Setters)
  incrementCount: () => set((state) => ({ count: state.count + 1 })),
  resetState: () => set({ count: 0, user: null }),
}));