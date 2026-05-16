/**
 * Zoom Intelligence - API Client
 * Handles all communication with the backend API.
 * Includes demo mode with mock data when backend is unavailable.
 */

const API = (() => {
  const BASE_URL = '/api/v1';
  let demoMode = false;

  // Demo/mock data
  const MOCK_MEETINGS = [
    {
      id: 'demo-001',
      status: 'active',
      platform: 'zoom',
      meeting_url: 'https://zoom.us/j/123456789',
      participants: ['Jordannah Korus', 'Todd Chen', 'Sarah Miller'],
      transcript_segments: 47,
      action_items_count: 3,
      started_at: new Date(Date.now() - 25 * 60000).toISOString(),
      ended_at: null,
    },
    {
      id: 'demo-002',
      status: 'completed',
      platform: 'google_meet',
      meeting_url: 'https://meet.google.com/abc-defg-hij',
      participants: ['Jordannah Korus', 'Ronen Korus', 'Alex K.'],
      transcript_segments: 156,
      action_items_count: 7,
      started_at: new Date(Date.now() - 3600000).toISOString(),
      ended_at: new Date(Date.now() - 1800000).toISOString(),
    },
    {
      id: 'demo-003',
      status: 'completed',
      platform: 'teams',
      meeting_url: 'https://teams.microsoft.com/l/meetup-join/abc',
      participants: ['Jordannah Korus', 'Paul H.'],
      transcript_segments: 89,
      action_items_count: 4,
      started_at: new Date(Date.now() - 86400000).toISOString(),
      ended_at: new Date(Date.now() - 82800000).toISOString(),
    },
  ];

  const MOCK_MEETING_DETAIL = {
    id: 'demo-002',
    status: 'completed',
    platform: 'google_meet',
    meeting_url: 'https://meet.google.com/abc-defg-hij',
    bot_display_name: 'Pyonair AI',
    bot_id: 'bot-demo-002',
    participants: ['Jordannah Korus', 'Ronen Korus', 'Alex K.'],
    transcript_segments: 156,
    action_items: [
      { task: 'Prepare Celestica proposal deck by Tuesday', assignee: 'Jordannah Korus', due_date: '2026-05-20', status: 'pending' },
      { task: 'Set up demo environment for sales presentation', assignee: 'Ronen Korus', due_date: '2026-05-19', status: 'pending' },
      { task: 'Send pricing sheet to enterprise prospects', assignee: 'Alex K.', due_date: '2026-05-18', status: 'pending' },
      { task: 'Review competitor analysis document', assignee: 'Jordannah Korus', due_date: '2026-05-21', status: 'pending' },
      { task: 'Schedule follow-up with Todd', assignee: 'Ronen Korus', due_date: '2026-05-17', status: 'completed' },
      { task: 'Update CRM pipeline status', assignee: 'Alex K.', due_date: '2026-05-17', status: 'completed' },
      { task: 'Draft partnership agreement template', assignee: 'Jordannah Korus', due_date: '2026-05-22', status: 'pending' },
    ],
    decisions: [
      { decision: 'Focus enterprise sales on AI-powered proposal acceleration', context: 'Weeks-to-minutes value prop resonates best with C-suite' },
      { decision: 'Price enterprise tier at $999/month with annual discount', context: 'Competitive with market, justified by time savings' },
      { decision: 'Launch reseller program with 10% commission', context: 'Alex to manage partner channel' },
    ],
    insights: [
      { type: 'opportunity', content: 'Todd mentioned Celestica evaluating three vendors - we have first-mover advantage' },
      { type: 'risk', content: 'Timeline pressure - decision expected within 2 weeks' },
      { type: 'sentiment', content: 'Ronen confident about pipeline, Alex concerned about capacity' },
    ],
    chat_messages_sent: [],
    started_at: new Date(Date.now() - 3600000).toISOString(),
    ended_at: new Date(Date.now() - 1800000).toISOString(),
    summary: 'Sales strategy alignment meeting covering enterprise pipeline, Celestica opportunity, and reseller program launch. Key outcomes: agreed on pricing, assigned demo prep tasks, and established two-week timeline for Celestica decision.',
  };

  const MOCK_TRANSCRIPT = {
    meeting_id: 'demo-002',
    segment_count: 12,
    participants: ['Jordannah Korus', 'Ronen Korus', 'Alex K.'],
    segments: [
      { speaker: 'Jordannah Korus', text: "Alright team, let's get started. We have a lot to cover today around our enterprise pipeline.", timestamp: 0, timestamp_display: '0:00' },
      { speaker: 'Ronen Korus', text: "I have some great updates on the Celestica front. Todd is very interested in our proposal acceleration tool.", timestamp: 15, timestamp_display: '0:15' },
      { speaker: 'Jordannah Korus', text: "That's excellent. What's the timeline looking like?", timestamp: 28, timestamp_display: '0:28' },
      { speaker: 'Ronen Korus', text: "They're evaluating vendors now. We have about two weeks before they make a decision. I think we're in a strong position.", timestamp: 35, timestamp_display: '0:35' },
      { speaker: 'Alex K.', text: "On the reseller side, I've had three partners express interest this week. The 10% commission structure seems to be attractive.", timestamp: 52, timestamp_display: '0:52' },
      { speaker: 'Jordannah Korus', text: "Great progress Alex. Let's make sure the partner onboarding is smooth. What do they need from us?", timestamp: 68, timestamp_display: '1:08' },
      { speaker: 'Alex K.', text: "Mainly a demo environment and sales collateral. I can put together a partner kit if that works.", timestamp: 80, timestamp_display: '1:20' },
      { speaker: 'Jordannah Korus', text: "Perfect. Ronen, for Celestica - what do we need to have ready for the demo?", timestamp: 95, timestamp_display: '1:35' },
      { speaker: 'Ronen Korus', text: "The proposal acceleration workflow needs to be polished. I'd also love to show the meeting intelligence feature - this tool recording us right now is a great example.", timestamp: 108, timestamp_display: '1:48' },
      { speaker: 'Jordannah Korus', text: "Love it. Let's make sure we have both running smoothly by Tuesday. I'll handle the deck, Ronen you own the demo environment.", timestamp: 125, timestamp_display: '2:05' },
      { speaker: 'Ronen Korus', text: "On it. I'll have it ready by Monday evening so we can do a dry run.", timestamp: 140, timestamp_display: '2:20' },
      { speaker: 'Alex K.', text: "Should I update the pricing sheet for enterprise? We discussed $999 per month last time but wanted to confirm.", timestamp: 155, timestamp_display: '2:35' },
    ],
  };

  async function request(method, path, body = null) {
    if (demoMode) {
      return handleDemoRequest(method, path, body);
    }

    try {
      const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
      };
      if (body) opts.body = JSON.stringify(body);

      const res = await fetch(`${BASE_URL}${path}`, opts);

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      return await res.json();
    } catch (err) {
      // If backend unavailable, switch to demo mode
      if (err.message === 'Failed to fetch' || err.name === 'TypeError') {
        console.warn('Backend unavailable, switching to demo mode');
        demoMode = true;
        updateDemoBadge();
        return handleDemoRequest(method, path, body);
      }
      throw err;
    }
  }

  function handleDemoRequest(method, path, body) {
    // Simulate network delay
    return new Promise((resolve) => {
      setTimeout(() => {
        if (path === '/meetings' && method === 'GET') {
          resolve({ count: MOCK_MEETINGS.length, meetings: MOCK_MEETINGS });
        } else if (path.match(/^\/meetings\/[\w-]+$/) && method === 'GET') {
          resolve(MOCK_MEETING_DETAIL);
        } else if (path.match(/^\/meetings\/[\w-]+\/transcript$/) && method === 'GET') {
          resolve(MOCK_TRANSCRIPT);
        } else if (path === '/meetings/join' && method === 'POST') {
          resolve({ meeting_id: 'demo-new-' + Date.now(), status: 'joining', message: 'Demo: Bot would join meeting' });
        } else if (path.match(/\/end$/) && method === 'POST') {
          resolve({ meeting_id: 'demo-001', status: 'completed', title: 'Demo Meeting' });
        } else {
          resolve({});
        }
      }, 300);
    });
  }

  function updateDemoBadge() {
    const badge = document.querySelector('.demo-badge');
    if (badge) badge.classList.toggle('visible', demoMode);
  }

  // Public API
  return {
    get isDemoMode() { return demoMode; },
    setDemoMode(val) {
      demoMode = val;
      updateDemoBadge();
    },
    toggleDemoMode() {
      demoMode = !demoMode;
      updateDemoBadge();
      return demoMode;
    },

    listMeetings() {
      return request('GET', '/meetings');
    },

    getMeeting(id) {
      return request('GET', `/meetings/${id}`);
    },

    getTranscript(id) {
      return request('GET', `/meetings/${id}/transcript`);
    },

    joinMeeting(meetingUrl) {
      return request('POST', '/meetings/join', { meeting_url: meetingUrl });
    },

    endMeeting(id) {
      return request('POST', `/meetings/${id}/end`);
    },
  };
})();
