import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import CampaignList from "./pages/CampaignList";
import CampaignForm from "./pages/CampaignForm";
import CampaignDetail from "./pages/CampaignDetail";
import PublicCampaign from "./pages/PublicCampaign";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/admin" replace />} />
        <Route path="/admin" element={<CampaignList />} />
        <Route path="/admin/new" element={<CampaignForm />} />
        <Route path="/admin/:id" element={<CampaignDetail />} />
        <Route path="/admin/:id/edit" element={<CampaignForm />} />
        <Route path="/c/:token" element={<PublicCampaign />} />
        <Route path="*" element={<p>Page not found.</p>} />
      </Routes>
    </BrowserRouter>
  );
}
