import React from 'react';
import ProductListContainer from './components/ProductListContainer';
import Header from './components/Header'; // Assumindo que criaremos um Header em breve

const HomePage: React.FC = () => {
  return (
    <div className="home-page">
      <Header />
      <main>
        <ProductListContainer />
      </main>
    </div>
  );
};

export default HomePage;