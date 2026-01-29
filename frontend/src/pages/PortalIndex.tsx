import React from 'react';
import { Link } from '@tanstack/react-router';

export default function PortalIndex() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">Portal</h1>
      <p className="mt-2 text-sm text-gray-600">Landing Zone Portal — entry page and links.</p>

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link to="/portal/lz" className="block p-4 border rounded hover:shadow">Landing Zone (lz)</Link>
        <Link to="/portal/git" className="block p-4 border rounded hover:shadow">Git Integrations</Link>
        <Link to="/portal/monitoring" className="block p-4 border rounded hover:shadow">Monitoring & Observability</Link>
      </div>
    </div>
  );
}
