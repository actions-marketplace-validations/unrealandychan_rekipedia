"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  BookOpen,
  MessageSquare,
  Network,
  StickyNote,
  Search,
  ChevronRight,
  ChevronDown,
  Send,
  Loader2,
  Plus,
  Trash2,
  Tag,
  Hash,
  ExternalLink,
  RefreshCw,
  Folder,
  FileCode,
  Sparkles,
  Check
} from "lucide-react";
import { marked } from "marked";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// Setup marked to target blank links and enable clean linebreaks
marked.setOptions({
  breaks: true,
  gfm: true
});

interface WikiPage {
  slug: string;
  title: string;
  section: string;
}

interface ActiveWikiPage extends WikiPage {
  raw: string;
  html: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  model?: string;
  timestamp?: string;
}

interface Note {
  id: string;
  content: string;
  tags: string;
  source: string;
  created_at: string;
}

interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    kind: string;
    file: string;
    group: string;
    god: boolean;
  }>;
  edges: Array<{
    source: string;
    target: string;
    kind: string;
  }>;
  god_nodes: Array<{
    name: string;
    degree: number;
  }>;
}

export default function Dashboard() {
  // Navigation states
  const [activeTab, setActiveTab] = useState<"wiki" | "chat" | "graph" | "notes">("wiki");
  const [activeSlug, setActiveSlug] = useState<string>("");
  const [wikiPages, setWikiPages] = useState<WikiPage[]>([]);
  const [activeWiki, setActiveWiki] = useState<ActiveWikiPage | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [projectName, setProjectName] = useState("Codebase Intelligence");
  const [fileCount, setFileCount] = useState(0);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});

  // Loading states
  const [loadingWikiList, setLoadingWikiList] = useState(true);
  const [loadingWikiPage, setLoadingWikiPage] = useState(false);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [loadingNotes, setLoadingNotes] = useState(false);

  // Chat states
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatStreaming, setIsChatStreaming] = useState(false);
  const [activeModel, setActiveModel] = useState("ollama/llama4");
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Notes states
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteInput, setNoteInput] = useState("");
  const [noteTags, setNoteTags] = useState("");

  // Graph states
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);
  const [selectedGraphNode, setSelectedGraphNode] = useState<any>(null);
  const [rawGraphData, setRawGraphData] = useState<GraphData | null>(null);

  // Fetch initial project metadata & wiki pages
  useEffect(() => {
    async function loadMetadata() {
      try {
        const res = await fetch("/api/wiki");
        if (res.ok) {
          const pages: WikiPage[] = await res.json();
          setWikiPages(pages);
          
          // Group sections and set them to expanded by default
          const sections: Record<string, boolean> = {};
          pages.forEach(p => {
            sections[p.section] = true;
          });
          setExpandedSections(sections);

          // Find first available page or specific index/getting-started page
          if (pages.length > 0) {
            const indexPage = pages.find(p => p.slug === "getting-started" || p.slug === "index" || p.slug === "architecture-overview") || pages[0];
            setActiveSlug(indexPage.slug);
          }
        }
      } catch (err) {
        console.error("Failed to load wiki list:", err);
      } finally {
        setLoadingWikiList(false);
      }

      // Try to load file count and project name from health/history api
      try {
        const healthRes = await fetch("/api/health");
        if (healthRes.ok) {
          const health = await healthRes.json();
          // Fetch history to populate project title if possible, or use standard
        }
      } catch {}
    }

    loadMetadata();
  }, []);

  // Fetch active wiki page content
  useEffect(() => {
    if (!activeSlug) return;
    async function loadWikiPage() {
      setLoadingWikiPage(true);
      try {
        const res = await fetch(`/api/wiki/page/${activeSlug}`);
        if (res.ok) {
          const data: ActiveWikiPage = await res.json();
          setActiveWiki(data);
          setActiveTab("wiki");
        }
      } catch (err) {
        console.error("Failed to load wiki page:", err);
      } finally {
        setLoadingWikiPage(false);
      }
    }
    loadWikiPage();
  }, [activeSlug]);

  // Fetch Q&A Chat History
  const loadChatHistory = async () => {
    try {
      const res = await fetch("/api/history");
      if (res.ok) {
        const data = await res.json();
        // Convert API schema to UI ChatMessage schema
        const mapped: ChatMessage[] = data.map((h: any, i: number) => [
          { id: `q-${i}`, role: "user", content: h.question, timestamp: h.created_at },
          { id: `a-${i}`, role: "assistant", content: h.answer, model: h.model, timestamp: h.created_at }
        ]).flat();
        setChatHistory(mapped);
      }
    } catch (err) {
      console.error("Failed to load chat history:", err);
    }
  };

  useEffect(() => {
    if (activeTab === "chat") {
      loadChatHistory();
    }
  }, [activeTab]);

  // Scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Fetch Dependency Graph Data
  const loadGraphData = async () => {
    setLoadingGraph(true);
    try {
      const res = await fetch("/api/graph");
      if (res.ok) {
        const data: GraphData = await res.json();
        setRawGraphData(data);

        // Layout nodes in a grid or circle for visualization
        // In a real app we might use d3-force, let's do a smart grid layout based on groups
        const groups = Array.from(new Set(data.nodes.map(n => n.group)));
        const groupCols = Math.ceil(Math.sqrt(groups.length));
        const groupSpacingX = 450;
        const groupSpacingY = 450;

        const groupLayoutPositions: Record<string, { x: number; y: number }> = {};
        groups.forEach((g, idx) => {
          const col = idx % groupCols;
          const row = Math.floor(idx / groupCols);
          groupLayoutPositions[g] = {
            x: col * groupSpacingX,
            y: row * groupSpacingY
          };
        });

        const groupCounts: Record<string, number> = {};
        const flowNodes = data.nodes.map(node => {
          const g = node.group;
          groupCounts[g] = (groupCounts[g] || 0) + 1;
          const idxInGroup = groupCounts[g] - 1;

          // Place inside group bounding area
          const colInGroup = idxInGroup % 3;
          const rowInGroup = Math.floor(idxInGroup / 3);

          const groupBase = groupLayoutPositions[g] || { x: 0, y: 0 };
          const x = groupBase.x + colInGroup * 130;
          const y = groupBase.y + rowInGroup * 110;

          // Colors based on kind & god-class status
          let borderCol = "border-gray-700";
          let bgCol = "bg-gray-800/80 hover:bg-gray-800";
          let textCol = "text-gray-200";

          if (node.god) {
            borderCol = "border-red-500 shadow-[0_0_10px_rgba(239,68,68,0.3)]";
            bgCol = "bg-red-950/40 hover:bg-red-950/60";
          } else if (node.kind === "class") {
            borderCol = "border-blue-500";
            bgCol = "bg-blue-950/20 hover:bg-blue-950/40";
          } else if (node.kind === "function") {
            borderCol = "border-green-500";
            bgCol = "bg-green-950/20 hover:bg-green-950/40";
          }

          return {
            id: node.id,
            position: { x, y },
            data: { 
              label: (
                <div className="flex flex-col text-left text-xs p-1">
                  <div className="flex items-center gap-1.5 font-bold truncate">
                    {node.god ? <Sparkles className="w-3 h-3 text-red-400" /> : <FileCode className="w-3 h-3 text-blue-400" />}
                    <span className="truncate">{node.label}</span>
                  </div>
                  <div className="text-[9px] text-gray-400 mt-1 truncate">{node.file}</div>
                  <div className="flex items-center gap-2 mt-1 text-[8px]">
                    <span className="px-1 py-0.2 bg-gray-900 border border-gray-700 text-gray-300 rounded uppercase">
                      {node.kind}
                    </span>
                    <span className="text-gray-500 truncate">{node.group}</span>
                  </div>
                </div>
              ),
              raw: node
            },
            className: `border-2 rounded-lg p-2 ${bgCol} ${borderCol} ${textCol} shadow-lg transition-all cursor-pointer w-[200px]`,
            style: { borderStyle: "solid" }
          };
        });

        // Edges
        const flowEdges = data.edges.map((edge, idx) => ({
          id: `e-${idx}`,
          source: edge.source,
          target: edge.target,
          animated: edge.kind === "inherits" || edge.kind === "calls",
          label: edge.kind !== "imports" ? edge.kind : "",
          labelStyle: { fill: "#9CA3AF", fontSize: 8, fontWeight: 500 },
          style: {
            stroke: edge.kind === "inherits" ? "#3B82F6" : edge.kind === "calls" ? "#10B981" : "#4B5563",
            strokeWidth: 1.5
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 10,
            height: 10,
            color: edge.kind === "inherits" ? "#3B82F6" : edge.kind === "calls" ? "#10B981" : "#4B5563"
          }
        }));

        setNodes(flowNodes);
        setEdges(flowEdges);
      }
    } catch (err) {
      console.error("Failed to load graph:", err);
    } finally {
      setLoadingGraph(false);
    }
  };

  useEffect(() => {
    if (activeTab === "graph") {
      loadGraphData();
    }
  }, [activeTab]);

  // Fetch Notes List
  const loadNotesList = async () => {
    setLoadingNotes(true);
    try {
      const res = await fetch("/api/notes");
      if (res.ok) {
        const data = await res.json();
        setNotes(data);
      }
    } catch (err) {
      console.error("Failed to load notes:", err);
    } finally {
      setLoadingNotes(false);
    }
  };

  useEffect(() => {
    if (activeTab === "notes") {
      loadNotesList();
    }
  }, [activeTab]);

  // Submit Note
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteInput.trim()) return;
    try {
      const res = await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: noteInput,
          tags: noteTags.split(",").map(t => t.trim()).filter(Boolean)
        })
      });
      if (res.ok) {
        setNoteInput("");
        setNoteTags("");
        loadNotesList();
      }
    } catch (err) {
      console.error("Failed to create note:", err);
    }
  };

  // Delete Note
  const handleDeleteNote = async (id: string) => {
    try {
      const res = await fetch(`/api/notes/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        loadNotesList();
      }
    } catch (err) {
      console.error("Failed to delete note:", err);
    }
  };

  // Submit Chat Question
  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatStreaming) return;

    const userQuestion = chatInput.trim();
    setChatInput("");

    // Add user message to local state
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `assistant-${Date.now()}`;
    
    setChatHistory(prev => [
      ...prev,
      { id: userMsgId, role: "user", content: userQuestion, timestamp: new Date().toLocaleTimeString() },
      { id: assistantMsgId, role: "assistant", content: "", timestamp: new Date().toLocaleTimeString() }
    ]);

    setIsChatStreaming(true);

    try {
      // Encode question for URL query parameter
      const url = `/ask/stream?question=${encodeURIComponent(userQuestion)}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error("API streaming error");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      let partialText = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6).trim();
              if (data === "[DONE]") {
                setIsChatStreaming(false);
              } else if (data.startsWith("[ERROR]")) {
                const errMsg = data.slice(7).trim();
                setChatHistory(prev =>
                  prev.map(msg =>
                    msg.id === assistantMsgId
                      ? { ...msg, content: msg.content + `\n\n❌ Error: ${errMsg}` }
                      : msg
                  )
                );
                setIsChatStreaming(false);
              } else {
                // Decode safe escaped newlines back to actual newlines
                const cleanChunk = data.replace(/\\n/g, "\n");
                setChatHistory(prev =>
                  prev.map(msg =>
                    msg.id === assistantMsgId
                      ? { ...msg, content: msg.content + cleanChunk }
                      : msg
                  )
                );
              }
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Chat connection failed:", err);
      setChatHistory(prev =>
        prev.map(msg =>
          msg.id === assistantMsgId
            ? { ...msg, content: msg.content + `\n\n❌ Connection failed: ${err.message}` }
            : msg
        )
      );
      setIsChatStreaming(false);
    } finally {
      setIsChatStreaming(false);
      // Reload history to ensure db saves match local
      loadChatHistory();
    }
  };

  // Group wiki pages by section
  const sections: Record<string, WikiPage[]> = {};
  wikiPages.forEach(p => {
    if (!sections[p.section]) {
      sections[p.section] = [];
    }
    sections[p.section].push(p);
  });

  // Filter wiki pages based on search
  const filteredSections = Object.entries(sections).reduce<Record<string, WikiPage[]>>((acc, [sect, pages]) => {
    const matched = pages.filter(p => p.title.toLowerCase().includes(searchQuery.toLowerCase()) || p.slug.toLowerCase().includes(searchQuery.toLowerCase()));
    if (matched.length > 0) {
      acc[sect] = matched;
    }
    return acc;
  }, {});

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleNodeClick = (_event: any, flowNode: any) => {
    setSelectedGraphNode(flowNode.data.raw);
  };

  return (
    <div className="flex h-screen bg-[#070A13] text-gray-100 overflow-hidden">
      {/* SIDEBAR */}
      <div className={`flex flex-col bg-[#0F1322] border-r border-[#1E2540] h-full transition-all duration-300 ${isSidebarOpen ? "w-[280px]" : "w-0 -translate-x-[280px] md:w-[60px] md:translate-x-0"}`}>
        {/* Sidebar Header */}
        <div className="flex items-center gap-3 p-4 border-b border-[#1E2540] min-h-[65px] truncate">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-md flex-shrink-0">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          {isSidebarOpen && (
            <div className="flex flex-col truncate">
              <span className="font-bold text-sm tracking-wide bg-gradient-to-r from-blue-400 to-indigo-300 bg-clip-text text-transparent">
                REKIPEDIA
              </span>
              <span className="text-[10px] text-gray-400 truncate">Codebase Wiki</span>
            </div>
          )}
        </div>

        {/* Global Action Navigation Links */}
        <div className="p-3 border-b border-[#1E2540] flex flex-col gap-1">
          <button
            onClick={() => setActiveTab("chat")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "chat"
                ? "bg-gradient-to-r from-blue-600/30 to-indigo-600/30 text-blue-400 border border-blue-500/20"
                : "text-gray-400 hover:bg-[#151B30] hover:text-gray-100"
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            {isSidebarOpen && <span>Codebase Chat</span>}
          </button>
          <button
            onClick={() => setActiveTab("graph")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "graph"
                ? "bg-gradient-to-r from-blue-600/30 to-indigo-600/30 text-blue-400 border border-blue-500/20"
                : "text-gray-400 hover:bg-[#151B30] hover:text-gray-100"
            }`}
          >
            <Network className="w-4 h-4" />
            {isSidebarOpen && <span>Dependency Graph</span>}
          </button>
          <button
            onClick={() => setActiveTab("notes")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "notes"
                ? "bg-gradient-to-r from-blue-600/30 to-indigo-600/30 text-blue-400 border border-blue-500/20"
                : "text-gray-400 hover:bg-[#151B30] hover:text-gray-100"
            }`}
          >
            <StickyNote className="w-4 h-4" />
            {isSidebarOpen && <span>Notes & Insights</span>}
          </button>
        </div>

        {/* Search Bar */}
        {isSidebarOpen && (
          <div className="p-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search wiki chapters..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-[#161C33] border border-[#232B4E] rounded-lg pl-9 pr-3 py-2 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
        )}

        {/* Wiki List Directory Section */}
        <div className="flex-1 overflow-y-auto px-3 py-2 flex flex-col gap-2">
          {isSidebarOpen && (
            <>
              <div className="text-[10px] font-bold tracking-wider text-gray-500 uppercase px-2 mb-1">
                Wiki Directory
              </div>

              {loadingWikiList ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
                </div>
              ) : Object.keys(filteredSections).length === 0 ? (
                <div className="text-xs text-gray-500 text-center p-4 italic">No pages matched.</div>
              ) : (
                Object.entries(filteredSections).map(([sectionName, pages]) => (
                  <div key={sectionName} className="flex flex-col">
                    {/* Collapsible Header */}
                    <button
                      onClick={() => toggleSection(sectionName)}
                      className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-[#151B30] transition-colors text-left"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <Folder className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                        <span className="text-xs font-semibold text-gray-300 truncate uppercase tracking-wide">
                          {sectionName}
                        </span>
                      </div>
                      {expandedSections[sectionName] ? (
                        <ChevronDown className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                      )}
                    </button>

                    {/* Collapsible Content Pages */}
                    {expandedSections[sectionName] && (
                      <div className="flex flex-col gap-0.5 mt-1 border-l border-indigo-950/40 ml-3.5 pl-1.5">
                        {pages.map(page => (
                          <button
                            key={page.slug}
                            onClick={() => {
                              setActiveSlug(page.slug);
                              setActiveTab("wiki");
                            }}
                            className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left text-xs font-medium transition-all ${
                              activeSlug === page.slug && activeTab === "wiki"
                                ? "bg-blue-600/10 text-blue-400 border-l-2 border-blue-500"
                                : "text-gray-400 hover:bg-[#151B30]/60 hover:text-gray-200"
                            }`}
                          >
                            <span className="truncate">{page.title}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </>
          )}
        </div>
      </div>

      {/* MAIN MAIN PANEL CONTENT WINDOW */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Main Content Header */}
        <header className="flex items-center justify-between px-6 border-b border-[#1E2540] min-h-[65px] bg-[#0A0D18]">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-1.5 hover:bg-[#1E2540] rounded-md transition-colors text-gray-400 hover:text-gray-100"
            >
              <ChevronRight className={`w-5 h-5 transition-transform ${isSidebarOpen ? "rotate-180" : ""}`} />
            </button>
            <h1 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
              <span>{projectName}</span>
              <span className="px-2 py-0.5 text-[9px] bg-[#1E2540] text-gray-400 rounded-full font-normal">
                Serve Mode
              </span>
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                if (activeTab === "wiki") {
                  // Reload active wiki page
                  const s = activeSlug;
                  setActiveSlug("");
                  setTimeout(() => setActiveSlug(s), 50);
                } else if (activeTab === "chat") {
                  loadChatHistory();
                } else if (activeTab === "graph") {
                  loadGraphData();
                } else if (activeTab === "notes") {
                  loadNotesList();
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-[#13192F] border border-[#232B4E] rounded-lg hover:bg-[#1E2540] transition-colors text-gray-300"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Sync</span>
            </button>
          </div>
        </header>

        {/* Dynamic Display Windows */}
        <div className="flex-1 overflow-hidden">
          {/* TAB 1: WIKI DOCUMENTATION VIEWER */}
          {activeTab === "wiki" && (
            <div className="h-full overflow-y-auto px-8 py-10 bg-[#070A13]">
              {loadingWikiPage ? (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                  <span className="text-xs text-gray-500">Loading wiki page...</span>
                </div>
              ) : activeWiki ? (
                <div className="max-w-4xl mx-auto flex gap-10">
                  {/* Markdown Body */}
                  <div className="flex-1">
                    <div className="text-xs font-bold text-blue-400 tracking-wider uppercase mb-1">
                      {activeWiki.section}
                    </div>
                    <div
                      className="prose prose-invert"
                      dangerouslySetInnerHTML={{ __html: activeWiki.html }}
                    />
                  </div>

                  {/* On This Page Panel (Right panel) */}
                  <div className="hidden lg:block w-[220px] flex-shrink-0">
                    <div className="sticky top-0 bg-[#0B0F19] border border-[#1E2540]/60 rounded-xl p-4">
                      <div className="text-xs font-bold text-gray-400 tracking-wider uppercase mb-3">
                        Metadata & Tools
                      </div>
                      <div className="flex flex-col gap-3.5 text-xs text-gray-400">
                        <div>
                          <div className="text-gray-500 font-medium">Chapter Slug</div>
                          <div className="font-mono mt-1 text-gray-300 select-all truncate">
                            {activeWiki.slug}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-500 font-medium">File Source</div>
                          <div className="font-mono mt-1 text-gray-300 select-all truncate flex items-center gap-1">
                            <Hash className="w-3 h-3 text-indigo-400" />
                            <span>{activeWiki.slug}.md</span>
                          </div>
                        </div>
                        <div className="border-t border-[#1E2540] pt-3">
                          <button
                            onClick={() => {
                              setChatInput(`Explain how the concepts inside '${activeWiki.title}' are structured and implemented.`);
                              setActiveTab("chat");
                            }}
                            className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg font-medium shadow-md transition-all"
                          >
                            <MessageSquare className="w-3.5 h-3.5" />
                            <span>Ask AI about this</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500 italic">
                  Select a wiki page from the sidebar to view documentation.
                </div>
              )}
            </div>
          )}

          {/* TAB 2: CODEBASE CHAT PANEL */}
          {activeTab === "chat" && (
            <div className="h-full flex bg-[#070A13]">
              {/* Main Chat Panel */}
              <div className="flex-1 flex flex-col h-full bg-[#080B15]">
                {/* Chat Message Window */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  {chatHistory.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center max-w-md mx-auto">
                      <div className="w-12 h-12 bg-blue-600/10 text-blue-400 rounded-full flex items-center justify-center mb-4 border border-blue-500/20">
                        <MessageSquare className="w-6 h-6" />
                      </div>
                      <h3 className="text-lg font-bold text-gray-200">Ask your Codebase anything</h3>
                      <p className="text-xs text-gray-400 mt-2">
                        Questions are answered by our AI model grounded directly in your scanned source code architecture, relationships, and wiki.
                      </p>
                      <div className="grid grid-cols-1 gap-2 w-full mt-6">
                        {[
                          "Explain the overall project architecture.",
                          "Where is the main entry point located?",
                          "What are the most critical hotspots or modules?"
                        ].map((q, idx) => (
                          <button
                            key={idx}
                            onClick={() => setChatInput(q)}
                            className="px-4 py-2.5 text-xs bg-[#12172D] border border-[#232B4E] rounded-lg hover:bg-[#1E2540] text-left text-gray-300 font-medium transition-colors"
                          >
                            {q}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    chatHistory.map((msg, idx) => (
                      <div
                        key={msg.id}
                        className={`flex gap-4 max-w-4xl mx-auto ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                      >
                        {msg.role === "assistant" && (
                          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                            <Sparkles className="w-4.5 h-4.5 text-indigo-400" />
                          </div>
                        )}
                        
                        <div className={`flex flex-col max-w-[80%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                          <div
                            className={`p-4 rounded-xl text-sm leading-relaxed border shadow-md ${
                              msg.role === "user"
                                ? "bg-blue-600/10 border-blue-500/20 text-gray-100"
                                : "bg-[#11162C] border-[#1E2540] text-gray-200 prose prose-invert"
                            }`}
                          >
                            {msg.role === "user" ? (
                              msg.content
                            ) : (
                              <div dangerouslySetInnerHTML={{ __html: marked.parse(msg.content) }} />
                            )}
                          </div>
                          {msg.timestamp && (
                            <span className="text-[9px] text-gray-500 mt-1 px-1">
                              {msg.timestamp} {msg.model && `• via ${msg.model}`}
                            </span>
                          )}
                        </div>

                        {msg.role === "user" && (
                          <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
                            <Hash className="w-4.5 h-4.5 text-blue-400" />
                          </div>
                        )}
                      </div>
                    ))
                  )}
                  {isChatStreaming && (
                    <div className="flex gap-4 max-w-4xl mx-auto justify-start">
                      <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                        <Sparkles className="w-4.5 h-4.5 text-indigo-400 animate-pulse" />
                      </div>
                      <div className="bg-[#11162C] border-[#1E2540] p-4 rounded-xl text-sm border shadow-md text-gray-400 flex items-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                        <span>rekipedia is thinking...</span>
                      </div>
                    </div>
                  )}
                  <div ref={chatBottomRef} />
                </div>

                {/* Chat Input Board */}
                <div className="p-4 border-t border-[#1E2540] bg-[#0A0D18]">
                  <form onSubmit={handleChatSubmit} className="max-w-4xl mx-auto flex gap-3">
                    <input
                      type="text"
                      placeholder="Ask rekipedia about symbols, modules, files..."
                      value={chatInput}
                      onChange={e => setChatInput(e.target.value)}
                      disabled={isChatStreaming}
                      className="flex-1 bg-[#12162A] border border-[#232B4E] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50 text-gray-100 placeholder-gray-500"
                    />
                    <button
                      type="submit"
                      disabled={!chatInput.trim() || isChatStreaming}
                      className="p-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl disabled:opacity-40 transition-all shadow-md flex-shrink-0"
                    >
                      <Send className="w-5 h-5" />
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: MODULE DEPENDENCY GRAPH CANVAS */}
          {activeTab === "graph" && (
            <div className="h-full flex relative bg-[#070A13]">
              {loadingGraph ? (
                <div className="flex-1 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                  <span className="text-xs text-gray-500">Parsing dependency graph...</span>
                </div>
              ) : (
                <>
                  {/* Canvas Container */}
                  <div className="flex-1 h-full relative">
                    <ReactFlow
                      nodes={nodes}
                      edges={edges}
                      onNodesChange={onNodesChange}
                      onEdgesChange={onEdgesChange}
                      onNodeClick={handleNodeClick}
                      fitView
                    >
                      <Controls className="bg-gray-900 border border-gray-700 text-gray-200" />
                      <MiniMap zoomable pannable nodeColor="#4B5563" className="bg-gray-950 border border-gray-800" />
                      <Background color="#1E2937" gap={16} size={1} />
                    </ReactFlow>
                  </div>

                  {/* Selected Node Inspector Panel (Right panel) */}
                  {selectedGraphNode && (
                    <div className="w-[320px] bg-[#0C101F] border-l border-[#1E2540] flex flex-col h-full animate-in slide-in-from-right duration-200">
                      <div className="p-4 border-b border-[#1E2540] flex items-center justify-between">
                        <h3 className="font-bold text-sm text-gray-200 truncate">Symbol Inspector</h3>
                        <button
                          onClick={() => setSelectedGraphNode(null)}
                          className="text-xs text-gray-400 hover:text-gray-100"
                        >
                          Close
                        </button>
                      </div>
                      <div className="p-4 flex-1 overflow-y-auto space-y-4 text-xs text-gray-300">
                        <div>
                          <div className="text-gray-500 font-semibold mb-1">Symbol Name</div>
                          <div className="font-mono bg-gray-900 px-2 py-1.5 rounded text-blue-400 border border-gray-800 font-bold break-all">
                            {selectedGraphNode.label}
                          </div>
                        </div>
                        <div>
                          <div className="text-gray-500 font-semibold mb-1">Defined In File</div>
                          <div className="font-mono text-gray-200 bg-gray-900 px-2 py-1.5 rounded border border-gray-800 break-all">
                            {selectedGraphNode.file}
                          </div>
                        </div>
                        <div className="flex gap-4">
                          <div>
                            <div className="text-gray-500 font-semibold">Kind</div>
                            <span className="inline-block px-2 py-0.5 mt-1 bg-indigo-900/30 border border-indigo-500/30 text-indigo-400 rounded uppercase font-bold text-[10px]">
                              {selectedGraphNode.kind}
                            </span>
                          </div>
                          <div>
                            <div className="text-gray-500 font-semibold">Workspace Group</div>
                            <span className="inline-block px-2 py-0.5 mt-1 bg-gray-900 border border-gray-700 text-gray-400 rounded uppercase text-[10px]">
                              {selectedGraphNode.group}
                            </span>
                          </div>
                        </div>
                        {selectedGraphNode.god && (
                          <div className="p-3 bg-red-950/20 border border-red-500/20 rounded-lg">
                            <div className="flex items-center gap-1.5 font-bold text-red-400 mb-1">
                              <Sparkles className="w-3.5 h-3.5" />
                              <span>God Class / Module</span>
                            </div>
                            <p className="text-[11px] text-gray-400 leading-normal">
                              This file has high structural complexity (high fan-in/fan-out couplings). Refactoring is advised.
                            </p>
                          </div>
                        )}
                        <div className="border-t border-[#1E2540] pt-4">
                          <button
                            onClick={() => {
                              setChatInput(`Deep-dive review of file '${selectedGraphNode.file}'. Detail its primary function and symbols.`);
                              setActiveTab("chat");
                            }}
                            className="w-full py-2.5 bg-[#12162B] hover:bg-[#1E2540] border border-[#232B4E] rounded-lg text-center font-semibold text-blue-400 flex items-center justify-center gap-1.5 transition-colors"
                          >
                            <Sparkles className="w-3.5 h-3.5" />
                            <span>Ask AI to review file</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* TAB 4: PERSONAL NOTES / INSIGHTS BOARD */}
          {activeTab === "notes" && (
            <div className="h-full overflow-y-auto px-8 py-10 bg-[#070A13]">
              <div className="max-w-4xl mx-auto space-y-8">
                {/* Board Description */}
                <div>
                  <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
                    <StickyNote className="w-5 h-5 text-indigo-400" />
                    <span>Insights, Refactor Notes & Decisions</span>
                  </h2>
                  <p className="text-xs text-gray-400 mt-1">
                    Capture scratchpad ideas, refactoring goals, and architecture designs. Notes are persisted in the central SQLite `.rekipedia/store.db` for multi-session access.
                  </p>
                </div>

                {/* Form to submit a new note */}
                <form onSubmit={handleAddNote} className="bg-[#0F1322] border border-[#1E2540] rounded-xl p-5 space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-400 uppercase mb-1.5">New Note Content</label>
                    <textarea
                      placeholder="Write your scratchpad notes or TODOs... (supports markdown)"
                      value={noteInput}
                      onChange={e => setNoteInput(e.target.value)}
                      rows={4}
                      className="w-full bg-[#161C33] border border-[#232B4E] rounded-lg p-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <label className="block text-xs font-bold text-gray-400 uppercase mb-1.5">Tags (Comma separated)</label>
                      <input
                        type="text"
                        placeholder="e.g. todo, refactor, architecture"
                        value={noteTags}
                        onChange={e => setNoteTags(e.target.value)}
                        className="w-full bg-[#161C33] border border-[#232B4E] rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                    <div className="flex items-end">
                      <button
                        type="submit"
                        disabled={!noteInput.trim()}
                        className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-sm rounded-lg shadow-md transition-all disabled:opacity-50"
                      >
                        <Plus className="w-4 h-4" />
                        <span>Add Note</span>
                      </button>
                    </div>
                  </div>
                </form>

                {/* Notes Feed Grid */}
                {loadingNotes ? (
                  <div className="flex items-center justify-center p-8">
                    <Loader2 className="w-8 h-8 text-gray-500 animate-spin" />
                  </div>
                ) : notes.length === 0 ? (
                  <div className="text-sm text-gray-500 italic text-center py-10 bg-[#0F1322]/20 border border-dashed border-[#1E2540] rounded-xl">
                    No notes saved yet. Add your first codebase insight!
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {notes.map(note => (
                      <div
                        key={note.id}
                        className="bg-[#0F1322] border border-[#1E2540] hover:border-[#283155] rounded-xl p-5 flex flex-col justify-between shadow-md group transition-all"
                      >
                        <div className="space-y-3">
                          {/* Note Body */}
                          <div
                            className="text-sm leading-relaxed text-gray-200 prose prose-invert prose-sm"
                            dangerouslySetInnerHTML={{ __html: marked.parse(note.content) }}
                          />
                        </div>

                        {/* Note Metadata and delete */}
                        <div className="flex items-center justify-between border-t border-[#1E2540]/60 pt-4 mt-4">
                          <div className="flex flex-wrap gap-1">
                            {note.tags ? (
                              note.tags.split(",").map(tag => (
                                <span
                                  key={tag}
                                  className="flex items-center gap-1 px-2 py-0.5 bg-[#171D35] text-indigo-400 rounded-full text-[10px] font-medium border border-indigo-500/10"
                                >
                                  <Tag className="w-2.5 h-2.5" />
                                  <span>{tag.trim()}</span>
                                </span>
                              ))
                            ) : (
                              <span className="text-[10px] text-gray-600">no tags</span>
                            )}
                          </div>
                          
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] text-gray-500">
                              {new Date(note.created_at).toLocaleDateString()}
                            </span>
                            <button
                              onClick={() => handleDeleteNote(note.id)}
                              className="p-1 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
