// ------------------------------------------------
// Componente de Página de Configurações
// ------------------------------------------------

import React from 'react';
import { useStore } from '../store/useStore'; // Importa o Zustand

const SettingsPage = () => {
  // Acessando o estado global para exibir dados
  const state = useStore();

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <h1 className="text-4xl font-bold text-gray-900 dark:text-white border-b pb-2 border-indigo-500/50">
        ⚙️ Configurações do Projeto
      </h1>

      {/* Card de Exemplo */}
      <div className="p-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg space-y-6">
        <h2 className="text-2xl font-semibold text-indigo-600 dark:text-indigo-400">Estado Global (Zustand)</h2>
        <p className="text-gray-600 dark:text-gray-300">
          Aqui você pode visualizar e interagir com o estado global do seu aplicativo.
        </p>

        {/* Exibição de Estado */}
        <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg border border-gray-200 dark:border-gray-600">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-300 mb-1">Contagem Atual:</p>
          <div className="text-4xl font-bold text-indigo-600 dark:text-indigo-400">{state.count}</div>
        </div>

        {/* Botão de Ação */}
        <button 
            onClick={() => alert('Ação de reset do estado!')}
            className="w-full py-2 px-4 bg-red-500 text-white rounded hover:bg-red-600 transition duration-200"
        >
          Resetar Contagem (Exemplo)
        </button>
      </div>

    </div>
  );
};

export default SettingsPage;