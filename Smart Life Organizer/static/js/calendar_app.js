// calendar_app.js — FullCalendar initialization & event handlers
document.addEventListener('DOMContentLoaded', function () {
  const calEl = document.getElementById('fullcalendar');
  if (!calEl) return;
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  const categoriesData = JSON.parse(document.getElementById('categories-json').textContent);

  // ── FullCalendar ──
  const calendar = new FullCalendar.Calendar(calEl, {
    initialView: 'dayGridMonth',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,timeGridDay'
    },
    buttonText: { today: 'Today', month: 'Month', week: 'Week', day: 'Day' },
    height: 'auto',
    nowIndicator: true,
    selectable: true,
    editable: true,
    eventResizableFromStart: false,
    slotMinTime: '06:00:00',
    slotMaxTime: '23:00:00',
    allDaySlot: false,
    events: { url: '/api/events/feed/', failure: function () { alert('Error loading events'); } },

    // Click empty slot → quick add
    dateClick: function (info) {
      openQuickAdd(info.dateStr, null);
    },
    select: function (info) {
      openQuickAdd(info.startStr, info.endStr);
      calendar.unselect();
    },

    // Click event → popover
    eventClick: function (info) {
      info.jsEvent.preventDefault();
      showEventPopover(info.event, info.el);
    },

    // Drag & drop
    eventDrop: function (info) {
      updateEventTime(info.event, info.revert);
    },
    eventResize: function (info) {
      updateEventTime(info.event, info.revert);
    },

    eventDidMount: function (info) {
      if (info.event.extendedProps.isCompleted) {
        info.el.style.opacity = '0.55';
        info.el.style.textDecoration = 'line-through';
      }
    }
  });
  calendar.render();
  window._fc = calendar;

  // ── Quick Add Modal ──
  function openQuickAdd(startStr, endStr) {
    const m = document.getElementById('quick-add-modal');
    const sInput = document.getElementById('qa-start');
    const eInput = document.getElementById('qa-end');
    // Format for datetime-local
    if (startStr) sInput.value = startStr.substring(0, 16);
    if (endStr) {
      eInput.value = endStr.substring(0, 16);
    } else if (startStr) {
      const d = new Date(startStr);
      d.setHours(d.getHours() + 1);
      eInput.value = d.toISOString().substring(0, 16);
    }
    document.getElementById('qa-title').value = '';
    document.getElementById('qa-category').value = '';
    document.getElementById('qa-error').classList.add('hidden');
    // Reset color picker
    document.getElementById('qa-color').value = '';
    document.querySelectorAll('#qa-color-picker .color-circle').forEach(c => c.classList.remove('selected'));
    // Reset category preview
    document.getElementById('qa-cat-preview').classList.add('hidden');
    m.classList.remove('hidden');
    setTimeout(() => document.getElementById('qa-title').focus(), 80);
  }
  window.openQuickAdd = openQuickAdd;

  document.getElementById('qa-cancel').onclick = () => document.getElementById('quick-add-modal').classList.add('hidden');
  document.getElementById('qa-backdrop').onclick = () => document.getElementById('quick-add-modal').classList.add('hidden');

  // ── Color circle click handlers ──
  document.querySelectorAll('#qa-color-picker .color-circle').forEach(circle => {
    circle.addEventListener('click', function () {
      document.querySelectorAll('#qa-color-picker .color-circle').forEach(c => c.classList.remove('selected'));
      this.classList.add('selected');
      document.getElementById('qa-color').value = this.getAttribute('data-color');
    });
  });

  // ── Category dropdown → color preview dot ──
  document.getElementById('qa-category').addEventListener('change', function () {
    const sel = this.options[this.selectedIndex];
    const preview = document.getElementById('qa-cat-preview');
    const dot = document.getElementById('qa-cat-dot');
    const label = document.getElementById('qa-cat-label');
    if (this.value && sel.dataset.color) {
      dot.style.background = sel.dataset.color;
      label.textContent = this.value;
      preview.classList.remove('hidden');
    } else {
      preview.classList.add('hidden');
    }
  });

  document.getElementById('qa-submit').onclick = function () {
    const title = document.getElementById('qa-title').value.trim();
    const start = document.getElementById('qa-start').value;
    const end = document.getElementById('qa-end').value;
    const category = document.getElementById('qa-category').value;
    const selectedColor = document.getElementById('qa-color').value || null;
    const errBox = document.getElementById('qa-error');
    errBox.classList.add('hidden');
    if (!title || !start || !end || !category) { errBox.textContent = 'All fields are required.'; errBox.classList.remove('hidden'); return; }
    if (new Date(end) <= new Date(start)) { errBox.textContent = 'End must be after start.'; errBox.classList.remove('hidden'); return; }
    this.disabled = true; this.textContent = 'Saving…';
    fetch('/api/events/create/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, start_time: start, end_time: end, category, category_color: selectedColor, description: '' })
    }).then(r => r.json()).then(data => {
      if (data.success) { document.getElementById('quick-add-modal').classList.add('hidden'); calendar.refetchEvents(); }
      else { errBox.textContent = data.error; errBox.classList.remove('hidden'); }
    }).catch(() => { errBox.textContent = 'Network error.'; errBox.classList.remove('hidden'); })
      .finally(() => { this.disabled = false; this.textContent = 'Save'; });
  };

  // ── Full Event Modal (advanced) ──
  document.getElementById('btn-open-event-modal').onclick = function () {
    document.getElementById('event-modal').classList.remove('hidden');
    resetFullModal();
  };
  document.getElementById('qa-more-options').onclick = function () {
    document.getElementById('quick-add-modal').classList.add('hidden');
    const s = document.getElementById('qa-start').value;
    const e = document.getElementById('qa-end').value;
    document.getElementById('event-modal').classList.remove('hidden');
    resetFullModal();
    if (s) document.getElementById('event-start').value = s;
    if (e) document.getElementById('event-end').value = e;
  };

  function resetFullModal() {
    document.getElementById('create-event-form').reset();
    document.getElementById('new-category-row').classList.add('hidden');
    document.getElementById('repeat-options').classList.add('hidden');
    document.getElementById('form-error').classList.add('hidden');
  }
  document.getElementById('btn-close-event-modal').onclick = () => document.getElementById('event-modal').classList.add('hidden');
  document.getElementById('full-modal-backdrop').onclick = () => document.getElementById('event-modal').classList.add('hidden');
  document.getElementById('full-modal-cancel').onclick = () => document.getElementById('event-modal').classList.add('hidden');

  // Category new toggle
  document.getElementById('btn-show-new-category').onclick = function () {
    document.getElementById('event-category').value = '__new__';
    document.getElementById('new-category-row').classList.remove('hidden');
    setTimeout(() => document.getElementById('new-category-name').focus(), 50);
  };
  document.getElementById('event-category').onchange = function () {
    if (this.value === '__new__') document.getElementById('new-category-row').classList.remove('hidden');
    else document.getElementById('new-category-row').classList.add('hidden');
  };
  document.getElementById('event-repeat-weekly').onchange = function () {
    if (this.checked) document.getElementById('repeat-options').classList.remove('hidden');
    else document.getElementById('repeat-options').classList.add('hidden');
  };

  // Full modal submit
  document.getElementById('btn-submit-event').onclick = function (e) {
    e && e.preventDefault();
    const title = document.getElementById('event-title').value.trim();
    const start = document.getElementById('event-start').value;
    const end = document.getElementById('event-end').value;
    let category = document.getElementById('event-category').value;
    const desc = document.getElementById('event-description').value;
    const errBox = document.getElementById('form-error');
    errBox.classList.add('hidden');
    let category_color = null;
    const newName = document.getElementById('new-category-name').value.trim();
    const newColor = document.getElementById('new-category-color').value || '#0d9488';
    if (category === '__new__' || (!category && newName)) {
      if (!newName) { errBox.textContent = 'Provide a category name.'; errBox.classList.remove('hidden'); return; }
      category = newName; category_color = newColor;
    }
    if (!title || !start || !end || !category) { errBox.textContent = 'Fill in all required fields.'; errBox.classList.remove('hidden'); return; }
    if (new Date(end) <= new Date(start)) { errBox.textContent = 'End must be after start.'; errBox.classList.remove('hidden'); return; }
    this.disabled = true; this.textContent = 'Creating…';
    let rrule = null, recurrence_end = null;
    if (document.getElementById('event-repeat-weekly').checked) {
      rrule = 'FREQ=WEEKLY;BYDAY=' + document.getElementById('event-weekday').value;
      const until = document.getElementById('event-recurrence-end').value;
      if (until) recurrence_end = until + 'T23:59:59';
    }
    fetch('/api/events/create/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, description: desc, start_time: start, end_time: end, category, category_color, rrule, recurrence_end })
    }).then(r => r.json()).then(data => {
      if (data.success) { document.getElementById('event-modal').classList.add('hidden'); calendar.refetchEvents(); }
      else { errBox.textContent = data.error || 'Error'; errBox.classList.remove('hidden'); }
    }).catch(() => { errBox.textContent = 'Network error.'; errBox.classList.remove('hidden'); })
      .finally(() => { this.disabled = false; this.textContent = 'Create Event'; });
  };

  // ── Event Popover ──
  function showEventPopover(event, el) {
    closePopover();
    const pop = document.createElement('div');
    pop.id = 'event-popover';
    pop.className = 'fixed z-[80] bg-white rounded-2xl shadow-2xl border border-slate-200 w-80 p-5 space-y-3 animate-pop';
    const rect = el.getBoundingClientRect();
    pop.style.top = Math.min(rect.bottom + 8, window.innerHeight - 320) + 'px';
    pop.style.left = Math.min(rect.left, window.innerWidth - 340) + 'px';
    const ext = event.extendedProps;
    const catColor = ext.categoryColor || '#94a3b8';
    const startD = new Date(event.start);
    const endD = event.end ? new Date(event.end) : startD;
    const fmt = d => d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    pop.innerHTML = `
      <div class="flex items-start justify-between">
        <div class="flex items-center gap-2 min-w-0">
          <span class="w-3 h-3 rounded-full shrink-0" style="background:${catColor}"></span>
          <h4 class="text-sm font-bold text-slate-900 truncate">${event.title}</h4>
        </div>
        <button onclick="closePopover()" class="text-slate-300 hover:text-slate-600 text-lg leading-none">&times;</button>
      </div>
      <div class="text-xs text-slate-500 space-y-1">
        <p>📅 ${fmt(startD)} → ${fmt(endD)}</p>
        ${ext.category ? '<p>🏷️ ' + ext.category + '</p>' : ''}
        ${ext.description ? '<p class="text-slate-400 italic">' + ext.description + '</p>' : ''}
        ${ext.isRecurring ? '<p class="text-amber-600">↻ Recurring event</p>' : ''}
      </div>
      ${ext.aiTip ? `
      <div class="mt-3 p-3 bg-teal-50 rounded-xl border border-teal-100">
        <div class="flex items-center gap-1.5 mb-1">
          <span class="text-[10px]">💡</span>
          <span class="text-[10px] font-bold text-teal-700 uppercase tracking-wider">AI Insight</span>
        </div>
        <p class="text-xs text-teal-900 leading-relaxed italic">"${ext.aiTip}"</p>
      </div>` : ''}
      <div class="flex gap-2 pt-2 border-t border-slate-100">
        <button onclick="deleteFromPopover(${event.id}, ${ext.isRecurring}, '${ext.originalStart || ''}')" class="flex-1 text-xs font-semibold text-red-500 hover:bg-red-50 py-2 rounded-lg transition">Delete</button>
        <button onclick="closePopover()" class="flex-1 text-xs font-semibold text-slate-500 hover:bg-slate-50 py-2 rounded-lg transition">Close</button>
      </div>`;
    document.body.appendChild(pop);
    setTimeout(() => document.addEventListener('click', popClickAway), 10);
  }
  function popClickAway(e) { if (!e.target.closest('#event-popover')) closePopover(); }
  window.closePopover = function () {
    const p = document.getElementById('event-popover'); if (p) p.remove();
    document.removeEventListener('click', popClickAway);
  };
  window.deleteFromPopover = function (eventId, isRecurring, originalStart) {
    if (isRecurring) {
      if (confirm('Delete only this occurrence?')) { doDelete(eventId, 'single', originalStart); return; }
      if (!confirm('Delete entire series?')) return;
    } else { if (!confirm('Delete this event?')) return; }
    doDelete(eventId, 'series', null);
  };
  function doDelete(id, scope, orig) {
    fetch('/api/events/' + id + '/delete/', {
      method: 'POST', headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope, original_start: orig })
    }).then(r => r.json()).then(d => { if (d.success) { closePopover(); calendar.refetchEvents(); } else alert(d.error); })
      .catch(() => alert('Network error'));
  }

  // ── Drag/Resize → update time ──
  function updateEventTime(event, revert) {
    const body = { start_time: event.start.toISOString(), end_time: (event.end || event.start).toISOString() };
    const ext = event.extendedProps;
    if (ext.isRecurring) { body.scope = 'single'; body.original_start = ext.originalStart; }
    fetch('/api/events/' + event.id + '/edit/', {
      method: 'POST', headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(r => r.json()).then(d => { if (!d.success) { alert(d.error); revert(); } })
      .catch(() => { alert('Network error'); revert(); });
  }

  // AI Tip
  window.showTip = function (text, title) {
    document.getElementById('aitip-text').textContent = text;
    document.getElementById('aitip-event-title').textContent = title;
    document.getElementById('aitip-modal').classList.remove('hidden');
  };
  window.closeTip = function () { document.getElementById('aitip-modal').classList.add('hidden'); };
});
