/**
 * Zoom Intelligence - Meetings List Page
 * Renders the meetings table and handles join meeting form.
 */

(() => {
  let refreshInterval = null;

  function init() {
    loadMeetings();
    setupJoinForm();
    setupDemoToggle();
    startAutoRefresh();
  }

  async function loadMeetings() {
    const tableBody = document.getElementById('meetings-body');
    const emptyState = document.getElementById('empty-state');
    const tableEl = document.getElementById('meetings-table');

    try {
      const data = await API.listMeetings();
      const meetings = data.meetings || [];

      if (meetings.length === 0) {
        tableEl.style.display = 'none';
        emptyState.style.display = 'block';
        return;
      }

      tableEl.style.display = 'table';
      emptyState.style.display = 'none';

      // Sort: active first, then by start time descending
      meetings.sort((a, b) => {
        if (a.status === 'active' && b.status !== 'active') return -1;
        if (b.status === 'active' && a.status !== 'active') return 1;
        return new Date(b.started_at) - new Date(a.started_at);
      });

      tableBody.innerHTML = meetings.map(m => renderMeetingRow(m)).join('');
    } catch (err) {
      showToast('Failed to load meetings: ' + err.message, true);
    }
  }

  function renderMeetingRow(meeting) {
    const startDate = meeting.started_at ? formatDate(meeting.started_at) : '--';
    const duration = calculateDuration(meeting.started_at, meeting.ended_at);
    const participantCount = meeting.participants ? meeting.participants.length : 0;
    const badgeClass = getBadgeClass(meeting.status);
    const title = getMeetingTitle(meeting);

    return `
      <tr onclick="window.location.href='meeting.html?id=${meeting.id}'">
        <td>
          <div class="meeting-title">${title}</div>
          <div class="meeting-platform">${meeting.platform.replace('_', ' ')}</div>
        </td>
        <td class="meeting-meta">${startDate}</td>
        <td class="meeting-meta">${duration}</td>
        <td><span class="badge badge-${badgeClass}"><span class="badge-dot"></span>${meeting.status}</span></td>
        <td class="meeting-meta">${participantCount} participant${participantCount !== 1 ? 's' : ''}</td>
        <td class="meeting-meta">${meeting.action_items_count || 0} actions</td>
      </tr>
    `;
  }

  function getMeetingTitle(meeting) {
    // Try to derive title from URL
    if (meeting.meeting_url) {
      if (meeting.meeting_url.includes('zoom')) return 'Zoom Meeting';
      if (meeting.meeting_url.includes('meet.google')) return 'Google Meet';
      if (meeting.meeting_url.includes('teams')) return 'Teams Meeting';
    }
    return 'Meeting ' + meeting.id.slice(0, 8);
  }

  function getBadgeClass(status) {
    switch (status) {
      case 'active': return 'active';
      case 'completed': return 'completed';
      case 'processing': return 'processing';
      case 'joining': return 'processing';
      case 'failed': return 'failed';
      default: return 'completed';
    }
  }

  function formatDate(isoStr) {
    const d = new Date(isoStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function calculateDuration(start, end) {
    if (!start) return '--';
    const s = new Date(start);
    const e = end ? new Date(end) : new Date();
    const diffMins = Math.round((e - s) / 60000);

    if (diffMins < 1) return '<1 min';
    if (diffMins < 60) return `${diffMins} min`;
    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return `${hours}h ${mins}m`;
  }

  function setupJoinForm() {
    const form = document.getElementById('join-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('meeting-url-input');
      const url = input.value.trim();

      if (!url) {
        showToast('Please enter a meeting URL', true);
        return;
      }

      const btn = form.querySelector('button');
      btn.disabled = true;
      btn.textContent = 'Joining...';

      try {
        const result = await API.joinMeeting(url);
        showToast('Bot is joining the meeting');
        input.value = '';
        // Refresh list after short delay
        setTimeout(loadMeetings, 1000);
      } catch (err) {
        showToast('Failed to join: ' + err.message, true);
      } finally {
        btn.disabled = false;
        btn.textContent = 'Join Meeting';
      }
    });
  }

  function setupDemoToggle() {
    const badge = document.querySelector('.demo-badge');
    if (badge) {
      badge.addEventListener('click', () => {
        const isDemo = API.toggleDemoMode();
        showToast(isDemo ? 'Demo mode ON' : 'Demo mode OFF (connecting to backend)');
        loadMeetings();
      });
    }
  }

  function startAutoRefresh() {
    // Poll every 5 seconds for active meetings
    refreshInterval = setInterval(loadMeetings, 5000);
  }

  function showToast(message, isError = false) {
    let toast = document.querySelector('.toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'toast';
      document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.toggle('error', isError);
    toast.classList.add('visible');

    setTimeout(() => toast.classList.remove('visible'), 3000);
  }

  // Expose for global use
  window.showToast = showToast;

  // Init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
