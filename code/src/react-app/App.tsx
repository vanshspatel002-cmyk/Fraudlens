import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Navigation } from "@/react-app/components/Navigation";
import { Footer } from "@/react-app/components/Footer";
import Home from "@/react-app/pages/Home";
import PhotoChecker from "@/react-app/pages/PhotoChecker";
import Dashboard from "@/react-app/pages/Dashboard";
import History from "@/react-app/pages/History";
import About from "@/react-app/pages/About";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Navigation />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/checker" element={<PhotoChecker />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
