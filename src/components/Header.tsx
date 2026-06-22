import React from 'react';
import './Header.css'; // Assumindo que criaremos um arquivo CSS para estilização

const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="logo">VisionCLI</div>
      <nav>
        {/* Aqui podem ir links de navegação */}
        <a href="/">Home</a>
        <a href="/about">Sobre</a>
      </nav>
    </header>
  );
};

export default Header;