import React from 'react';
import ProductCard from './ProductCard';
// Assumindo que o produto.json está na mesma pasta ou importável corretamente no setup do projeto
import productsData from '../data/products.json'; 

const ProductListContainer: React.FC = () => {
  return (
    <div className="product-list-container">
      <h1>Nossas Rosquinhas Deliciosas</h1>
      <div className="product-grid">
        {productsData.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
};

export default ProductListContainer;