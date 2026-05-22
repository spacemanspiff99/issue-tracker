```index.tsx
import "./index.css";
import React from "react";
import { render } from "react-dom";
import { App } from "./App";

render(<App />, document.getElementById("root"));

```
```App.tsx
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { IssueProvider } from './components/IssueContext'
import { IssueDrawer } from './components/IssueDrawer'
import { AppShell } from './components/AppShell'
import { Overview } from './pages/Overview'
import { Board } from './pages/Board'
import { Backlog } from './pages/Backlog'
import { Releases } from './pages/Releases'
import { Intake } from './pages/Intake'
import { IssueDetail } from './pages/IssueDetail'
export function App() {
  return (
    <BrowserRouter>
      <IssueProvider>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<Overview />} />
            <Route path="board" element={<Board />} />
            <Route path="backlog" element={<Backlog />} />
            <Route path="releases" element={<Releases />} />
            <Route path="intake" element={<Intake />} />
            <Route path="issue/:id" element={<IssueDetail />} />

            {/* Placeholders for other nav items */}
            <Route
              path="categories"
              element={<div className="p-8">Categories Placeholder</div>}
            />
            <Route
              path="sprints"
              element={<div className="p-8">Sprints Placeholder</div>}
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
        <IssueDrawer />
      </IssueProvider>
    </BrowserRouter>
  )
}

```
```index.css
/* @import url() FONT IMPORTS MUST ALWAYS BE AT THE VERY TOP OF THIS FILE, ABOVE THE TAILWIND IMPORTS — DO NOT DELETE THIS COMMENT */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* CRITICAL: THE FOLLOWING TAILWIND IMPORTS MUST NEVER BE DELETED OR REORDERED — DO NOT DELETE THIS COMMENT */
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';

/* END TAILWIND IMPORTS — ALL OTHER CSS MUST GO BELOW THIS LINE */

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --ring: 0 0% 9%;
    --radius: 0.3rem;
  }
  body {
    @apply bg-white text-slate-900 font-sans antialiased;
  }
}
@layer utilities {
  .state-intake { @apply bg-slate-100 text-slate-700 border-slate-200; }
  .state-clarify { @apply bg-amber-50 text-amber-700 border-amber-200; }
  .state-ready { @apply bg-violet-50 text-violet-700 border-violet-200; }
  .state-implementing { @apply bg-blue-50 text-blue-700 border-blue-200; }
  .state-verifying { @apply bg-teal-50 text-teal-700 border-teal-200; }
  .state-closed { @apply bg-green-50 text-green-700 border-green-200; }
  .scrollbar-hide::-webkit-scrollbar {
    display: none;
  }
  .scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
}

```
```tailwind.config.js

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./*.{js,ts,jsx,tsx}",
    "./**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
      },
    },
  },
  plugins: [],
}

```
```components/mockData.ts
export type WorkflowState =
  | 'intake'
  | 'clarify'
  | 'ready-for-codex'
  | 'implementing'
  | 'verifying'
  | 'closed'
export type Priority = 'low' | 'medium' | 'high' | 'urgent'

export interface Category {
  id: string
  name: string
  issueCount: number
}

export interface Sprint {
  id: string
  sequence: string
  name: string
  startDate: string
  endDate: string
  isActive: boolean
  progress: number
  issueCount: number
}

export interface Release {
  id: string
  name: string
  progress: number
  blockerCount: number
  unscheduledCount: number
  linkedSprints: string[]
  readinessNotes: string
}

export interface Issue {
  id: string
  sequence: string
  title: string
  status: WorkflowState
  priority: Priority
  categoryId: string
  summary: string
  proposedApproach?: string
  acceptanceCriteria: { id: string; text: string; done: boolean }[]
  dependencies: string[]
  isBlocked: boolean
  assignee?: { name: string; isBot: boolean; avatar?: string }
  sprintId?: string
  releaseId?: string
  createdAt: string
  updatedAt: string
  reporter: string
  closeout?: {
    originatingLlm: string
    closedBy: string
    closeNote: string
    closedAt: string
  }
}

export const categories: Category[] = [
  { id: 'cat-1', name: 'Backend', issueCount: 12 },
  { id: 'cat-2', name: 'MCP', issueCount: 8 },
  { id: 'cat-3', name: 'Web UI', issueCount: 24 },
  { id: 'cat-4', name: 'Migrations', issueCount: 3 },
  { id: 'cat-5', name: 'Voice Intake', issueCount: 5 },
]

export const sprints: Sprint[] = [
  {
    id: 'spr-1',
    sequence: '0041',
    name: 'Sprint 41',
    startDate: '2026-05-01',
    endDate: '2026-05-14',
    isActive: false,
    progress: 100,
    issueCount: 15,
  },
  {
    id: 'spr-2',
    sequence: '0042',
    name: 'Sprint 42',
    startDate: '2026-05-15',
    endDate: '2026-05-28',
    isActive: true,
    progress: 35,
    issueCount: 12,
  },
]

export const releases: Release[] = [
  {
    id: 'rel-1',
    name: 'v1.2.0 - Voice Intake Core',
    progress: 80,
    blockerCount: 1,
    unscheduledCount: 2,
    linkedSprints: ['0041', '0042'],
    readinessNotes: 'Awaiting final UAT on voice recording permissions.',
  },
  {
    id: 'rel-2',
    name: 'v1.3.0 - MCP Expansion',
    progress: 10,
    blockerCount: 0,
    unscheduledCount: 8,
    linkedSprints: [],
    readinessNotes: 'Planning phase.',
  },
]

export const issues: Issue[] = [
  {
    id: 'iss-1',
    sequence: '0142',
    title: 'Add Alembic migration for issue.milestone column',
    status: 'closed',
    priority: 'high',
    categoryId: 'cat-4',
    summary:
      'We need to support releases by adding a milestone column to the issue table.',
    proposedApproach:
      'Create a new alembic revision. Add `milestone_id` foreign key to `issues` table referencing `milestones.id`.',
    acceptanceCriteria: [
      { id: 'ac-1', text: 'Migration script created', done: true },
      { id: 'ac-2', text: 'Tests pass locally', done: true },
    ],
    dependencies: [],
    isBlocked: false,
    assignee: { name: 'codex-bot', isBot: true },
    sprintId: 'spr-1',
    releaseId: 'rel-1',
    createdAt: '2026-05-02T10:00:00Z',
    updatedAt: '2026-05-03T14:30:00Z',
    reporter: 'human-admin',
    closeout: {
      originatingLlm: 'gpt-4o',
      closedBy: 'human-admin',
      closeNote: 'Verified migration applied successfully in UAT.',
      closedAt: '2026-05-03T14:30:00Z',
    },
  },
  {
    id: 'iss-2',
    sequence: '0143',
    title:
      'MCP server: compact next-action tool returns wrong shape on empty sprint',
    status: 'implementing',
    priority: 'high',
    categoryId: 'cat-2',
    summary:
      'When a sprint has no issues, the next-action tool returns an array instead of the expected object shape with a message.',
    proposedApproach:
      'Update `get_next_action` in `mcp/server.py` to check for empty results and return the fallback object.',
    acceptanceCriteria: [
      {
        id: 'ac-1',
        text: 'Tool returns `{ "status": "empty", "message": "..." }` when sprint is empty',
        done: false,
      },
      { id: 'ac-2', text: 'MCP unit tests updated', done: false },
    ],
    dependencies: [],
    isBlocked: false,
    assignee: { name: 'claude-agent', isBot: true },
    sprintId: 'spr-2',
    releaseId: 'rel-2',
    createdAt: '2026-05-14T09:15:00Z',
    updatedAt: '2026-05-15T11:20:00Z',
    reporter: 'human-admin',
  },
  {
    id: 'iss-3',
    sequence: '0144',
    title:
      'Voice intake: record button stuck in recording state after permission denial',
    status: 'verifying',
    priority: 'urgent',
    categoryId: 'cat-5',
    summary:
      'If the user denies microphone permissions, the UI still shows the recording animation.',
    proposedApproach:
      'Catch the `NotAllowedError` from `getUserMedia` and reset the recording state.',
    acceptanceCriteria: [
      {
        id: 'ac-1',
        text: 'UI resets to idle state on permission denial',
        done: true,
      },
      { id: 'ac-2', text: 'Toast error message shown to user', done: true },
    ],
    dependencies: [],
    isBlocked: false,
    assignee: { name: 'codex-bot', isBot: true },
    sprintId: 'spr-2',
    releaseId: 'rel-1',
    createdAt: '2026-05-14T16:45:00Z',
    updatedAt: '2026-05-15T10:05:00Z',
    reporter: 'human-admin',
  },
  {
    id: 'iss-4',
    sequence: '0145',
    title: 'Design system: implement workflow state pill colors',
    status: 'ready-for-codex',
    priority: 'medium',
    categoryId: 'cat-3',
    summary: 'Need consistent pill colors for workflow states across the app.',
    acceptanceCriteria: [
      { id: 'ac-1', text: 'CSS classes created for all 6 states', done: false },
      { id: 'ac-2', text: 'Applied to Board and Overview', done: false },
    ],
    dependencies: ['0144'],
    isBlocked: true,
    sprintId: 'spr-2',
    createdAt: '2026-05-15T08:00:00Z',
    updatedAt: '2026-05-15T08:00:00Z',
    reporter: 'human-admin',
  },
  {
    id: 'iss-5',
    sequence: '0146',
    title: 'Audio upload fails for files > 5MB',
    status: 'clarify',
    priority: 'medium',
    categoryId: 'cat-5',
    summary: 'FastAPI is rejecting large audio files during voice intake.',
    acceptanceCriteria: [
      { id: 'ac-1', text: 'Increase max upload size to 25MB', done: false },
    ],
    dependencies: [],
    isBlocked: false,
    createdAt: '2026-05-15T09:30:00Z',
    updatedAt: '2026-05-15T09:30:00Z',
    reporter: 'human-admin',
  },
  {
    id: 'iss-6',
    sequence: '0147',
    title: 'Implement drag and drop for board columns',
    status: 'intake',
    priority: 'low',
    categoryId: 'cat-3',
    summary: 'Users want to drag issues between workflow states on the board.',
    acceptanceCriteria: [
      { id: 'ac-1', text: 'Use framer-motion for drag', done: false },
      { id: 'ac-2', text: 'Update backend on drop', done: false },
    ],
    dependencies: [],
    isBlocked: false,
    createdAt: '2026-05-15T10:15:00Z',
    updatedAt: '2026-05-15T10:15:00Z',
    reporter: 'human-admin',
  },
]

export const projectInfo = {
  name: 'Issue Tracker Core',
  sequence: 'ITCR',
  kpis: {
    totalIssues: 147,
    donePercent: 68,
    blockedCount: 3,
    uncategorizedCount: 12,
  },
  workflowCounts: {
    intake: 5,
    clarify: 3,
    'ready-for-codex': 12,
    implementing: 4,
    verifying: 2,
    closed: 121,
  },
}

```
```components/AppShell.tsx
import React, { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  KanbanSquare,
  ListTodo,
  Milestone,
  Mic,
  Tags,
  Timer,
  Search,
  Plus,
  TerminalSquare,
  Sparkles,
} from 'lucide-react'
import { projectInfo } from './mockData'
import { CreateIssueModal } from './CreateIssueModal'
const navItems = [
  {
    name: 'Overview',
    path: '/',
    icon: LayoutDashboard,
  },
  {
    name: 'Board',
    path: '/board',
    icon: KanbanSquare,
  },
  {
    name: 'Backlog',
    path: '/backlog',
    icon: ListTodo,
  },
  {
    name: 'Releases',
    path: '/releases',
    icon: Milestone,
  },
  {
    name: 'Intake',
    path: '/intake',
    icon: Mic,
  },
  {
    name: 'Categories',
    path: '/categories',
    icon: Tags,
  },
  {
    name: 'Sprints',
    path: '/sprints',
    icon: Timer,
  },
]
export function AppShell() {
  const location = useLocation()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const currentNavName =
    navItems.find((item) =>
      item.path === '/'
        ? location.pathname === '/'
        : location.pathname.startsWith(item.path),
    )?.name || 'Issue'
  return (
    <>
      <CreateIssueModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />
      <div className="flex h-screen w-full bg-gradient-to-br from-purple-50 via-pink-50 to-orange-50 text-slate-900 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-64 border-r border-purple-200 bg-gradient-to-b from-purple-100 to-pink-100 flex flex-col flex-shrink-0 shadow-lg">
          {/* Project Switcher */}
          <div className="h-14 flex items-center px-4 border-b border-purple-300 hover:bg-white/50 cursor-pointer transition-colors">
            <div className="flex items-center gap-2 w-full">
              <div className="w-6 h-6 bg-gradient-to-br from-purple-600 to-pink-600 rounded-lg flex items-center justify-center text-white text-xs font-bold shadow-md">
                IT
              </div>
              <div className="flex-1 overflow-hidden">
                <div className="text-sm font-bold truncate text-purple-900">
                  {projectInfo.name}
                </div>
                <div className="text-xs text-purple-600 font-mono">
                  {projectInfo.sequence}
                </div>
              </div>
            </div>
          </div>

          {/* Section Nav */}
          <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.name}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${isActive ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg transform scale-105' : 'text-purple-700 hover:bg-white/50 hover:text-purple-900'}`
                  }
                >
                  <Icon className="w-4 h-4" />
                  {item.name}
                </NavLink>
              )
            })}
          </nav>

          {/* Local Indicator */}
          <div className="p-4 border-t border-purple-300">
            <div className="flex items-center gap-2 text-xs text-purple-700 font-mono bg-white/50 px-2 py-1.5 rounded-lg border border-purple-300 shadow-sm">
              <TerminalSquare className="w-3.5 h-3.5" />
              <span>localhost:8000</span>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col min-w-0">
          {/* Top Bar */}
          <header className="h-14 border-b-2 border-purple-200 flex items-center justify-between px-6 flex-shrink-0 bg-gradient-to-r from-white via-purple-50 to-pink-50 shadow-sm">
            <div className="flex items-center text-sm text-purple-600 font-medium">
              <span className="font-bold text-purple-900">
                {projectInfo.sequence}
              </span>
              <span className="mx-2 text-purple-400">/</span>
              <span className="text-purple-700">{currentNavName}</span>
            </div>

            <div className="flex items-center gap-4">
              <div className="relative group">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-purple-400" />
                <input
                  type="text"
                  placeholder="Search..."
                  className="pl-9 pr-12 py-2 bg-white border-2 border-purple-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 w-64 transition-all shadow-sm"
                />
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
                  <kbd className="font-mono text-[10px] bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded border border-purple-300">
                    ⌘
                  </kbd>
                  <kbd className="font-mono text-[10px] bg-purple-100 text-purple-600 px-1.5 py-0.5 rounded border border-purple-300">
                    K
                  </kbd>
                </div>
              </div>

              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="flex items-center gap-2 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 text-white px-4 py-2 rounded-xl text-sm font-bold hover:from-purple-600 hover:via-pink-600 hover:to-orange-600 transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <Sparkles className="w-4 h-4" />
                <span>Issue</span>
                <kbd className="font-mono text-[10px] bg-white/20 text-white px-1.5 py-0.5 rounded ml-1">
                  C
                </kbd>
              </button>
            </div>
          </header>

          {/* Page Content */}
          <div className="flex-1 overflow-auto bg-white">
            <Outlet />
          </div>
        </main>
      </div>
    </>
  )
}

