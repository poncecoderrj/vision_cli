// ------------------------------------------------
// Componente de Layout/Estrutura Principal
// ------------------------------------------------

import React from 'react';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* O componente App.tsx já contém a navegação, mas podemos usar um layout wrapper */}
      <main>{children}</main>
    </div>
  );
};

export default Layout;