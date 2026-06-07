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
import KnowledgeCategories from './pages/KnowledgeCategories';
import KnowledgeBase from './pages/KnowledgeBase';
import KnowledgeImport from './pages/KnowledgeImport';
import PromptAdmin from './pages/PromptAdmin';
import RiskTerms from './pages/RiskTerms';
import HouseProfiles from './pages/HouseProfiles';
import HouseDetail from './pages/HouseDetail';
import Compass from './pages/Compass';
import XuanKong from './pages/XuanKong';
import FengshuiPhoto from './pages/FengshuiPhoto';
import LandscapePhoto from './pages/LandscapePhoto';
import YinzhaiStudy from './pages/YinzhaiStudy';
import TianxingFengshui from './pages/TianxingFengshui';
import DateSelection from './pages/DateSelection';
import Naming from './pages/Naming';
import Divination from './pages/Divination';
import ReportDetail from './pages/ReportDetail';
import SystemCheck from './pages/SystemCheck';

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
        <Route path="reports/:id"     element={<ReportDetail />} />
        <Route path="history"         element={<History />} />
        <Route path="settings"        element={<Settings />} />
        <Route path="case-review"    element={<CaseReview />} />
        <Route path="categories"      element={<KnowledgeCategories />} />
        <Route path="knowledge"       element={<KnowledgeBase />} />
        <Route path="knowledge-import" element={<KnowledgeImport />} />
        <Route path="prompts"         element={<PromptAdmin />} />
        <Route path="risk-terms"      element={<RiskTerms />} />
        <Route path="houses"          element={<HouseProfiles />} />
        <Route path="houses/:id"      element={<HouseDetail />} />
        <Route path="compass"         element={<Compass />} />
        <Route path="xuankong"        element={<XuanKong />} />
        <Route path="fengshui-photo"  element={<FengshuiPhoto />} />
        <Route path="landscape-photo" element={<LandscapePhoto />} />
        <Route path="yinzhai"         element={<YinzhaiStudy />} />
        <Route path="tianxing"        element={<TianxingFengshui />} />
        <Route path="date-selection"  element={<DateSelection />} />
        <Route path="naming"          element={<Naming />} />
        <Route path="divination"      element={<Divination />} />
        <Route path="system-check"    element={<SystemCheck />} />
        <Route path="*"               element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