```
```pages/Overview.tsx
import React, { Children } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { useIssue } from '../components/IssueContext'
import {
  projectInfo,
  sprints,
  releases,
  categories,
  issues,
  WorkflowState,
} from '../components/mockData'
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ListTodo,
  Mic,
  Plus,
  ArrowRight,
  Clock,
  Activity,
  Bot,
} from 'lucide-react'
const containerVariants = {
  hidden: {
    opacity: 0,
  },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
    },
  },
}
const itemVariants = {
  hidden: {
    opacity: 0,
    y: 10,
  },
  visible: {
    opacity: 1,
    y: 0,
  },
}
export function Overview() {
  const { openIssue } = useIssue()
  const activeSprint = sprints.find((s) => s.isActive)
  // Mock recent activity
  const recentActivity = [
    {
      id: 1,
      issueId: 'ITCR-0142',
      action: 'closed issue',
      actor: 'codex-bot',
      isBot: true,
      time: '2 hours ago',
    },
    {
      id: 2,
      issueId: 'ITCR-0144',
      action: 'moved to verifying',
      actor: 'claude-agent',
      isBot: true,
      time: '4 hours ago',
    },
    {
      id: 3,
      issueId: 'ITCR-0145',
      action: 'created issue',
      actor: 'human-admin',
      isBot: false,
      time: '1 day ago',
    },
    {
      id: 4,
      issueId: 'ITCR-0146',
      action: 'added voice intake',
      actor: 'human-admin',
      isBot: false,
      time: '1 day ago',
    },
  ]
  return (
    <motion.div
      className="p-8 max-w-6xl mx-auto space-y-8"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div
        variants={itemVariants}
        className="flex justify-between items-end"
      >
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {projectInfo.name}
          </h1>
          <p className="text-slate-500 mt-1">
            Local-first project tracker for steering AI coding work.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/intake"
            className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-md text-sm font-medium transition-colors"
          >
            <Mic className="w-4 h-4" />
            Voice Intake
          </Link>
          <button className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
            <Plus className="w-4 h-4" />
            New Issue
          </button>
        </div>
      </motion.div>

      {/* KPIs */}
      <motion.div variants={itemVariants} className="grid grid-cols-4 gap-4">
        <div className="border border-slate-200 rounded-lg p-4 bg-white">
          <div className="text-sm text-slate-500 flex items-center gap-2 mb-2">
            <ListTodo className="w-4 h-4" /> Total Issues
          </div>
          <div className="text-2xl font-semibold">
            {projectInfo.kpis.totalIssues}
          </div>
        </div>
        <div className="border border-slate-200 rounded-lg p-4 bg-white">
          <div className="text-sm text-slate-500 flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4" /> Done
          </div>
          <div className="text-2xl font-semibold">
            {projectInfo.kpis.donePercent}%
          </div>
        </div>
        <div className="border border-slate-200 rounded-lg p-4 bg-white">
          <div className="text-sm text-slate-500 flex items-center gap-2 mb-2">
            <AlertCircle className="w-4 h-4" /> Blocked
          </div>
          <div className="text-2xl font-semibold text-red-600">
            {projectInfo.kpis.blockedCount}
          </div>
        </div>
        <div className="border border-slate-200 rounded-lg p-4 bg-white">
          <div className="text-sm text-slate-500 flex items-center gap-2 mb-2">
            <HelpCircle className="w-4 h-4" /> Uncategorized
          </div>
          <div className="text-2xl font-semibold">
            {projectInfo.kpis.uncategorizedCount}
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-3 gap-8">
        {/* Left Column */}
        <div className="col-span-2 space-y-8">
          {/* AI Workflow Counts */}
          <motion.div
            variants={itemVariants}
            className="border border-slate-200 rounded-lg bg-white overflow-hidden"
          >
            <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50">
              <h2 className="text-sm font-semibold text-slate-900">
                AI Workflow States
              </h2>
            </div>
            <div className="p-5">
              <div className="flex gap-2 mb-4">
                {Object.entries(projectInfo.workflowCounts).map(
                  ([state, count]) => {
                    const percent = (count / projectInfo.kpis.totalIssues) * 100
                    return (
                      <div
                        key={state}
                        className={`h-2 rounded-full state-${state.replace('-for-codex', '')}`}
                        style={{
                          width: `${Math.max(percent, 2)}%`,
                        }}
                        title={`${state}: ${count}`}
                      />
                    )
                  },
                )}
              </div>
              <div className="grid grid-cols-3 gap-3">
                {Object.entries(projectInfo.workflowCounts).map(
                  ([state, count]) => (
                    <div
                      key={state}
                      className="flex items-center justify-between p-2 rounded border border-slate-100 bg-slate-50"
                    >
                      <span className="text-xs font-medium text-slate-600 capitalize">
                        {state.replace(/-/g, ' ')}
                      </span>
                      <span className="text-xs font-mono font-semibold text-slate-900">
                        {count}
                      </span>
                    </div>
                  ),
                )}
              </div>
            </div>
          </motion.div>

          {/* Active Sprint & Releases */}
          <div className="grid grid-cols-2 gap-4">
            {/* Active Sprint */}
            <motion.div
              variants={itemVariants}
              className="border border-slate-200 rounded-lg bg-white flex flex-col"
            >
              <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-slate-900">
                  Active Sprint
                </h2>
                <Link
                  to="/board"
                  className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1"
                >
                  Board <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
              {activeSprint ? (
                <div className="p-5 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200">
                        #{activeSprint.sequence}
                      </span>
                      <span className="font-medium text-sm">
                        {activeSprint.name}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 flex items-center gap-1 mb-4">
                      <Clock className="w-3 h-3" />
                      {activeSprint.startDate} to {activeSprint.endDate}
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-500">
                        {activeSprint.issueCount} issues
                      </span>
                      <span className="font-medium">
                        {activeSprint.progress}% done
                      </span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-slate-900 rounded-full"
                        style={{
                          width: `${activeSprint.progress}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-5 text-sm text-slate-500 flex-1 flex items-center justify-center">
                  No active sprint.
                </div>
              )}
            </motion.div>

            {/* Release Readiness */}
            <motion.div
              variants={itemVariants}
              className="border border-slate-200 rounded-lg bg-white flex flex-col"
            >
              <div className="px-5 py-4 border-b border-slate-200 bg-slate-50/50 flex justify-between items-center">
                <h2 className="text-sm font-semibold text-slate-900">
                  Next Release
                </h2>
                <Link
                  to="/releases"
                  className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1"
                >
                  All <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
              <div className="p-5 flex-1 flex flex-col justify-between">
                {releases[0] && (
                  <>
                    <div>
                      <div className="font-medium text-sm mb-2">
                        {releases[0].name}
                      </div>
                      {releases[0].blockerCount > 0 && (
                        <div className="inline-flex items-center gap-1 text-xs text-red-700 bg-red-50 border border-red-200 px-2 py-1 rounded mb-3">
                          <AlertCircle className="w-3 h-3" />
                          {releases[0].blockerCount} Blocker
                        </div>
                      )}
                      <p className="text-xs text-slate-500 line-clamp-2 mb-4">
                        {releases[0].readinessNotes}
                      </p>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs mb-1.5">
                        <span className="text-slate-500">Progress</span>
                        <span className="font-medium">
                          {releases[0].progress}%
                        </span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-slate-900 rounded-full"
                          style={{
                            width: `${releases[0].progress}%`,
                          }}
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-8">
          {/* Saved Views */}
          <motion.div
            variants={itemVariants}
            className="border border-slate-200 rounded-lg bg-white"
          >
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/50">
              <h2 className="text-sm font-semibold text-slate-900">
                Saved Views
              </h2>
            </div>
            <div className="p-2 space-y-0.5">
              {[
                'All Issues',
                'Backlog',
                'Active Sprint',
                'Blocked',
                'Done',
                'Uncategorized',
              ].map((view) => (
                <Link
                  key={view}
                  to="/board"
                  className="block px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 rounded-md transition-colors"
                >
                  {view}
                </Link>
              ))}
            </div>
          </motion.div>

          {/* Recent Activity */}
          <motion.div
            variants={itemVariants}
            className="border border-slate-200 rounded-lg bg-white"
          >
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/50 flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-500" />
              <h2 className="text-sm font-semibold text-slate-900">
                Recent Activity
              </h2>
            </div>
            <div className="p-4">
              <div className="space-y-4 relative before:absolute before:inset-0 before:ml-2 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
                {recentActivity.map((activity, index) => (
                  <div
                    key={activity.id}
                    className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
                  >
                    <div className="flex items-center justify-center w-4 h-4 rounded-full border border-white bg-slate-200 text-slate-500 shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                      {activity.isBot ? (
                        <Bot className="w-2.5 h-2.5" />
                      ) : (
                        <div className="w-1.5 h-1.5 bg-slate-500 rounded-full" />
                      )}
                    </div>
                    <div className="w-[calc(100%-2rem)] md:w-[calc(50%-1rem)] p-3 rounded border border-slate-100 bg-slate-50 shadow-sm">
                      <div className="flex items-center justify-between mb-1">
                        <span
                          className={`text-xs font-medium ${activity.isBot ? 'font-mono text-blue-600' : 'text-slate-700'}`}
                        >
                          {activity.actor}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {activity.time}
                        </span>
                      </div>
                      <div className="text-xs text-slate-600">
                        {activity.action}{' '}
                        <span
                          onClick={() => openIssue(activity.issueId)}
                          className="font-mono text-purple-600 font-semibold cursor-pointer hover:underline"
                        >
                          {activity.issueId}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Categories */}
          <motion.div
            variants={itemVariants}
            className="border border-slate-200 rounded-lg bg-white"
          >
            <div className="px-4 py-3 border-b border-slate-200 bg-slate-50/50">
              <h2 className="text-sm font-semibold text-slate-900">
                Categories
              </h2>
            </div>
            <div className="p-2 space-y-0.5">
              {categories.map((cat) => (
                <div
                  key={cat.id}
                  className="flex items-center justify-between px-3 py-2 text-sm text-slate-600 rounded-md"
                >
                  <span>{cat.name}</span>
                  <span className="text-xs font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-500">
                    {cat.issueCount}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}

```
```pages/Board.tsx
import React, { useState } from 'react'
import { motion, Reorder } from 'framer-motion'
import { useIssue } from '../components/IssueContext'
import {
  issues as initialIssues,
  sprints,
  categories,
  WorkflowState,
} from '../components/mockData'
import {
  MoreHorizontal,
  Plus,
  AlertCircle,
  Link as LinkIcon,
  Bot,
  User,
  GripVertical,
  ChevronDown,
  Filter,
} from 'lucide-react'
const WORKFLOW_STATES: {
  id: WorkflowState
  label: string
}[] = [
  {
    id: 'intake',
    label: 'Intake',
  },
  {
    id: 'clarify',
    label: 'Clarify',
  },
  {
    id: 'ready-for-codex',
    label: 'Ready for Codex',
  },
  {
    id: 'implementing',
    label: 'Implementing',
  },
  {
    id: 'verifying',
    label: 'Verifying',
  },
  {
    id: 'closed',
    label: 'Closed',
  },
]
export function Board() {
  const { openIssue } = useIssue()
  const [issues, setIssues] = useState(initialIssues)
  const activeSprint = sprints.find((s) => s.isActive)
  const [selectedSprint, setSelectedSprint] = useState(
    activeSprint?.id || 'all',
  )
  const filteredIssues = issues.filter((issue) =>
    selectedSprint === 'all' ? true : issue.sprintId === selectedSprint,
  )
  const getCategoryName = (id: string) =>
    categories.find((c) => c.id === id)?.name || 'Unknown'
  const PriorityIcon = ({ priority }: { priority: string }) => {
    switch (priority) {
      case 'urgent':
        return (
          <div className="w-2 h-2 rounded-full bg-red-500" title="Urgent" />
        )
      case 'high':
        return (
          <div className="w-2 h-2 rounded-full bg-orange-500" title="High" />
        )
      case 'medium':
        return (
          <div className="w-2 h-2 rounded-full bg-yellow-500" title="Medium" />
        )
      case 'low':
        return <div className="w-2 h-2 rounded-full bg-slate-300" title="Low" />
      default:
        return null
    }
  }
  return (
    <div className="h-full flex flex-col bg-white">
      {/* Board Header */}
      <header className="px-6 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold text-slate-900">Board</h1>

          {/* Sprint Selector */}
          <div className="relative">
            <select
              value={selectedSprint}
              onChange={(e) => setSelectedSprint(e.target.value)}
              className="appearance-none bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-md pl-3 pr-8 py-1.5 font-medium focus:outline-none focus:ring-2 focus:ring-slate-400 cursor-pointer"
            >
              <option value="all">All Work</option>
              {sprints.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} {s.isActive ? '(Active)' : ''}
                </option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-md hover:bg-slate-100 transition-colors">
            <Filter className="w-4 h-4" />
            Filter
          </button>
          <div className="w-px h-4 bg-slate-200 mx-1" />
          <button className="text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-md hover:bg-slate-100 transition-colors">
            Backlog
          </button>
        </div>
      </header>

      {/* Board Columns */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden p-6">
        <div className="flex gap-6 h-full min-w-max">
          {WORKFLOW_STATES.map((state) => {
            const columnIssues = filteredIssues.filter(
              (i) => i.status === state.id,
            )
            return (
              <div key={state.id} className="w-80 flex flex-col h-full">
                {/* Column Header */}
                <div className="flex items-center justify-between mb-3 px-1">
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-2.5 h-2.5 rounded-full state-${state.id.replace('-for-codex', '')} border`}
                    />
                    <h2 className="text-sm font-semibold text-slate-700">
                      {state.label}
                    </h2>
                    <span className="text-xs font-mono text-slate-400 bg-slate-100 px-1.5 rounded">
                      {columnIssues.length}
                    </span>
                  </div>
                  <button className="text-slate-400 hover:text-slate-600 p-1 rounded hover:bg-slate-100">
                    <Plus className="w-4 h-4" />
                  </button>
                </div>

                {/* Column Cards */}
                <div className="flex-1 overflow-y-auto scrollbar-hide pb-4">
                  <div className="space-y-3 min-h-[100px]">
                    {columnIssues.map((issue) => (
                      <motion.div
                        layoutId={issue.id}
                        key={issue.id}
                        onClick={() => openIssue(issue.id)}
                        className="group bg-gradient-to-br from-white to-slate-50 border-2 border-slate-200 hover:border-purple-300 rounded-xl p-3 shadow-sm hover:shadow-md transition-all cursor-pointer relative"
                      >
                        <div className="absolute left-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 cursor-grab text-purple-300 hover:text-purple-500 transition-opacity">
                          <GripVertical className="w-4 h-4" />
                        </div>

                        <div className="pl-4">
                          <div className="flex items-start justify-between mb-2">
                            <span className="font-mono text-xs text-purple-600 font-semibold">
                              #{issue.sequence}
                            </span>
                            <div className="flex items-center gap-1.5">
                              {issue.isBlocked && (
                                <AlertCircle className="w-3.5 h-3.5 text-red-500" />
                              )}
                              {issue.dependencies.length > 0 && (
                                <LinkIcon className="w-3.5 h-3.5 text-blue-400" />
                              )}
                            </div>
                          </div>

                          <h3 className="text-sm font-bold text-slate-900 mb-3 leading-snug group-hover:text-purple-700 transition-colors">
                            {issue.title}
                          </h3>

                          <div className="flex items-center justify-between mt-auto">
                            <div className="flex items-center gap-2">
                              <PriorityIcon priority={issue.priority} />
                              <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 truncate max-w-[120px]">
                                {getCategoryName(issue.categoryId)}
                              </span>
                            </div>

                            {issue.assignee && (
                              <div
                                className="w-5 h-5 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600"
                                title={issue.assignee.name}
                              >
                                {issue.assignee.isBot ? (
                                  <Bot className="w-3 h-3" />
                                ) : (
                                  <User className="w-3 h-3" />
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

```
```pages/Backlog.tsx
import React, { useState } from 'react'
import { motion, Reorder } from 'framer-motion'
import { useIssue } from '../components/IssueContext'
import { issues as initialIssues, categories } from '../components/mockData'
import {
  GripVertical,
  Search,
  Filter,
  Link as LinkIcon,
  AlertCircle,
  Save,
} from 'lucide-react'
export function Backlog() {
  const { openIssue } = useIssue()
  // Filter out closed issues for the backlog view
  const backlogIssues = initialIssues.filter((i) => i.status !== 'closed')
  const [items, setItems] = useState(backlogIssues)
  const [isDirty, setIsDirty] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const handleReorder = (newOrder: typeof items) => {
    setItems(newOrder)
    setIsDirty(true)
  }
  const handleSave = () => {
    setIsDirty(false)
    // Mock save action
  }
  const getCategoryName = (id: string) =>
    categories.find((c) => c.id === id)?.name || 'Unknown'
  const PriorityIcon = ({ priority }: { priority: string }) => {
    switch (priority) {
      case 'urgent':
        return (
          <div className="w-2 h-2 rounded-full bg-red-500" title="Urgent" />
        )
      case 'high':
        return (
          <div className="w-2 h-2 rounded-full bg-orange-500" title="High" />
        )
      case 'medium':
        return (
          <div className="w-2 h-2 rounded-full bg-yellow-500" title="Medium" />
        )
      case 'low':
        return <div className="w-2 h-2 rounded-full bg-slate-300" title="Low" />
      default:
        return null
    }
  }
  const filteredItems = items.filter(
    (item) =>
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.sequence.includes(searchQuery),
  )
  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <header className="px-6 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0 bg-white z-10">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold text-slate-900">Backlog</h1>
          <span className="text-sm text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full font-medium">
            {filteredItems.length} issues
          </span>
        </div>

        <div className="flex items-center gap-4">
          {isDirty && (
            <motion.button
              initial={{
                opacity: 0,
                scale: 0.9,
              }}
              animate={{
                opacity: 1,
                scale: 1,
              }}
              onClick={handleSave}
              className="flex items-center gap-1.5 bg-slate-900 text-white px-3 py-1.5 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors"
            >
              <Save className="w-4 h-4" />
              Save Order
            </motion.button>
          )}

          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search backlog..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 w-64"
            />
          </div>

          <button className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-md hover:bg-slate-100 transition-colors border border-slate-200">
            <Filter className="w-4 h-4" />
            Filter
          </button>
        </div>
      </header>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto">
          {/* List Header */}
          <div className="flex items-center px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200 mb-2">
            <div className="w-8"></div>
            <div className="w-20">ID</div>
            <div className="flex-1">Title</div>
            <div className="w-32">Status</div>
            <div className="w-32">Category</div>
            <div className="w-16 text-center">Pri</div>
            <div className="w-16 text-center">Deps</div>
          </div>

          <Reorder.Group
            axis="y"
            values={items}
            onReorder={handleReorder}
            className="space-y-1"
          >
            {filteredItems.map((item) => (
              <Reorder.Item
                key={item.id}
                value={item}
                className="flex items-center px-4 py-3 bg-white border border-slate-100 rounded-lg hover:border-slate-300 hover:shadow-sm transition-all group cursor-default"
              >
                {/* Drag Handle */}
                <div className="w-8 text-slate-300 cursor-grab active:cursor-grabbing group-hover:text-purple-500 transition-colors">
                  <GripVertical className="w-4 h-4" />
                </div>

                {/* ID */}
                <div className="w-20 font-mono text-sm text-purple-600 font-semibold">
                  #{item.sequence}
                </div>

                {/* Title */}
                <div className="flex-1 pr-4" onClick={() => openIssue(item.id)}>
                  <span className="text-sm font-bold text-slate-900 group-hover:text-purple-600 transition-colors cursor-pointer">
                    {item.title}
                  </span>
                </div>

                {/* Status */}
                <div className="w-32">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border state-${item.status.replace('-for-codex', '')}`}
                  >
                    {item.status.replace(/-/g, ' ')}
                  </span>
                </div>

                {/* Category */}
                <div className="w-32">
                  <select
                    value={item.categoryId}
                    onChange={(e) => {
                      const newItems = items.map((i) =>
                        i.id === item.id
                          ? {
                              ...i,
                              categoryId: e.target.value,
                            }
                          : i,
                      )
                      setItems(newItems)
                      setIsDirty(true)
                    }}
                    className="text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-1 rounded-lg border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-pointer w-full"
                  >
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Priority */}
                <div className="w-24 flex justify-center">
                  <select
                    value={item.priority}
                    onChange={(e) => {
                      const newItems = items.map((i) =>
                        i.id === item.id
                          ? {
                              ...i,
                              priority: e.target.value as any,
                            }
                          : i,
                      )
                      setItems(newItems)
                      setIsDirty(true)
                    }}
                    className="text-xs font-semibold text-slate-700 bg-slate-50 px-2 py-1 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-400 cursor-pointer w-full"
                  >
                    <option value="low">🟢 Low</option>
                    <option value="medium">🟡 Med</option>
                    <option value="high">🟠 High</option>
                    <option value="urgent">🔴 Urg</option>
                  </select>
                </div>

                {/* Deps */}
                <div className="w-16 flex justify-center gap-1.5">
                  {item.dependencies.length > 0 && (
                    <LinkIcon
                      className="w-4 h-4 text-slate-400"
                      title={`${item.dependencies.length} dependencies`}
                    />
                  )}
                  {item.isBlocked && (
                    <AlertCircle
                      className="w-4 h-4 text-red-500"
                      title="Blocked"
                    />
                  )}
                </div>
              </Reorder.Item>
            ))}
          </Reorder.Group>

          {filteredItems.length === 0 && (
            <div className="text-center py-12 text-slate-500 text-sm">
              No issues found matching your criteria.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

```
```pages/Releases.tsx
import React from 'react'
import { motion } from 'framer-motion'
import { releases, issues } from '../components/mockData'
import {
  Milestone,
  AlertCircle,
  Calendar,
  CheckCircle2,
  Timer,
  ChevronRight,
} from 'lucide-react'
export function Releases() {
  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <header className="px-6 py-4 border-b border-slate-200 flex items-center justify-between flex-shrink-0 bg-white">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Releases</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Milestone rollups across issues and sprints.
          </p>
        </div>
        <button className="bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
          New Release
        </button>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {releases.map((release, index) => {
            const releaseIssues = issues.filter(
              (i) => i.releaseId === release.id,
            )
            const totalIssues = releaseIssues.length
            const closedIssues = releaseIssues.filter(
              (i) => i.status === 'closed',
            ).length
            return (
              <motion.div
                key={release.id}
                initial={{
                  opacity: 0,
                  y: 10,
                }}
                animate={{
                  opacity: 1,
                  y: 0,
                }}
                transition={{
                  delay: index * 0.1,
                }}
                className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:border-slate-300 transition-colors shadow-sm"
              >
                {/* Release Header */}
                <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="mt-1 p-2 bg-white border border-slate-200 rounded-lg text-slate-700 shadow-sm">
                      <Milestone className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                        {release.name}
                        {release.progress === 100 && (
                          <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full font-medium flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Released
                          </span>
                        )}
                      </h2>
                      <div className="flex items-center gap-4 mt-2 text-sm text-slate-600">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-4 h-4 text-slate-400" />
                          <span>Target: Q2 2026</span>
                        </div>
                        {release.linkedSprints.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <Timer className="w-4 h-4 text-slate-400" />
                            <span>
                              Sprints:{' '}
                              {release.linkedSprints
                                .map((s) => `#${s}`)
                                .join(', ')}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <button className="text-slate-400 hover:text-slate-600 p-2 rounded-md hover:bg-slate-100 transition-colors">
                    <ChevronRight className="w-5 h-5" />
                  </button>
                </div>

                {/* Release Body */}
                <div className="p-5">
                  {/* Progress Section */}
                  <div className="mb-6">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-medium text-slate-700">
                        Overall Progress
                      </span>
                      <span className="font-semibold text-slate-900">
                        {release.progress}%
                      </span>
                    </div>
                    <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${release.progress === 100 ? 'bg-green-500' : 'bg-slate-900'}`}
                        style={{
                          width: `${release.progress}%`,
                        }}
                      />
                    </div>
                    <div className="flex justify-between mt-2 text-xs text-slate-500">
                      <span>
                        {closedIssues} of {totalIssues} issues closed
                      </span>
                      {release.unscheduledCount > 0 && (
                        <span className="text-amber-600">
                          {release.unscheduledCount} unscheduled issues
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Readiness Notes */}
                    <div className="bg-slate-50 rounded-lg p-4 border border-slate-100">
                      <h3 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-2">
                        Readiness Notes
                      </h3>
                      <p className="text-sm text-slate-700 leading-relaxed">
                        {release.readinessNotes ||
                          'No readiness notes provided.'}
                      </p>
                    </div>

                    {/* Stats & Blockers */}
                    <div className="space-y-3">
                      {release.blockerCount > 0 && (
                        <div className="flex items-center justify-between p-3 bg-red-50 border border-red-100 rounded-lg">
                          <div className="flex items-center gap-2 text-red-700 font-medium text-sm">
                            <AlertCircle className="w-4 h-4" />
                            Active Blockers
                          </div>
                          <span className="bg-red-100 text-red-700 font-mono text-sm px-2 py-0.5 rounded">
                            {release.blockerCount}
                          </span>
                        </div>
                      )}

                      <div className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg">
                        <span className="text-sm text-slate-600">
                          Total Scope
                        </span>
                        <span className="font-mono text-sm text-slate-900">
                          {totalIssues} issues
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

```
```pages/Intake.tsx
import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Mic,
  Square,
  Play,
  UploadCloud,
  AlertCircle,
  CheckCircle2,
  FileAudio,
  Trash2,
  HelpCircle,
} from 'lucide-react'
export function Intake() {
  const [title, setTitle] = useState('')
  const [notes, setNotes] = useState('')
  const [priority, setPriority] = useState('medium')
  const [needsClarification, setNeedsClarification] = useState(false)
  // Recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [hasRecording, setHasRecording] = useState(false)
  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submittedId, setSubmittedId] = useState<string | null>(null)
  // Faux timer
  useEffect(() => {
    let interval: number
    if (isRecording) {
      interval = window.setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [isRecording])
  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }
  const handleStartRecording = () => {
    setIsRecording(true)
    setHasRecording(false)
    setRecordingTime(0)
  }
  const handleStopRecording = () => {
    setIsRecording(false)
    setHasRecording(true)
  }
  const handleDeleteRecording = () => {
    setHasRecording(false)
    setRecordingTime(0)
  }
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    // Mock submission delay
    setTimeout(() => {
      setIsSubmitting(false)
      setSubmittedId('ITCR-0148')
    }, 1500)
  }
  if (submittedId) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50 p-6">
        <motion.div
          initial={{
            opacity: 0,
            scale: 0.95,
          }}
          animate={{
            opacity: 1,
            scale: 1,
          }}
          className="bg-white border border-slate-200 rounded-xl p-8 max-w-md w-full text-center shadow-sm"
        >
          <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-semibold text-slate-900 mb-2">
            Intake Issue Created
          </h2>
          <p className="text-slate-500 mb-8">
            Your voice feedback has been saved and an issue has been created in
            the backlog.
          </p>
          <div className="flex flex-col gap-3">
            <Link
              to={`/issue/${submittedId}`}
              className="bg-slate-900 text-white px-4 py-2.5 rounded-md font-medium hover:bg-slate-800 transition-colors"
            >
              View Issue {submittedId}
            </Link>
            <button
              onClick={() => {
                setSubmittedId(null)
                setTitle('')
                setNotes('')
                setHasRecording(false)
                setRecordingTime(0)
                setNeedsClarification(false)
              }}
              className="text-slate-600 hover:text-slate-900 font-medium py-2"
            >
              Submit another
            </button>
          </div>
        </motion.div>
      </div>
    )
  }
  return (
    <div className="max-w-3xl mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Voice Intake</h1>
        <p className="text-slate-500">
          Record rough feedback or ideas to be processed into actionable work.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Title */}
        <div>
          <label className="block text-sm font-bold text-slate-900 mb-1.5">
            Title
          </label>
          <input
            type="text"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Brief summary of the feedback..."
            className="w-full bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-400 placeholder:text-purple-400/50 font-medium"
          />
        </div>

        {/* Priority */}
        <div>
          <label className="block text-sm font-bold text-slate-900 mb-1.5">
            Priority
          </label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full md:w-64 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-green-400 cursor-pointer font-medium"
          >
            <option value="low">🟢 Low</option>
            <option value="medium">🟡 Medium</option>
            <option value="high">🟠 High</option>
            <option value="urgent">🔴 Urgent</option>
          </select>
        </div>

        {/* Audio Section */}
        <div className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-2xl p-6 shadow-sm">
          <label className="block text-sm font-bold text-blue-900 mb-4">
            Audio Recording
          </label>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Record Area */}
            <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-blue-300 rounded-xl bg-white/80 relative overflow-hidden min-h-[200px]">
              <AnimatePresence mode="wait">
                {!isRecording && !hasRecording && (
                  <motion.div
                    key="idle"
                    initial={{
                      opacity: 0,
                    }}
                    animate={{
                      opacity: 1,
                    }}
                    exit={{
                      opacity: 0,
                    }}
                    className="flex flex-col items-center"
                  >
                    <button
                      type="button"
                      onClick={handleStartRecording}
                      className="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center hover:bg-red-100 transition-colors mb-4 group"
                    >
                      <Mic className="w-8 h-8 group-hover:scale-110 transition-transform" />
                    </button>
                    <span className="text-sm font-medium text-slate-600">
                      Click to record
                    </span>
                  </motion.div>
                )}

                {isRecording && (
                  <motion.div
                    key="recording"
                    initial={{
                      opacity: 0,
                    }}
                    animate={{
                      opacity: 1,
                    }}
                    exit={{
                      opacity: 0,
                    }}
                    className="flex flex-col items-center w-full"
                  >
                    <div className="flex items-center gap-4 mb-6 w-full justify-center">
                      {/* Fake Waveform */}
                      <div className="flex items-center gap-1 h-8">
                        {[...Array(12)].map((_, i) => (
                          <motion.div
                            key={i}
                            className="w-1.5 bg-red-400 rounded-full"
                            animate={{
                              height: ['20%', '100%', '40%', '80%', '20%'],
                            }}
                            transition={{
                              repeat: Infinity,
                              duration: 1.5,
                              delay: i * 0.1,
                              ease: 'easeInOut',
                            }}
                          />
                        ))}
                      </div>
                    </div>

                    <div className="font-mono text-2xl text-slate-900 mb-6">
                      {formatTime(recordingTime)}
                    </div>

                    <button
                      type="button"
                      onClick={handleStopRecording}
                      className="w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center hover:bg-slate-800 transition-colors"
                    >
                      <Square className="w-4 h-4 fill-current" />
                    </button>
                  </motion.div>
                )}

                {hasRecording && (
                  <motion.div
                    key="recorded"
                    initial={{
                      opacity: 0,
                    }}
                    animate={{
                      opacity: 1,
                    }}
                    exit={{
                      opacity: 0,
                    }}
                    className="flex flex-col items-center w-full"
                  >
                    <div className="w-full bg-slate-50 rounded-lg p-4 flex items-center gap-4 mb-4 border border-slate-200">
                      <button
                        type="button"
                        className="w-10 h-10 bg-white border border-slate-200 rounded-full flex items-center justify-center text-slate-700 hover:bg-slate-50"
                      >
                        <Play className="w-4 h-4 ml-1" />
                      </button>
                      <div className="flex-1">
                        <div className="h-2 bg-slate-200 rounded-full w-full overflow-hidden">
                          <div className="h-full bg-slate-400 w-0" />
                        </div>
                      </div>
                      <span className="font-mono text-sm text-slate-500">
                        {formatTime(recordingTime)}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={handleDeleteRecording}
                      className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1.5 font-medium"
                    >
                      <Trash2 className="w-4 h-4" /> Discard
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Upload Area */}
            <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-blue-300 rounded-xl bg-white/80 hover:bg-white transition-colors cursor-pointer min-h-[200px]">
              <UploadCloud className="w-8 h-8 text-blue-400 mb-3" />
              <span className="text-sm font-bold text-blue-900 mb-1">
                Upload audio file
              </span>
              <span className="text-xs text-blue-600 font-medium">
                MP3, WAV, M4A up to 25MB
              </span>
            </div>
          </div>

          <div className="mt-4 flex items-start gap-2 text-xs text-blue-700 font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <p>
              Audio is stored locally under{' '}
              <code className="font-mono bg-blue-100 px-1.5 py-0.5 rounded text-blue-800">
                exports/voice-feedback/
              </code>{' '}
              and is never committed to git.
            </p>
          </div>
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-bold text-slate-900 mb-1.5">
            Notes / Transcript (Optional)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add any written context, links, or a manual transcript..."
            className="w-full bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 min-h-[120px] resize-y placeholder:text-purple-400/50 font-medium"
          />
        </div>

        {/* Clarification Flag */}
        <div className="flex items-start gap-3 p-5 bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-200 rounded-xl shadow-sm">
          <div className="flex items-center h-5 mt-0.5">
            <input
              id="clarification"
              type="checkbox"
              checked={needsClarification}
              onChange={(e) => setNeedsClarification(e.target.checked)}
              className="w-5 h-5 text-amber-600 border-2 border-amber-300 rounded focus:ring-amber-500"
            />
          </div>
          <div className="flex-1">
            <label
              htmlFor="clarification"
              className="text-sm font-bold text-amber-900 flex items-center gap-1.5 cursor-pointer"
            >
              Not Done / Needs Clarifications
              <HelpCircle
                className="w-4 h-4 text-amber-600"
                title="Check this if the feedback is ambiguous and needs human review before an agent can process it."
              />
            </label>
            <p className="text-xs text-amber-700 mt-1.5 font-medium">
              Flags this intake issue so it stays in the{' '}
              <code className="font-mono bg-amber-100 px-1.5 py-0.5 rounded text-amber-800">
                clarify
              </code>{' '}
              state instead of moving to the backlog.
            </p>
          </div>
        </div>

        {/* Submit */}
        <div className="pt-6 border-t-2 border-slate-100 flex justify-end">
          <button
            type="submit"
            disabled={isSubmitting || !title || (!hasRecording && !notes)}
            className="bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 text-white px-8 py-3 rounded-xl font-bold hover:from-purple-600 hover:via-pink-600 hover:to-orange-600 transition-all shadow-lg hover:shadow-xl transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Creating...
              </>
            ) : (
              'Create backlog intake issue'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

```
```pages/IssueDetail.tsx
import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { issues, categories, sprints, releases } from '../components/mockData'
import {
  ArrowLeft,
  CheckSquare,
  Square,
  Link as LinkIcon,
  MessageSquare,
  Activity,
  Bot,
  User,
  Lock,
  Github,
  ChevronDown,
  Calendar,
  Clock,
  Tag,
} from 'lucide-react'
export function IssueDetail() {
  const { id } = useParams()
  // In a real app we'd fetch by ID. Here we'll just find it or use the first one if ID is weird format from mock
  const issue =
    issues.find((i) => i.id === id || i.sequence === id) || issues[0]
  if (!issue) {
    return <div className="p-8 text-slate-500">Issue not found.</div>
  }
  const category = categories.find((c) => c.id === issue.categoryId)
  const sprint = sprints.find((s) => s.id === issue.sprintId)
  const release = releases.find((r) => r.id === issue.releaseId)
  const isClosed = issue.status === 'closed'
  return (
    <div className="h-full flex flex-col bg-white overflow-hidden">
      {/* Header */}
      <header className="px-6 py-4 border-b border-slate-200 flex-shrink-0 bg-white z-10">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-2 text-sm text-slate-500 mb-3">
            <Link
              to="/board"
              className="hover:text-slate-900 flex items-center gap-1 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Board
            </Link>
          </div>

          <div className="flex items-start justify-between">
            <div className="flex-1 mr-8">
              <div className="flex items-center gap-3 mb-2">
                <span className="font-mono text-lg text-slate-500">
                  #{issue.sequence}
                </span>
                <button
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border state-${issue.status.replace('-for-codex', '')} hover:opacity-80 transition-opacity`}
                >
                  <span className="capitalize">
                    {issue.status.replace(/-/g, ' ')}
                  </span>
                  <ChevronDown className="w-3 h-3" />
                </button>
                {sprint && (
                  <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-1 rounded border border-slate-200">
                    {sprint.name}
                  </span>
                )}
              </div>
              <h1 className="text-2xl font-semibold text-slate-900 leading-tight hover:bg-slate-50 p-1 -ml-1 rounded cursor-text transition-colors">
                {issue.title}
              </h1>
            </div>

            <div className="flex items-center gap-2">
              {isClosed && (
                <div className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-50 px-3 py-1.5 rounded-md border border-green-200">
                  <Lock className="w-3.5 h-3.5" />
                  Closed
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row gap-8 p-6">
          {/* Left Column (Main) */}
          <div className="flex-1 space-y-8">
            {/* Summary */}
            <section>
              <h3 className="text-sm font-semibold text-slate-900 mb-2">
                Summary
              </h3>
              <div className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-100">
                {issue.summary}
              </div>
            </section>

            {/* Proposed Approach */}
            {issue.proposedApproach && (
              <section>
                <h3 className="text-sm font-semibold text-slate-900 mb-2">
                  Proposed Approach
                </h3>
                <div className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg border border-slate-100 font-mono text-[13px]">
                  {issue.proposedApproach}
                </div>
              </section>
            )}

            {/* Acceptance Criteria */}
            <section>
              <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center justify-between">
                Acceptance Criteria
                <span className="text-xs font-normal text-slate-500">
                  {issue.acceptanceCriteria.filter((ac) => ac.done).length} /{' '}
                  {issue.acceptanceCriteria.length}
                </span>
              </h3>
              <div className="space-y-2">
                {issue.acceptanceCriteria.map((ac) => (
                  <div key={ac.id} className="flex items-start gap-3 group">
                    <button className="mt-0.5 text-slate-400 hover:text-slate-600 transition-colors">
                      {ac.done ? (
                        <CheckSquare className="w-4 h-4 text-blue-600" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                    <span
                      className={`text-sm ${ac.done ? 'text-slate-500 line-through' : 'text-slate-700'}`}
                    >
                      {ac.text}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            {/* Closeout Metadata */}
            {isClosed && issue.closeout && (
              <section className="bg-slate-50 border border-slate-200 rounded-lg p-5 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                  <Lock className="w-24 h-24" />
                </div>
                <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
                  <Lock className="w-4 h-4 text-slate-500" />
                  Closeout Record
                  <span className="text-xs font-normal text-slate-500 ml-auto bg-white px-2 py-0.5 rounded border border-slate-200">
                    Immutable
                  </span>
                </h3>
                <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                  <div>
                    <div className="text-slate-500 text-xs mb-1">
                      Originating LLM
                    </div>
                    <div className="font-mono text-slate-900">
                      {issue.closeout.originatingLlm}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500 text-xs mb-1">Closed By</div>
                    <div className="font-mono text-slate-900">
                      {issue.closeout.closedBy}
                    </div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-slate-500 text-xs mb-1">Closed At</div>
                    <div className="text-slate-900">
                      {new Date(issue.closeout.closedAt).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div>
                  <div className="text-slate-500 text-xs mb-1">Close Note</div>
                  <div className="text-slate-700 bg-white p-3 rounded border border-slate-200 italic">
                    "{issue.closeout.closeNote}"
                  </div>
                </div>
              </section>
            )}

            {/* Notes Timeline */}
            <section>
              <h3 className="text-sm font-semibold text-slate-900 mb-4 border-b border-slate-100 pb-2">
                Activity
              </h3>
              <div className="space-y-6 relative before:absolute before:inset-0 before:ml-[15px] before:-translate-x-px md:before:mx-0 md:before:translate-x-0 before:h-full before:w-0.5 before:bg-slate-100">
                {/* Mock Timeline Item 1 */}
                <div className="relative flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 shrink-0 z-10 bg-white">
                    <User className="w-4 h-4" />
                  </div>
                  <div className="flex-1 pt-1.5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-slate-900">
                        {issue.reporter}
                      </span>
                      <span className="text-xs text-slate-500">
                        created this issue
                      </span>
                      <span className="text-xs text-slate-400 ml-auto">
                        {new Date(issue.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Mock Timeline Item 2 */}
                <div className="relative flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0 z-10 bg-white">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="flex-1 pt-1.5">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sm font-medium font-mono text-blue-700">
                        codex-bot
                      </span>
                      <span className="text-xs text-slate-500">commented</span>
                      <span className="text-xs text-slate-400 ml-auto">
                        2 days ago
                      </span>
                    </div>
                    <div className="text-sm text-slate-700 bg-white border border-slate-200 p-3 rounded-lg shadow-sm">
                      I have analyzed the requirements and proposed an approach
                      using Alembic. Ready to implement when approved.
                    </div>
                  </div>
                </div>

                {/* Mock Timeline Item 3 */}
                <div className="relative flex items-start gap-4">
                  <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 shrink-0 z-10 bg-white">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div className="flex-1 pt-1.5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-slate-900">
                        human-admin
                      </span>
                      <span className="text-xs text-slate-500">
                        changed state to
                      </span>
                      <span className="text-xs font-medium bg-violet-50 text-violet-700 border border-violet-200 px-1.5 py-0.5 rounded">
                        Ready for Codex
                      </span>
                      <span className="text-xs text-slate-400 ml-auto">
                        1 day ago
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Add Comment */}
              <div className="mt-6 flex gap-4">
                <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 shrink-0">
                  <User className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <textarea
                    placeholder="Add a note or instruction for the agent..."
                    className="w-full bg-white border border-slate-200 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 min-h-[100px] resize-y"
                  />
                  <div className="mt-2 flex justify-end">
                    <button className="bg-slate-900 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-800 transition-colors">
                      Comment
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* Right Sidebar */}
          <div className="w-full md:w-72 flex-shrink-0 space-y-6">
            {/* Properties */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-4">
              <div>
                <div className="text-xs text-slate-500 mb-1">Assignee</div>
                <div className="flex items-center gap-2 text-sm">
                  {issue.assignee ? (
                    <>
                      <div className="w-5 h-5 rounded-full bg-white border border-slate-200 flex items-center justify-center text-slate-600">
                        {issue.assignee.isBot ? (
                          <Bot className="w-3 h-3" />
                        ) : (
                          <User className="w-3 h-3" />
                        )}
                      </div>
                      <span
                        className={
                          issue.assignee.isBot
                            ? 'font-mono text-blue-700'
                            : 'text-slate-900'
                        }
                      >
                        {issue.assignee.name}
                      </span>
                    </>
                  ) : (
                    <span className="text-slate-400 italic">Unassigned</span>
                  )}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-500 mb-1">Category</div>
                <div className="flex items-center gap-1.5 text-sm text-slate-900">
                  <Tag className="w-3.5 h-3.5 text-slate-400" />
                  {category?.name || 'None'}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-500 mb-1">Priority</div>
                <div className="text-sm text-slate-900 capitalize flex items-center gap-1.5">
                  <div
                    className={`w-2 h-2 rounded-full ${issue.priority === 'urgent' ? 'bg-red-500' : issue.priority === 'high' ? 'bg-orange-500' : issue.priority === 'medium' ? 'bg-yellow-500' : 'bg-slate-300'}`}
                  />
                  {issue.priority}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-500 mb-1">Sprint</div>
                <div className="text-sm text-slate-900">
                  {sprint ? (
                    sprint.name
                  ) : (
                    <span className="text-slate-400 italic">None</span>
                  )}
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-500 mb-1">Release</div>
                <div className="text-sm text-slate-900">
                  {release ? (
                    release.name
                  ) : (
                    <span className="text-slate-400 italic">None</span>
                  )}
                </div>
              </div>
            </div>

            {/* Dates */}
            <div className="text-xs text-slate-500 space-y-2 px-1">
              <div className="flex items-center justify-between">
                <span>Created</span>
                <span>{new Date(issue.createdAt).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Updated</span>
                <span>{new Date(issue.updatedAt).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Reporter</span>
                <span className="font-medium text-slate-700">
                  {issue.reporter}
                </span>
              </div>
            </div>

            {/* Linked References */}
            <div>
              <h4 className="text-xs font-semibold text-slate-900 mb-2 px-1 uppercase tracking-wider">
                Links
              </h4>
              <div className="space-y-1.5">
                <a
                  href="#"
                  className="flex items-center gap-2 text-sm text-slate-600 hover:text-blue-600 hover:bg-blue-50 p-1.5 rounded transition-colors group"
                >
                  <Github className="w-4 h-4 text-slate-400 group-hover:text-blue-600" />
                  <span className="truncate">PR #42: Add milestone column</span>
                </a>
                <a
                  href="#"
                  className="flex items-center gap-2 text-sm text-slate-600 hover:text-blue-600 hover:bg-blue-50 p-1.5 rounded transition-colors group"
                >
                  <LinkIcon className="w-4 h-4 text-slate-400 group-hover:text-blue-600" />
                  <span className="truncate">Figma: Release View</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

```
```components/IssueContext.tsx
import React, { useState, createContext, useContext } from 'react'
interface IssueContextType {
  selectedIssueId: string | null
  openIssue: (issueId: string) => void
  closeIssue: () => void
}
const IssueContext = createContext<IssueContextType | undefined>(undefined)
export function IssueProvider({ children }: { children: ReactNode }) {
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null)
  const openIssue = (issueId: string) => {
    setSelectedIssueId(issueId)
  }
  const closeIssue = () => {
    setSelectedIssueId(null)
  }
  return (
    <IssueContext.Provider
      value={{
        selectedIssueId,
        openIssue,
        closeIssue,
      }}
    >
      {children}
    </IssueContext.Provider>
  )
}
export function useIssue() {
  const context = useContext(IssueContext)
  if (!context) {
    throw new Error('useIssue must be used within IssueProvider')
  }
  return context
}

```
```components/IssueDrawer.tsx
import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useIssue } from './IssueContext'
import { issues, categories, sprints, releases } from './mockData'
import {
  X,
  CheckSquare,
  Square,
  Lock,
  Bot,
  User,
  ChevronDown,
  Tag,
  Calendar,
} from 'lucide-react'
export function IssueDrawer() {
  const { selectedIssueId, closeIssue } = useIssue()
  const issue = issues.find((i) => i.id === selectedIssueId)
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeIssue()
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [closeIssue])
  if (!issue) return null
  const category = categories.find((c) => c.id === issue.categoryId)
  const sprint = sprints.find((s) => s.id === issue.sprintId)
  const release = releases.find((r) => r.id === issue.releaseId)
  const isClosed = issue.status === 'closed'
  return (
    <AnimatePresence>
      {selectedIssueId && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{
              opacity: 0,
            }}
            animate={{
              opacity: 1,
            }}
            exit={{
              opacity: 0,
            }}
            onClick={closeIssue}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
          />

          {/* Drawer */}
          <motion.div
            initial={{
              x: '100%',
            }}
            animate={{
              x: 0,
            }}
            exit={{
              x: '100%',
            }}
            transition={{
              type: 'spring',
              damping: 30,
              stiffness: 300,
            }}
            className="fixed right-0 top-0 bottom-0 w-[600px] bg-white shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex-shrink-0 px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-purple-50 to-pink-50">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-lg text-purple-600 font-semibold">
                    #{issue.sequence}
                  </span>
                  <select
                    value={issue.status}
                    className={`px-3 py-1 rounded-full text-xs font-medium border state-${issue.status.replace('-for-codex', '')} cursor-pointer hover:opacity-80 transition-opacity`}
                  >
                    <option value="intake">Intake</option>
                    <option value="clarify">Clarify</option>
                    <option value="ready-for-codex">Ready for Codex</option>
                    <option value="implementing">Implementing</option>
                    <option value="verifying">Verifying</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>
                <button
                  onClick={closeIssue}
                  className="p-2 hover:bg-white/50 rounded-lg transition-colors text-slate-600 hover:text-slate-900"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <input
                type="text"
                defaultValue={issue.title}
                className="w-full text-xl font-semibold text-slate-900 bg-white/50 hover:bg-white border border-transparent hover:border-purple-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-400 transition-all"
              />
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Properties Grid */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl border border-blue-100">
                <div>
                  <label className="text-xs font-semibold text-blue-900 mb-1.5 block">
                    Priority
                  </label>
                  <select
                    value={issue.priority}
                    className="w-full bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-pointer"
                  >
                    <option value="low">🟢 Low</option>
                    <option value="medium">🟡 Medium</option>
                    <option value="high">🟠 High</option>
                    <option value="urgent">🔴 Urgent</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-blue-900 mb-1.5 block">
                    Category
                  </label>
                  <select
                    value={issue.categoryId}
                    className="w-full bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-pointer"
                  >
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-blue-900 mb-1.5 block">
                    Sprint
                  </label>
                  <select
                    value={issue.sprintId || ''}
                    className="w-full bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-pointer"
                  >
                    <option value="">None</option>
                    {sprints.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold text-blue-900 mb-1.5 block">
                    Release
                  </label>
                  <select
                    value={issue.releaseId || ''}
                    className="w-full bg-white border border-blue-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 cursor-pointer"
                  >
                    <option value="">None</option>
                    {releases.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Summary */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center gap-2">
                  <span className="w-1 h-4 bg-gradient-to-b from-purple-500 to-pink-500 rounded-full"></span>
                  Summary
                </h3>
                <textarea
                  defaultValue={issue.summary}
                  className="w-full bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 min-h-[100px] resize-y"
                />
              </div>

              {/* Proposed Approach */}
              {issue.proposedApproach && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 mb-2 flex items-center gap-2">
                    <span className="w-1 h-4 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-full"></span>
                    Proposed Approach
                  </h3>
                  <textarea
                    defaultValue={issue.proposedApproach}
                    className="w-full bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-200 rounded-lg p-4 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-400 min-h-[100px] resize-y"
                  />
                </div>
              )}

              {/* Acceptance Criteria */}
              <div>
                <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <span className="w-1 h-4 bg-gradient-to-b from-green-500 to-emerald-500 rounded-full"></span>
                    Acceptance Criteria
                  </span>
                  <span className="text-xs font-normal text-slate-500 bg-green-100 px-2 py-1 rounded-full">
                    {issue.acceptanceCriteria.filter((ac) => ac.done).length} /{' '}
                    {issue.acceptanceCriteria.length}
                  </span>
                </h3>
                <div className="space-y-2">
                  {issue.acceptanceCriteria.map((ac) => (
                    <div
                      key={ac.id}
                      className="flex items-start gap-3 p-3 bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg border border-green-100 hover:border-green-200 transition-colors"
                    >
                      <button className="mt-0.5 text-green-600 hover:text-green-700 transition-colors">
                        {ac.done ? (
                          <CheckSquare className="w-4 h-4" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                      <span
                        className={`text-sm flex-1 ${ac.done ? 'text-slate-500 line-through' : 'text-slate-700'}`}
                      >
                        {ac.text}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Closeout Metadata */}
              {isClosed && issue.closeout && (
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-5 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                    <Lock className="w-32 h-32" />
                  </div>
                  <h3 className="text-sm font-semibold text-green-900 mb-4 flex items-center gap-2">
                    <Lock className="w-4 h-4" />
                    Closeout Record
                    <span className="text-xs font-normal bg-white px-2 py-0.5 rounded-full border border-green-300 ml-auto">
                      Immutable
                    </span>
                  </h3>
                  <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                    <div>
                      <div className="text-green-700 text-xs mb-1 font-medium">
                        Originating LLM
                      </div>
                      <div className="font-mono text-green-900 bg-white px-2 py-1 rounded border border-green-200">
                        {issue.closeout.originatingLlm}
                      </div>
                    </div>
                    <div>
                      <div className="text-green-700 text-xs mb-1 font-medium">
                        Closed By
                      </div>
                      <div className="font-mono text-green-900 bg-white px-2 py-1 rounded border border-green-200">
                        {issue.closeout.closedBy}
                      </div>
                    </div>
                  </div>
                  <div>
                    <div className="text-green-700 text-xs mb-1 font-medium">
                      Close Note
                    </div>
                    <div className="text-green-900 bg-white p-3 rounded-lg border border-green-200 italic text-sm">
                      "{issue.closeout.closeNote}"
                    </div>
                  </div>
                </div>
              )}

              {/* Comment Section */}
              <div className="pt-4 border-t-2 border-dashed border-slate-200">
                <textarea
                  placeholder="Add a note or instruction for the agent..."
                  className="w-full bg-gradient-to-br from-amber-50 to-orange-50 border-2 border-amber-200 rounded-xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 min-h-[100px] resize-y placeholder:text-amber-600/50"
                />
                <div className="mt-3 flex justify-end">
                  <button className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:from-amber-600 hover:to-orange-600 transition-all shadow-lg hover:shadow-xl transform hover:scale-105">
                    💬 Comment
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

```
```components/CreateIssueModal.tsx
import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Sparkles } from 'lucide-react'
import { categories, sprints } from './mockData'
interface CreateIssueModalProps {
  isOpen: boolean
  onClose: () => void
}
export function CreateIssueModal({ isOpen, onClose }: CreateIssueModalProps) {
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [priority, setPriority] = useState('medium')
  const [categoryId, setCategoryId] = useState(categories[0].id)
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Mock creation
    console.log('Creating issue:', {
      title,
      summary,
      priority,
      categoryId,
    })
    onClose()
    setTitle('')
    setSummary('')
  }
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{
              opacity: 0,
            }}
            animate={{
              opacity: 1,
            }}
            exit={{
              opacity: 0,
            }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
          />

          <motion.div
            initial={{
              opacity: 0,
              scale: 0.95,
              y: 20,
            }}
            animate={{
              opacity: 1,
              scale: 1,
              y: 0,
            }}
            exit={{
              opacity: 0,
              scale: 0.95,
              y: 20,
            }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl bg-white rounded-2xl shadow-2xl z-50 overflow-hidden"
          >
            <div className="bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Create New Issue
              </h2>
              <button
                onClick={onClose}
                className="text-white/80 hover:text-white p-2 hover:bg-white/20 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="What needs to be done?"
                  className="w-full bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-purple-400 placeholder:text-purple-400/50"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-2">
                  Summary
                </label>
                <textarea
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  placeholder="Describe the issue in detail..."
                  className="w-full bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-400 min-h-[120px] resize-y placeholder:text-blue-400/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">
                    Priority
                  </label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-green-400 cursor-pointer"
                  >
                    <option value="low">🟢 Low</option>
                    <option value="medium">🟡 Medium</option>
                    <option value="high">🟠 High</option>
                    <option value="urgent">🔴 Urgent</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">
                    Category
                  </label>
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    className="w-full bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-200 rounded-xl px-4 py-3 text-slate-900 focus:outline-none focus:ring-2 focus:ring-amber-400 cursor-pointer"
                  >
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-4 py-3 border-2 border-slate-200 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-3 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 text-white rounded-xl font-semibold hover:from-purple-600 hover:via-pink-600 hover:to-orange-600 transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  ✨ Create Issue
                </button>
              </div>
            </form>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

```