import { BrowserRouter, Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import FeaturesPage from './pages/FeaturesPage'
import RepositoryLayout from './pages/RepositoryLayout'
import OverviewPage from './pages/OverviewPage'
import ArchitecturePage from './pages/ArchitecturePage'
import SetupPage from './pages/SetupPage'
import AskPage from './pages/AskPage'
import ContributionPage from './pages/ContributionPage'
import FilesPage from './pages/FilesPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/features" element={<FeaturesPage />} />
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
