/**
 * Zoom Intelligence - Meeting Detail Page
 * Renders meeting summary, action items, decisions, insights, and transcript.
 */

(() => {
  let meetingId = null;
  let refreshInterval = null;
  const speakerColorMap = {};
  let speakerIndex = 0;

  function init() {
    const params = new URLSearchParams(window.location.search);
    meetingId = params.get('id');

    if (!meetingId) {
      window.location.href = 'index.html';
      return;
    }

    loadMeeting();
    loadTranscript();
  }

  async function loadMeeting() {
    const loadingEl = document.getElementById('loading');
    const contentEl = document.getElementById('meeting-content');

    try {
      const meeting = await API.getMeeting(meetingId);
      loadingEl.style.display = 'none';
      contentEl.style.display = 'block';

      renderHeader(meeting);
      renderSummary(meeting);
      renderActionItems(meeting.action_items || []);
      renderDecisions(meeting.decisions || []);
      renderInsights(meeting.insights || []);

      // Auto-refresh if active
      if (meeting.status === 'active') {
        startAutoRefresh();
        showEndButton();
      }
    } catch (err) {
      loadingEl.innerHTML = `<p style="color: var(--danger);">Failed to load meeting: ${err.message}</p>`;
    }
  }

  async function loadTranscript() {
    try {
      const data = await API.getTranscript(meetingId);
      renderTranscript(data);
    } catch (err) {
      console.error('Failed to load transcript:', err);
    }
  }

  function renderHeader(meeting) {
    const title = meeting.summary
      ? meeting.summary.split('.')[0]
      : getMeetingTitle(meeting);

    document.getElementById('meeting-title').textContent = title;

    const badgeClass = getBadgeClass(meeting.status);
    document.getElementById('meeting-status').innerHTML =
      `<span class="badge badge-${badgeClass}"><span class="badge-dot"></span>${meeting.status}</span>`;

    const metaRow = document.getElementById('meeting-meta');
    const parts = [];

    if (meeting.platform) {
      parts.push(`<span>${meeting.platform.replace('_', ' ')}</span>`);
    }
    if (meeting.started_at) {
      const d = new Date(meeting.started_at);
      parts.push(`<span>${d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} at ${d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>`);
    }
    if (meeting.participants && meeting.participants.length > 0) {
      parts.push(`<span>${meeting.participants.length} participants: ${meeting.participants.join(', ')}</span>`);
    }
    if (meeting.started_at) {
      const duration = calculateDuration(meeting.started_at, meeting.ended_at);
      parts.push(`<span>Duration: ${duration}</span>`);
    }

    metaRow.innerHTML = parts.join('');
  }

  function renderSummary(meeting) {
    const el = document.getElementById('summary-section');
    if (meeting.summary) {
      el.style.display = 'block';
      el.querySelector('p').textContent = meeting.summary;
    } else {
      el.style.display = 'none';
    }
  }

  function renderActionItems(items) {
    const container = document.getElementById('action-items-list');
    const count = document.getElementById('action-items-count');
    count.textContent = items.length;

    if (items.length === 0) {
      container.innerHTML = '<p class="meeting-meta" style="padding: 16px 0;">No action items yet</p>';
      return;
    }

    container.innerHTML = items.map(item => `
      <div class="action-item">
        <div class="action-item-text">${item.task || item.text || item.content || ''}</div>
        <div class="action-item-meta">
          ${item.assignee ? `<span class="action-item-assignee">${item.assignee}</span>` : ''}
          ${item.due_date ? `<span>Due: ${item.due_date}</span>` : ''}
          ${item.status ? `<span>${item.status}</span>` : ''}
        </div>
      </div>
    `).join('');
  }

  function renderDecisions(decisions) {
    const container = document.getElementById('decisions-list');
    const count = document.getElementById('decisions-count');
    count.textContent = decisions.length;

    if (decisions.length === 0) {
      container.innerHTML = '<p class="meeting-meta" style="padding: 16px 0;">No decisions recorded yet</p>';
      return;
    }

    container.innerHTML = decisions.map(d => `
      <div class="decision-item">
        <div class="decision-item-text">${d.decision || d.text || ''}</div>
        ${d.context ? `<div class="decision-item-context">${d.context}</div>` : ''}
      </div>
    `).join('');
  }

  function renderInsights(insights) {
    const container = document.getElementById('insights-list');
    const count = document.getElementById('insights-count');
    count.textContent = insights.length;

    if (insights.length === 0) {
      container.innerHTML = '<p class="meeting-meta" style="padding: 16px 0;">No insights yet</p>';
      return;
    }

    container.innerHTML = insights.map(i => `
      <div class="insight-item">
        ${i.type ? `<div class="insight-type">${i.type}</div>` : ''}
        <div>${i.content || i.text || ''}</div>
      </div>
    `).join('');
  }

  function renderTranscript(data) {
    const container = document.getElementById('transcript-content');
    const segments = data.segments || [];

    if (segments.length === 0) {
      container.innerHTML = '<p class="meeting-meta">No transcript available</p>';
      return;
    }

    container.innerHTML = segments.map(seg => {
      const colorClass = getSpeakerColor(seg.speaker);
      return `
        <div class="transcript-segment">
          <span class="transcript-time">${seg.timestamp_display || formatTimestamp(seg.timestamp)}</span>
          <span class="transcript-speaker ${colorClass}">${seg.speaker}</span>
          <span class="transcript-text">${seg.text}</span>
        </div>
      `;
    }).join('');
  }

  function getSpeakerColor(speaker) {
    if (!speakerColorMap[speaker]) {
      speakerColorMap[speaker] = `speaker-${speakerIndex % 6}`;
      speakerIndex++;
    }
    return speakerColorMap[speaker];
  }

  function formatTimestamp(seconds) {
    if (seconds == null) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function getMeetingTitle(meeting) {
    if (meeting.meeting_url) {
      if (meeting.meeting_url.includes('zoom')) return 'Zoom Meeting';
      if (meeting.meeting_url.includes('meet.google')) return 'Google Meet';
      if (meeting.meeting_url.includes('teams')) return 'Teams Meeting';
    }
    return 'Meeting ' + (meeting.id || '').slice(0, 8);
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

  function showEndButton() {
    const btn = document.getElementById('end-meeting-btn');
    if (btn) {
      btn.style.display = 'inline-flex';
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.textContent = 'Ending...';
        try {
          await API.endMeeting(meetingId);
          window.showToast && window.showToast('Meeting ended, generating summary...');
          stopAutoRefresh();
          setTimeout(() => {
            loadMeeting();
            loadTranscript();
          }, 2000);
        } catch (err) {
          window.showToast && window.showToast('Failed to end meeting: ' + err.message, true);
          btn.disabled = false;
          btn.textContent = 'End Meeting';
        }
      });
    }
  }

  function startAutoRefresh() {
    refreshInterval = setInterval(() => {
      loadMeeting();
      loadTranscript();
    }, 5000);
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  }

  // Init
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
