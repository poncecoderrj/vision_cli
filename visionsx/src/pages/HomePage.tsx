// ------------------------------------------------
// Componente de Página Inicial
// ------------------------------------------------

import React from 'react';
import { useStore } from '../store/useStore'; // Importa o Zustand

const HomePage = () => {
  // Acessando o estado global para exibir dados
  const state = useStore();

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-20 bg-gray-50 dark:bg-gray-800 rounded-xl shadow-inner">
        <h1 className="text-6xl font-extrabold text-gray-900 dark:text-white mb-4 tracking-tight">
          Bem-vindo ao <span className="text-indigo-600 dark:text-indigo-400">VisionsX</span>!
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto mb-8">
          Este é o seu novo aplicativo React com Vite, TypeScript e Zustand. Vamos construir algo incrível juntos!
        </p>
        <button 
            onClick={() => alert('Ação de botão na Home!')}
            className="px-8 py-3 text-lg font-medium bg-indigo-600 text-white rounded-full shadow-lg hover:bg-indigo-700 transition duration-200"
        >
          Começar a Programar
        </button>
      </section>

      {/* Seção de Exemplo de Componente */}
      <section className="p-8 bg-white dark:bg-gray-900 rounded-xl shadow-lg">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-6 border-b pb-2 border-gray-200 dark:border-gray-700">
          Exemplo de Componente (Card)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-md hover:shadow-xl transition duration-300">
            <h3 className="text-xl font-semibold text-indigo-600 dark:text-indigo-400 mb-2">Funcionalidade A</h3>
            <p className="text-gray-600 dark:text-gray-400">Gerenciamento de estado global com Zustand.</p>
          </div>
          {/* Card 2 */}
          <div className="p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-md hover:shadow-xl transition duration-300">
            <h3 className="text-xl font-semibold text-indigo-600 dark:text-indigo-400 mb-2">Funcionalidade B</h3>
            <p className="text-gray-600 dark:text-gray-400">Estrutura de rotas com React Router DOM.</p>
          </div>
          {/* Card 3 */}
          <div className="p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-md hover:shadow-xl transition duration-300">
            <h3 className="text-xl font-semibold text-indigo-600 dark:text-indigo-400 mb-2">Funcionalidade C</h3>
            <p className="text-gray-600 dark:text-gray-400">Design responsivo com Tailwind CSS.</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;