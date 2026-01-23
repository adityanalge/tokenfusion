import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import App from './App';
import Demo from './Demo';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/tokenfusion" element={<App />} />
        <Route path="/demo" element={<Demo />} />
        <Route path="/" element={<Navigate to="/tokenfusion" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
