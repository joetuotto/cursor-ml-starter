import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import NewswirePage from './pages/NewswirePage';

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        {/* Redirect root to newswire trends */}
        <Route path="/" element={<Navigate to="/newswire/#trends" replace />} />
        
        {/* Newswire trends page */}
        <Route path="/newswire/*" element={<NewswirePage />} />
        
        {/* Catch-all redirect to newswire */}
        <Route path="*" element={<Navigate to="/newswire/#trends" replace />} />
      </Routes>
    </Router>
  );
};

export default App;
