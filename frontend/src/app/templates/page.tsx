/** Template marketplace page — browse, search, and install agent templates. */

"use client";

import { useState, useEffect } from "react";
import { Package, Search, Download, Star, Filter, GitBranch } from "lucide-react";
import api from "@/lib/api";

interface Template {
  id: string;
  name: string;
  description: string | null;
  category: string;
  version: string;
  is_verified: boolean;
  download_count: number;
}

const CATEGORIES = ["all", "general", "classification", "extraction", "analysis", "content", "development", "qa", "quality", "research"];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");

  const fetchTemplates = async () => {
    try {
      const params = new URLSearchParams();
      if (category !== "all") params.set("category", category);
      if (search) params.set("search", search);
      const response = await api.get(`/templates?${params.toString()}`);
      setTemplates(response.data);
    } catch {
      console.error("Failed to fetch templates");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTemplates(); }, [category]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchTemplates();
  };

  const handleInstall = async (template: Template) => {
    alert(`Template "${template.name}" installed! It will appear in your workflow editor's node toolbar.`);
    // In production: POST /templates/{id}/install which creates a workflow from template
  };

  const categoryColor: Record<string, string> = {
    general: "bg-gray-100 text-gray-600",
    classification: "bg-blue-100 text-blue-600",
    extraction: "bg-purple-100 text-purple-600",
    analysis: "bg-green-100 text-green-600",
    content: "bg-pink-100 text-pink-600",
    development: "bg-yellow-100 text-yellow-700",
    qa: "bg-indigo-100 text-indigo-600",
    quality: "bg-orange-100 text-orange-600",
    research: "bg-teal-100 text-teal-600",
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/" className="text-sm text-gray-500 hover:text-gray-700">← Dashboard</a>
          <div className="w-8 h-8 bg-emerald-600 rounded-lg flex items-center justify-center">
            <Package size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Template Marketplace</h1>
            <p className="text-xs text-gray-500">Browse and install pre-built agent templates</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Search + Filter */}
        <div className="flex gap-3 mb-6">
          <form onSubmit={handleSearch} className="flex-1 relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search templates..."
              className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </form>
          <div className="flex gap-1 overflow-x-auto pb-1">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  category === cat
                    ? "bg-emerald-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading templates...</div>
        ) : templates.length === 0 ? (
          <div className="bg-white rounded-lg border p-12 text-center">
            <Package size={32} className="text-gray-300 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-700 mb-2">No templates found</h3>
            <p className="text-gray-500 text-sm">
              {search ? `No results for "${search}"` : "No templates in this category yet."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {templates.map((template) => (
              <div key={template.id} className="bg-white rounded-lg border p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                      <Package size={16} className="text-emerald-600" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-800 text-sm">{template.name}</h3>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${categoryColor[template.category] || "bg-gray-100 text-gray-600"}`}>
                          {template.category}
                        </span>
                        {template.is_verified && (
                          <Star size={10} className="text-yellow-500 fill-yellow-500" />
                        )}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400">v{template.version}</span>
                </div>

                <p className="text-xs text-gray-500 mb-4 line-clamp-2">
                  {template.description || "No description"}
                </p>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Download size={10} /> {template.download_count}
                  </span>
                  <button
                    onClick={() => handleInstall(template)}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-medium transition-colors"
                  >
                    Install
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
