import React from 'react';
import './ProductCard.css'; // Vamos criar este arquivo CSS em seguida para estilização

interface Product {
  id: number;
  name: string;
  price: number;
  description: string;
  imageUrl: string;
}

interface ProductCardProps {
  product: Product;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  return (
    <div className="product-card">
      <img src={product.imageUrl} alt={product.name} className="product-image" />
      <div className="product-info">
        <h3>{product.name}</h3>
        <p className="price">R$ {product.price.toFixed(2)}</p>
        <p className="description">{product.description}</p>
      </div>
    </div>
  );
};

export default ProductCard;