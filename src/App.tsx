import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HomePage } from '@/pages/HomePage'
import { ExplorePage } from '@/pages/ExplorePage'
import { ToolDetailPage } from '@/pages/ToolDetailPage'
import { StoryDetailPage } from '@/pages/StoryDetailPage'
import { AboutPage } from '@/pages/AboutPage'
import { GuidePage } from '@/pages/GuidePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/tool/:id" element={<ToolDetailPage />} />
        <Route path="/story/:id" element={<StoryDetailPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/guide" element={<GuidePage />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
