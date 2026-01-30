/**
 * Main layout component with navigation
 */
import React, { useState } from 'react';
import { Link } from '@tanstack/react-router';
import {
  HomeIcon,
  CubeIcon,
  CurrencyDollarIcon,
  ShieldCheckIcon,
  ClipboardDocumentCheckIcon,
  SparklesIcon,
  Bars3Icon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

interface LayoutProps {
  children: React.ReactNode;
}

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Projects', href: '/projects', icon: CubeIcon },
  { name: 'Costs', href: '/costs', icon: CurrencyDollarIcon },
  { name: 'Compliance', href: '/compliance', icon: ShieldCheckIcon },
  { name: 'Workflows', href: '/workflows', icon: ClipboardDocumentCheckIcon },
  { name: 'AI Assistant', href: '/ai', icon: SparklesIcon },
];

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? '' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-900/80" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-white">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center space-x-2">
              <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">LZ</span>
              </div>
              <span className="text-xl font-bold text-gray-900">Portal</span>
            </div>
            <button onClick={() => setSidebarOpen(false)}>
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className="group flex items-center px-2 py-2 text-base font-medium rounded-md text-gray-700 hover:bg-indigo-50 hover:text-indigo-600"
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className="mr-4 h-6 w-6" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow border-r border-gray-200 bg-white overflow-y-auto">
          <div className="flex h-16 items-center px-4 border-b border-gray-200">
            <div className="flex items-center space-x-2">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shadow-lg">
                <span className="text-white font-bold text-lg">LZ</span>
              </div>
              <div>
                <div className="text-xl font-bold text-gray-900">Landing Zone</div>
                <div className="text-xs text-gray-500">Control Plane</div>
              </div>
            </div>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className="group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-gray-700 hover:bg-indigo-50 hover:text-indigo-600 transition-colors"
                activeProps={{
                  className: 'bg-indigo-50 text-indigo-600',
                }}
              >
                <item.icon className="mr-3 h-5 w-5 flex-shrink-0" />
                {item.name}
              </Link>
            ))}
          </nav>
          <div className="flex-shrink-0 border-t border-gray-200 p-4">
            <div className="flex items-center">
              <div className="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                <span className="text-sm font-medium text-gray-600">JD</span>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-700">John Doe</p>
                <p className="text-xs text-gray-500">admin@example.com</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-40 flex h-16 flex-shrink-0 bg-white border-b border-gray-200 lg:hidden">
          <button
            type="button"
            className="px-4 text-gray-500"
            onClick={() => setSidebarOpen(true)}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          <div className="flex flex-1 justify-between px-4">
            <div className="flex items-center">
              <span className="text-lg font-bold">Landing Zone Portal</span>
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
}
