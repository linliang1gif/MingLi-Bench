import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import ChatHome from './pages/ChatHome';
import Subjects from './pages/Subjects';
import SubjectCreate from './pages/SubjectCreate';
import ChartAnalysis from './pages/ChartAnalysis';
import Reports from './pages/Reports';
import History from './pages/History';
import Settings from './pages/Settings';
import CaseReview from './pages/CaseReview';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<ChatHome />} />
        <Route path="subjects"        element={<Subjects />} />
        <Route path="subjects/new"    element={<SubjectCreate />} />
        <Route path="chart"           element={<ChartAnalysis />} />
        <Route path="chart/:subjectId" element={<ChartAnalysis />} />
        <Route path="reports"         element={<Reports />} />
        <Route path="reports/:id"     element={<Reports />} />
        <Route path="history"         element={<History />} />
        <Route path="settings"        element={<Settings />} />
        <Route path="case-review"    element={<CaseReview />} />
        <Route path="*"               element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
