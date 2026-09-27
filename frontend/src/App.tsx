import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import FeaturesPage from './pages/FeaturesPage'
import RepositoryLayout from './layouts/RepositoryLayout'
import OverviewPage from './pages/OverviewPage'
import ArchitecturePage from './pages/ArchitecturePage'
import SetupPage from './pages/SetupPage'
import AskPage from './pages/AskPage'
import ContributionPage from './pages/ContributionPage'
import FilesPage from './pages/FilesPage'

import SignInPage from './pages/auth/SignInPage'
import SignUpPage from './pages/auth/SignUpPage'
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage'
import ProfilePage from './pages/auth/ProfilePage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/features" element={<FeaturesPage />} />
        
        {/* Auth Routes */}
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/profile" element={<ProfilePage />} />

        <Route path="/repository/:id" element={<RepositoryLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="architecture" element={<ArchitecturePage />} />
          <Route path="setup" element={<SetupPage />} />
          <Route path="ask" element={<AskPage />} />
          <Route path="contribution" element={<ContributionPage />} />
          <Route path="files" element={<FilesPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
