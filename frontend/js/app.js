/**
 * QueueSense Application Controller
 * Handles user interactions, file dropzone, computer vision processing checklist,
 * density indicator, error banner, and presentation controls.
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- DOM Elements ---
  const videoFileInput = document.getElementById('videoFileInput');
  const dropzone = document.getElementById('dropzone');
  const fileInfoBox = document.getElementById('fileInfoBox');
  const fileNameText = document.getElementById('fileNameText');
  const fileSizeText = document.getElementById('fileSizeText');
  const clearFileBtn = document.getElementById('clearFileBtn');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const analyzeBtnText = document.getElementById('analyzeBtnText');

  // Metric & Status Display Elements
  const queueCountVal = document.getElementById('queueCountVal');
  const estimatedWaitVal = document.getElementById('estimatedWaitVal');
  const serviceRateVal = document.getElementById('serviceRateVal');
  const statusBadge = document.getElementById('statusBadge');
  const densityText = document.getElementById('densityText');
  const densitySegLow = document.getElementById('densitySegLow');
  const densitySegMod = document.getElementById('densitySegMod');
  const densitySegHigh = document.getElementById('densitySegHigh');
  const lastUpdatedTime = document.getElementById('lastUpdatedTime');

  // Crowd Distribution Doughnut Chart Elements
  const doughnutChartSvg = document.getElementById('doughnutChartSvg');
  const doughnutTotalCount = document.getElementById('doughnutTotalCount');
  const distributionLegend = document.getElementById('distributionLegend');
  const distributionContent = document.getElementById('distributionContent');
  const distributionUnavailable = document.getElementById('distributionUnavailable');
  const distributionModeBadge = document.getElementById('distributionModeBadge');

  // Queue Trend Chart Elements
  const queueTrendCard = document.getElementById('queueTrendCard');
  const trendChartContainer = document.getElementById('trendChartContainer');
  const trendChartSvg = document.getElementById('trendChartSvg');
  const trendDirectionBadge = document.getElementById('trendDirectionBadge');
  const trendModeIndicator = document.getElementById('trendModeIndicator');
  const trendUnavailable = document.getElementById('trendUnavailable');

  // Recent Queue Activity Elements
  const recentActivityCard = document.getElementById('recentActivityCard');
  const activityTimelineList = document.getElementById('activityTimelineList');
  const activityEmptyState = document.getElementById('activityEmptyState');

  // Processing State Elements
  const processingCard = document.getElementById('processingCard');
  const stepElements = [
    document.getElementById('step1'),
    document.getElementById('step2'),
    document.getElementById('step3'),
    document.getElementById('step4')
  ];

  // Error & Informational Banner Elements
  const errorBanner = document.getElementById('errorBanner');
  const errorTitle = document.getElementById('errorTitle');
  const errorMessage = document.getElementById('errorMessage');
  const dismissErrorBtn = document.getElementById('dismissErrorBtn');
  const emptyQueueNotice = document.getElementById('emptyQueueNotice');

  // Demo Presentation Controls
  const mockToggle = document.getElementById('mockToggle');
  const mockToggleLabel = document.getElementById('mockToggleLabel');
  const currentModeBadge = document.getElementById('currentModeBadge');
  const scenarioBtns = document.querySelectorAll('.scenario-btn');
  const errorTestBtns = document.querySelectorAll('.error-test-btn');

  // State
  let selectedFile = null;
  let isAnalyzing = false;
  let stepTimer = null;


  // Recent Activity Events State
  const activityEvents = [
    {
      type: 'analysis',
      title: 'Queue analysis completed',
      description: 'Processed video sample for canteen line counter',
      time: 'Just now'
    },
    {
      type: 'count',
      title: 'Current queue: 8 people',
      description: 'Estimated wait is 4.0 min at 2.0 ppl/min throughput',
      time: '1 min ago'
    },
    {
      type: 'density',
      title: 'Density state: MODERATE',
      description: 'Crowd level within standard canteen capacity',
      time: '2 mins ago'
    }
  ];

  // Initialize UI with standard mock contract data
  // (isInitial = true to preserve default activity timeline)
  renderResult(window.QueueSenseAPI.DEFAULT_MOCK_DATA, true);

  // --- Keyboard & Click Accessibility on Dropzone ---

  dropzone.addEventListener('click', (e) => {
    if (!isAnalyzing && e.target !== videoFileInput) {
      videoFileInput.click();
    }
  });

  dropzone.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && !isAnalyzing) {
      e.preventDefault();
      videoFileInput.click();
    }
  });

  videoFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  // --- Drag and Drop Events ---

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('border-emerald-500', 'bg-emerald-50/40');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('border-emerald-500', 'bg-emerald-50/40');
    }, false);
  });

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  function handleFileSelected(file) {
    // Validate file type
    if (!window.QueueSenseAPI.validateFile(file)) {
      handleError({
        code: 'INVALID_FILE',
        message: 'Invalid file format. Please upload a valid MP4, MOV, or AVI video.'
      });
      return;
    }

    selectedFile = file;
    fileNameText.textContent = file.name;
    fileSizeText.textContent = formatBytes(file.size);
    fileInfoBox.classList.remove('hidden');
    hideError();
  }

  clearFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFile = null;
    videoFileInput.value = '';
    fileInfoBox.classList.add('hidden');
  });

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // --- Analysis Workflow & Computer Vision Pipeline State ---

  analyzeBtn.addEventListener('click', async () => {
    if (isAnalyzing) return;
    await executeAnalysis();
  });

  async function executeAnalysis(customScenario = null) {
    hideError();
    startProcessing();

    try {
      const options = {
        useMock: mockToggle.checked,
        scenario: customScenario || window.QueueSenseAPI.getScenario()
      };

      const result = await window.QueueSenseAPI.analyzeQueue(
        selectedFile, 
        options,
        (stepNumber) => updateStepProgress(stepNumber)
      );

      // Complete all steps before rendering result
      updateStepProgress(4);
      setTimeout(() => {
        renderResult(result);
        stopProcessing();
      }, 350);

    } catch (err) {
      stopProcessing();
      handleError(err);
    }
  }

  function startProcessing() {
    isAnalyzing = true;
    analyzeBtn.disabled = true;
    analyzeBtnText.textContent = 'Analyzing queue...';
    processingCard.classList.remove('hidden');
    
    // Reset steps
    stepElements.forEach((el, index) => {
      el.className = 'flex items-center gap-2.5 text-slate-400 transition-colors';
      const icon = el.querySelector('.step-icon');
      if (icon) {
        icon.className = 'step-icon w-4 h-4 rounded-full border border-slate-300 flex items-center justify-center text-[10px] font-bold';
        icon.textContent = String(index + 1);
      }
    });

    // Animate initial step
    updateStepProgress(1);
  }

  function updateStepProgress(activeStep) {
    stepElements.forEach((el, index) => {
      const stepIndex = index + 1;
      const icon = el.querySelector('.step-icon');

      if (stepIndex < activeStep) {
        // Completed step
        el.className = 'flex items-center gap-2.5 text-emerald-700 font-semibold transition-colors';
        if (icon) {
          icon.className = 'step-icon w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px] font-bold';
          icon.innerHTML = '✓';
        }
      } else if (stepIndex === activeStep) {
        // Active in-progress step
        el.className = 'flex items-center gap-2.5 text-slate-900 font-bold transition-colors';
        if (icon) {
          icon.className = 'step-icon w-4 h-4 rounded-full border-2 border-emerald-600 text-emerald-700 flex items-center justify-center text-[10px] font-bold animate-pulse';
          icon.innerHTML = '→';
        }
      } else {
        // Upcoming step
        el.className = 'flex items-center gap-2.5 text-slate-400 transition-colors';
        if (icon) {
          icon.className = 'step-icon w-4 h-4 rounded-full border border-slate-300 flex items-center justify-center text-[10px] font-bold';
          icon.textContent = String(stepIndex);
        }
      }
    });
  }

  function stopProcessing() {
    isAnalyzing = false;
    analyzeBtn.disabled = false;
    analyzeBtnText.textContent = 'Analyze Queue';
    processingCard.classList.add('hidden');
  }

  // --- Result Rendering (3-Second Comprehension) ---

  function renderResult(data, isInitial = false) {
    if (!data) return;

    // 1. Dominant metric: People in queue
    queueCountVal.textContent = data.queue_count;

    // 2. Secondary operational metrics
    estimatedWaitVal.textContent = data.estimated_wait;
    serviceRateVal.textContent = Math.round(data.service_rate);

    // 3. Status Badge & Density Bar
    const statusStr = (data.status || 'MODERATE').toUpperCase();
    const densityStr = (data.density || 'MEDIUM').toUpperCase();

    densityText.textContent = densityStr;
    updateStatusVisuals(statusStr, densityStr);

    // 4. Zero people detected banner
    if (data.queue_count === 0) {
      emptyQueueNotice.classList.remove('hidden');
    } else {
      emptyQueueNotice.classList.add('hidden');
    }

    // 5. Updated timestamp
    const timeStr = data.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    lastUpdatedTime.textContent = `Updated ${timeStr}`;

    // 6. Crowd Distribution Circular Doughnut Chart
    renderCrowdDistribution(data);

    // 7. Queue Trend Line Chart
    renderQueueTrend(data);

    // 8. Recent Queue Activity Timeline
    if (!isInitial) {
      logEventsFromResult(data);
    }
    renderRecentActivity();
  }

  function renderCrowdDistribution(data) {
    if (!doughnutChartSvg || !distributionLegend) return;

    const distribution = data.crowd_distribution;

    // Fallback when zone/category breakdown is unavailable in live backend stream
    if (!distribution || !Array.isArray(distribution) || distribution.length === 0) {
      distributionContent.classList.add('hidden');
      distributionUnavailable.classList.remove('hidden');
      distributionModeBadge.textContent = 'Live Feed';
      distributionModeBadge.className = 'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200';
      return;
    }

    // Category breakdown is available
    distributionContent.classList.remove('hidden');
    distributionUnavailable.classList.add('hidden');

    const isMock = data.isMock !== false;
    distributionModeBadge.textContent = isMock ? 'Demo Breakdown' : 'Zone Breakdown';
    distributionModeBadge.className = isMock
      ? 'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200'
      : 'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200';

    // Total detected people displayed in the center of the doughnut
    const totalCount = typeof data.queue_count === 'number' 
      ? data.queue_count 
      : distribution.reduce((sum, item) => sum + (item.count || 0), 0);
    doughnutTotalCount.textContent = totalCount;

    // SVG geometry calculations
    // Center: (70, 70), Radius: 50 -> Circumference: 2 * PI * 50 = 314.159
    const radius = 50;
    const circumference = 2 * Math.PI * radius;

    // Reset base circle
    doughnutChartSvg.innerHTML = `<circle cx="70" cy="70" r="${radius}" fill="transparent" stroke="#f1f5f9" stroke-width="15" />`;

    // Legend header for separate aligned columns
    const legendHeader = `
      <div class="grid grid-cols-[1fr_48px_56px] items-center gap-x-4 px-3 pb-2 border-b border-slate-100 text-[10px] font-bold uppercase tracking-wider text-slate-400">
        <span>Category</span>
        <span class="text-right">Count</span>
        <span class="text-right">Share</span>
      </div>
    `;

    // Zero people detected state
    if (totalCount === 0) {
      const emptyRows = distribution.map(item => `
        <div class="grid grid-cols-[1fr_48px_56px] items-center gap-x-4 py-2 px-3 rounded-lg hover:bg-slate-50/80 transition-colors">
          <div class="flex items-center gap-2.5 min-w-0">
            <span class="w-2.5 h-2.5 rounded-full flex-shrink-0 shadow-sm" style="background-color: ${item.color};"></span>
            <span class="text-xs font-semibold text-slate-700 leading-snug break-words">${item.name}</span>
          </div>
          <span class="text-right font-bold text-slate-900 font-mono text-xs tabular-nums">0</span>
          <span class="text-right font-semibold text-slate-400 font-mono text-xs tabular-nums">0%</span>
        </div>
      `).join('');
      distributionLegend.innerHTML = legendHeader + emptyRows;
      return;
    }

    // Render colored segments and legend rows
    let accumulatedOffset = 0;
    let legendRows = '';

    distribution.forEach((item) => {
      const count = item.count || 0;
      const percent = Math.round((count / totalCount) * 100);
      const dashLength = (count / totalCount) * circumference;

      if (dashLength > 0) {
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', '70');
        circle.setAttribute('cy', '70');
        circle.setAttribute('r', String(radius));
        circle.setAttribute('fill', 'transparent');
        circle.setAttribute('stroke', item.color);
        circle.setAttribute('stroke-width', '15');
        circle.setAttribute('stroke-dasharray', `${dashLength.toFixed(2)} ${(circumference - dashLength).toFixed(2)}`);
        circle.setAttribute('stroke-dashoffset', `-${accumulatedOffset.toFixed(2)}`);
        circle.setAttribute('class', 'transition-all duration-500');
        doughnutChartSvg.appendChild(circle);

        accumulatedOffset += dashLength;
      }

      legendRows += `
        <div class="grid grid-cols-[1fr_48px_56px] items-center gap-x-4 py-2 px-3 rounded-lg hover:bg-slate-50/80 transition-colors">
          <div class="flex items-center gap-2.5 min-w-0">
            <span class="w-2.5 h-2.5 rounded-full flex-shrink-0 shadow-sm" style="background-color: ${item.color};"></span>
            <span class="text-xs font-semibold text-slate-700 leading-snug break-words">${item.name}</span>
          </div>
          <span class="text-right font-bold text-slate-900 font-mono text-xs tabular-nums">${count}</span>
          <span class="text-right font-semibold text-slate-500 font-mono text-xs tabular-nums">${percent}%</span>
        </div>
      `;
    });

    distributionLegend.innerHTML = legendHeader + legendRows;
  }

  // --- Queue Trend Line Chart Renderer ---

  function renderQueueTrend(data) {
    if (!trendChartSvg || !trendChartContainer) return;

    const trend = data.queue_trend;

    // Friendly empty state for live mode when tracking batches aren't available yet
    if (!trend || !Array.isArray(trend) || trend.length < 2) {
      trendChartContainer.classList.add('hidden');
      trendUnavailable.classList.remove('hidden');
      trendDirectionBadge.textContent = 'Awaiting Data';
      trendDirectionBadge.className = 'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200';
      return;
    }

    trendChartContainer.classList.remove('hidden');
    trendUnavailable.classList.add('hidden');

    const isMock = data.isMock !== false;
    trendModeIndicator.textContent = isMock ? 'Demo Batches' : 'Tracked Batches';

    // SVG geometry calculations
    // viewBox: 0 0 420 180
    const w = 420;
    const h = 180;
    const padL = 38;
    const padR = 26;
    const padT = 24;
    const padB = 34;

    const plotW = w - padL - padR;
    const plotH = h - padT - padB;

    // Y scale
    const counts = trend.map(t => t.count);
    const maxVal = Math.max(10, Math.ceil(Math.max(...counts) / 5) * 5);
    const yGridVals = [0, Math.round(maxVal / 2), maxVal];

    // Map points to canvas coordinates
    const points = trend.map((item, idx) => {
      const x = padL + (idx * (plotW / (trend.length - 1)));
      const y = padT + (1 - (item.count / maxVal)) * plotH;
      return { x, y, count: item.count, batch: item.batch };
    });

    // Summary of trend direction
    const firstCount = points[0].count;
    const lastCount = points[points.length - 1].count;

    if (lastCount > firstCount) {
      trendDirectionBadge.textContent = 'Increasing ↑';
      trendDirectionBadge.className = 'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200';
    } else if (lastCount < firstCount) {
      trendDirectionBadge.textContent = 'Decreasing ↓';
      trendDirectionBadge.className = 'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200';
    } else {
      trendDirectionBadge.textContent = 'Stable →';
      trendDirectionBadge.className = 'text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200';
    }

    const baselineY = padT + plotH;

    // Grid lines and Y labels
    let gridSvg = '';
    yGridVals.forEach(val => {
      const gridY = padT + (1 - (val / maxVal)) * plotH;
      gridSvg += `
        <line x1="${padL}" y1="${gridY.toFixed(1)}" x2="${w - padR}" y2="${gridY.toFixed(1)}" stroke="#f1f5f9" stroke-dasharray="3 3" stroke-width="1" />
        <text x="${padL - 6}" y="${(gridY + 3).toFixed(1)}" text-anchor="end" font-size="9" fill="#94a3b8" font-family="monospace">${val}</text>
      `;
    });

    // Line & Area paths
    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    const areaD = `${pathD} L ${points[points.length - 1].x.toFixed(1)} ${baselineY} L ${points[0].x.toFixed(1)} ${baselineY} Z`;

    // Data points, badges, X-axis labels
    let pointsSvg = '';
    points.forEach(p => {
      pointsSvg += `
        <!-- X Axis Label -->
        <text x="${p.x.toFixed(1)}" y="${baselineY + 18}" text-anchor="middle" font-size="9" font-weight="600" fill="#64748b">${p.batch}</text>
        <!-- Point Circle -->
        <circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="4.5" fill="#ffffff" stroke="#2563eb" stroke-width="2.5" class="trend-point" />
        <!-- Count Value Badge -->
        <text x="${p.x.toFixed(1)}" y="${(p.y - 8).toFixed(1)}" text-anchor="middle" font-size="11" font-weight="bold" fill="#0f172a" font-family="monospace">${p.count}</text>
      `;
    });

    trendChartSvg.innerHTML = `
      <defs>
        <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.22"/>
          <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      <!-- Grid -->
      ${gridSvg}
      <!-- Gradient Fill -->
      <path d="${areaD}" fill="url(#trendGradient)" />
      <!-- Line -->
      <path d="${pathD}" fill="none" stroke="#2563eb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" class="trend-line" />
      <!-- Points & Labels -->
      ${pointsSvg}
    `;
  }

  // --- Recent Queue Activity Engine ---

  function logEventsFromResult(data) {
    const timeStr = data.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Primary analysis event
    activityEvents.unshift({
      type: 'analysis',
      title: 'Queue analysis completed',
      description: `Analysis finished • ${data.queue_count} people in queue`,
      time: timeStr
    });

    // Special status transitions
    if (data.queue_count === 0) {
      activityEvents.unshift({
        type: 'empty',
        title: 'Counter clear (0 people)',
        description: 'Zero waiting line detected at canteen counter',
        time: timeStr
      });
    } else if (data.queue_count >= 15) {
      activityEvents.unshift({
        type: 'threshold',
        title: 'High rush threshold reached',
        description: `Crowd volume reached ${data.queue_count} people (${data.density} density)`,
        time: timeStr
      });
    }

    // Keep the most recent 6 events
    if (activityEvents.length > 6) {
      activityEvents.length = 6;
    }
  }

  function renderRecentActivity() {
    if (!activityTimelineList || !activityEmptyState) return;

    if (activityEvents.length === 0) {
      activityTimelineList.classList.add('hidden');
      activityEmptyState.classList.remove('hidden');
      return;
    }

    activityTimelineList.classList.remove('hidden');
    activityEmptyState.classList.add('hidden');

    const iconMap = {
      analysis: {
        bg: 'bg-emerald-100 text-emerald-700',
        svg: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`
      },
      count: {
        bg: 'bg-blue-100 text-blue-700',
        svg: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>`
      },
      density: {
        bg: 'bg-amber-100 text-amber-700',
        svg: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`
      },
      wait: {
        bg: 'bg-teal-100 text-teal-700',
        svg: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
      },
      threshold: {
        bg: 'bg-rose-100 text-rose-700',
        svg: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`
      },
      empty: {
        bg: 'bg-emerald-100 text-emerald-700',
        svg: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`
      }
    };

    activityTimelineList.innerHTML = activityEvents.map(evt => {
      const icon = iconMap[evt.type] || iconMap.analysis;
      return `
        <div class="flex items-start gap-3 relative pb-3.5 last:pb-1">
          <div class="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 z-10 shadow-sm ${icon.bg}">
            ${icon.svg}
          </div>
          <div class="flex-1 min-w-0 pt-0.5">
            <div class="flex items-center justify-between gap-2">
              <p class="text-xs font-bold text-slate-900 truncate">${evt.title}</p>
              <span class="text-[10px] font-mono text-slate-400 flex-shrink-0">${evt.time}</span>
            </div>
            <p class="text-[11px] text-slate-500 mt-0.5 leading-snug">${evt.description}</p>
          </div>
        </div>
      `;
    }).join('');
  }

  function updateStatusVisuals(status, density) {
    // Reset density segments to neutral base
    const neutralClass = 'density-step py-2 px-1 rounded-lg border border-slate-200 text-[11px] font-bold text-slate-400 bg-slate-50';
    densitySegLow.className = neutralClass;
    densitySegMod.className = neutralClass;
    densitySegHigh.className = neutralClass;

    const isLow = status.includes('LOW') || density.includes('LOW');
    const isHigh = status.includes('HIGH') || status.includes('CROWDED') || status.includes('BUSY') || density.includes('HIGH');

    if (isLow) {
      // LOW / CALM STATUS
      statusBadge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wide bg-emerald-100 text-emerald-800 border border-emerald-300';
      statusBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> LOW WAIT';
      
      densitySegLow.className = 'density-step py-2 px-1 rounded-lg border border-emerald-300 text-[11px] font-extrabold text-emerald-900 bg-emerald-100 shadow-sm';

    } else if (isHigh) {
      // HIGH / BUSY STATUS
      statusBadge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wide bg-rose-100 text-rose-800 border border-rose-300';
      statusBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-rose-600"></span> BUSY / HIGH';

      densitySegHigh.className = 'density-step py-2 px-1 rounded-lg border border-rose-300 text-[11px] font-extrabold text-rose-900 bg-rose-100 shadow-sm';

    } else {
      // MODERATE / ATTENTION (Default)
      statusBadge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wide bg-amber-100 text-amber-800 border border-amber-300';
      statusBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-amber-600"></span> MODERATE';

      densitySegMod.className = 'density-step py-2 px-1 rounded-lg border border-amber-300 text-[11px] font-extrabold text-amber-900 bg-amber-100 shadow-sm';
    }
  }

  // --- Error Handling ---

  function handleError(err) {
    console.error('QueueSense Error:', err);

    let title = 'Unable to analyze video.';
    let message = 'Please try again or check that the backend is running.';

    if (err.code === 'BACKEND_UNAVAILABLE') {
      title = 'Backend Unavailable';
      message = 'Unable to connect to backend server. Please verify the Flask service is running or switch to demo mode.';
    } else if (err.code === 'PROCESSING_ERROR') {
      title = 'Video Processing Failed';
      message = 'Unable to analyze video. Computer vision processing failed.';
    } else if (err.code === 'INVALID_RESPONSE') {
      title = 'Invalid API Response';
      message = 'Invalid response format received from backend.';
    } else if (err.code === 'INVALID_FILE') {
      title = 'Invalid File';
      message = 'Invalid file format. Please upload a valid MP4, MOV, or AVI video.';
    } else if (err.message) {
      message = err.message;
    }

    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorBanner.classList.remove('hidden');
  }

  function hideError() {
    errorBanner.classList.add('hidden');
  }

  dismissErrorBtn.addEventListener('click', hideError);

  // --- Presentation & Demo Mode Controls ---

  mockToggle.addEventListener('change', (e) => {
    const isMock = e.target.checked;
    window.QueueSenseAPI.config.USE_MOCK = isMock;
    mockToggleLabel.textContent = isMock ? 'Mock Data (Active)' : 'Live Flask API (Active)';
    currentModeBadge.textContent = isMock ? 'MOCK MODE' : 'LIVE API';
    currentModeBadge.className = isMock 
      ? 'text-[10px] text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 font-mono'
      : 'text-[10px] text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300 font-mono';
  });

  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const scenario = btn.dataset.scenario;
      window.QueueSenseAPI.setScenario(scenario);
      executeAnalysis(scenario);
    });
  });

  errorTestBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const errorType = btn.dataset.error;
      if (errorType === 'backend_down') {
        handleError({ code: 'BACKEND_UNAVAILABLE' });
      } else if (errorType === 'proc_error') {
        handleError({ code: 'PROCESSING_ERROR' });
      } else if (errorType === 'invalid_file') {
        handleError({ code: 'INVALID_FILE' });
      } else if (errorType === 'invalid_resp') {
        handleError({ code: 'INVALID_RESPONSE' });
      }
    });
  });

});
