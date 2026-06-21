// ------------------------------------------------
// Componente App principal
// ------------------------------------------------

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import { useStore } from '../store/useStore'; // Importa o Zustand

// Páginas (serão criadas em src/pages)
import HomePage from '../pages/HomePage'; 
import SettingsPage from '../pages/SettingsPage'; 

function App() {
  // Inicializa o estado global com Zustand
  const [state, setState] = useStore();

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        {/* Componente de Navegação Global */}
        <nav className="p-4 shadow-md bg-white dark:bg-gray-800 sticky top-0 z-10">
          <div className="container mx-auto flex justify-between items-center max-w-6xl">
            <h1 className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">VisionsX</h1>
            <div className="flex space-x-4">
              {/* Botão de Exemplo */}
              <button 
                onClick={() => setState(s => ({ count: s.count + 1 }))}
                className="px-3 py-1 bg-indigo-500 text-white rounded hover:bg-indigo-600 transition duration-200"
              >
                Incrementar Contagem ({state.count})
              </button>
            </div>
          </div>
        </nav>

        {/* Rotas Principais */}
        <main className="container mx-auto p-8 max-w-6xl">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            {/* Adicionar mais rotas aqui */}
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;