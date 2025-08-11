import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { Layout } from './ui/Layout';
import TrendsNew from './pages/TrendsNew';
import Article from './pages/Article';

function TrendsRoute() {
  const { cat } = useParams();
  return <TrendsNew category={cat} />;
}

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/en/newswire" replace />} />
          <Route path="/:lang/newswire" element={<TrendsNew />} />
          <Route path="/:lang/category/:cat" element={<TrendsRoute />} />
          <Route path="/:lang/article/:id" element={<Article />} />
          <Route path="*" element={<Navigate to="/en/newswire" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;
