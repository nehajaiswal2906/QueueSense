/**
 * QueueSense Centralized API Module
 * Preserves the exact backend contract while supporting mock fallbacks,
 * input validation, and structured error mapping.
 */

const API_CONFIG = {
  USE_MOCK: false,
  ENDPOINT: 'http://localhost:5000/upload',
  TIMEOUT_MS: 90000,
  MOCK_DELAY_MS: 2200 // Sufficient time to display realistic CV pipeline steps
};

// Official Mock Data Contract
const DEFAULT_MOCK_DATA = {
  queue_count: 8,
  service_rate: 2.0,
  estimated_wait: 4.0,
  density: "medium",
  status: "moderate",
  // Demo crowd distribution across queue zones/activities
  crowd_distribution: [
    { name: "Placing an order", count: 3, percent: 38, color: "#3b82f6" },     // Blue
    { name: "Waiting for food", count: 3, percent: 38, color: "#10b981" },     // Green
    { name: "Collecting an order", count: 1, percent: 12, color: "#f97316" },  // Orange
    { name: "Other detected activity", count: 1, percent: 12, color: "#eab308" }// Yellow
  ],
  // Illustrative batches of 10 observed people (demo tracking data)
  queue_trend: [
    { batch: "Batch 1 (1–10)", count: 5 },
    { batch: "Batch 2 (11–20)", count: 7 },
    { batch: "Batch 3 (21–30)", count: 8 }
  ]
};

// Preset demo scenarios for hackathon agility
const MOCK_SCENARIOS = {
  moderate: {
    queue_count: 8,
    service_rate: 2.0,
    estimated_wait: 4.0,
    density: "medium",
    status: "moderate",
    crowd_distribution: [
      { name: "Placing an order", count: 3, percent: 38, color: "#3b82f6" },
      { name: "Waiting for food", count: 3, percent: 38, color: "#10b981" },
      { name: "Collecting an order", count: 1, percent: 12, color: "#f97316" },
      { name: "Other detected activity", count: 1, percent: 12, color: "#eab308" }
    ],
    queue_trend: [
      { batch: "Batch 1 (1–10)", count: 5 },
      { batch: "Batch 2 (11–20)", count: 7 },
      { batch: "Batch 3 (21–30)", count: 8 }
    ]
  },
  low: {
    queue_count: 2,
    service_rate: 2.0,
    estimated_wait: 1.0,
    density: "low",
    status: "low",
    crowd_distribution: [
      { name: "Placing an order", count: 1, percent: 50, color: "#3b82f6" },
      { name: "Waiting for food", count: 1, percent: 50, color: "#10b981" },
      { name: "Collecting an order", count: 0, percent: 0, color: "#f97316" },
      { name: "Other detected activity", count: 0, percent: 0, color: "#eab308" }
    ],
    queue_trend: [
      { batch: "Batch 1 (1–10)", count: 6 },
      { batch: "Batch 2 (11–20)", count: 4 },
      { batch: "Batch 3 (21–30)", count: 2 }
    ]
  },
  high: {
    queue_count: 18,
    service_rate: 2.0,
    estimated_wait: 9.0,
    density: "high",
    status: "high",
    crowd_distribution: [
      { name: "Placing an order", count: 6, percent: 33, color: "#3b82f6" },
      { name: "Waiting for food", count: 7, percent: 39, color: "#10b981" },
      { name: "Collecting an order", count: 3, percent: 17, color: "#f97316" },
      { name: "Other detected activity", count: 2, percent: 11, color: "#eab308" }
    ],
    queue_trend: [
      { batch: "Batch 1 (1–10)", count: 11 },
      { batch: "Batch 2 (11–20)", count: 15 },
      { batch: "Batch 3 (21–30)", count: 18 }
    ]
  },
  empty: {
    queue_count: 0,
    service_rate: 2.0,
    estimated_wait: 0.0,
    density: "low",
    status: "low",
    crowd_distribution: [
      { name: "Placing an order", count: 0, percent: 0, color: "#3b82f6" },
      { name: "Waiting for food", count: 0, percent: 0, color: "#10b981" },
      { name: "Collecting an order", count: 0, percent: 0, color: "#f97316" },
      { name: "Other detected activity", count: 0, percent: 0, color: "#eab308" }
    ],
    queue_trend: [
      { batch: "Batch 1 (1–10)", count: 0 },
      { batch: "Batch 2 (11–20)", count: 0 }
    ]
  }
};

let currentScenario = 'moderate';

/**
 * Validates whether an uploaded file is a valid video/image format
 * @param {File} file 
 * @returns {boolean}
 */
function validateFile(file) {
  if (!file) return true; // Optional if analyzing default sample
  const validTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/mkv', 'image/jpeg', 'image/png'];
  const validExtensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.jpg', '.jpeg', '.png'];
  
  const typeMatches = file.type && validTypes.includes(file.type.toLowerCase());
  const extMatches = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
  
  return typeMatches || extMatches;
}

/**
 * Validates the incoming API payload against the expected QueueSense contract
 * @param {object} data 
 * @returns {boolean}
 */
function validateResponse(data) {
  if (!data || typeof data !== 'object') return false;
  
  const hasQueueCount = typeof data.queue_count === 'number' && !isNaN(data.queue_count);
  const hasStatus = typeof data.status === 'string' && data.status.trim().length > 0;

  return hasQueueCount && hasStatus;
}

/**
 * Centralized API entrypoint to analyze queue video
 * @param {File|null} videoFile 
 * @param {object} options 
 * @param {function} onStepCallback - optional callback for tracking inference steps
 * @returns {Promise<object>}
 */
async function analyzeQueue(videoFile = null, options = {}, onStepCallback = null) {
  const useMock = options.useMock !== undefined ? options.useMock : API_CONFIG.USE_MOCK;
  const scenario = options.scenario || currentScenario;

  // File validation check
  if (videoFile && !validateFile(videoFile)) {
    const error = new Error('Invalid file format. Please upload a valid MP4, MOV, or AVI video.');
    error.code = 'INVALID_FILE';
    throw error;
  }

  // 1. MOCK MODE EXECUTION
  if (useMock) {
    // Notify progressive processing steps if callback provided
    if (typeof onStepCallback === 'function') {
      setTimeout(() => onStepCallback(1), 300);
      setTimeout(() => onStepCallback(2), 900);
      setTimeout(() => onStepCallback(3), 1500);
      setTimeout(() => onStepCallback(4), 2000);
    }

    await new Promise(resolve => setTimeout(resolve, API_CONFIG.MOCK_DELAY_MS));

    // Simulated error triggers for presentation testing
    if (scenario === 'simulate_backend_down') {
      const error = new Error('Unable to connect to backend server. Please verify the Flask service is running or switch to demo mode.');
      error.code = 'BACKEND_UNAVAILABLE';
      throw error;
    }

    if (scenario === 'simulate_invalid') {
      const error = new Error('Invalid response format received from backend.');
      error.code = 'INVALID_RESPONSE';
      throw error;
    }

    if (scenario === 'simulate_proc_error') {
      const error = new Error('Unable to analyze video. Computer vision processing failed.');
      error.code = 'PROCESSING_ERROR';
      throw error;
    }

    const mockResult = MOCK_SCENARIOS[scenario] || DEFAULT_MOCK_DATA;
    
    if (!validateResponse(mockResult)) {
      const error = new Error('Mock data schema validation failed.');
      error.code = 'INVALID_RESPONSE';
      throw error;
    }

    return {
      ...mockResult,
      isMock: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };
  }

  // 2. REAL FLASK BACKEND INTEGRATION
  const formData = new FormData();
  if (videoFile) {
    formData.append('file', videoFile);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT_MS);

  try {
    if (typeof onStepCallback === 'function') {
      onStepCallback(1);
    }

    const response = await fetch(API_CONFIG.ENDPOINT, {
      method: 'POST',
      body: formData,
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (typeof onStepCallback === 'function') {
      onStepCallback(3);
    }

    if (!response.ok) {
      const error = new Error(`Server returned HTTP ${response.status} (${response.statusText})`);
      error.code = 'PROCESSING_ERROR';
      error.status = response.status;
      throw error;
    }

    let result;
    try {
      result = await response.json();
    } catch {
      const error = new Error('Invalid response format received from backend.');
      error.code = 'INVALID_RESPONSE';
      throw error;
    }

    if (!validateResponse(result)) {
      const error = new Error('Response did not match expected QueueSense schema.');
      error.code = 'INVALID_RESPONSE';
      error.rawPayload = result;
      throw error;
    }

    if (!result.density) {
      result.density = result.status || 'moderate';
    }

    if (typeof onStepCallback === 'function') {
      onStepCallback(4);
    }

    return {
      ...result,
      isMock: false,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    };

  } catch (err) {
    clearTimeout(timeoutId);

    if (err.name === 'AbortError') {
      const timeoutErr = new Error('Request timed out while waiting for CV inference.');
      timeoutErr.code = 'PROCESSING_ERROR';
      throw timeoutErr;
    }

    if (err.message && err.message.includes('Failed to fetch')) {
      const connErr = new Error('Unable to connect to backend server. Please verify the Flask service is running or switch to demo mode.');
      connErr.code = 'BACKEND_UNAVAILABLE';
      throw connErr;
    }

    if (!err.code) {
      err.code = 'PROCESSING_ERROR';
    }
    throw err;
  }
}

// Global API export
window.QueueSenseAPI = {
  config: API_CONFIG,
  analyzeQueue,
  validateResponse,
  validateFile,
  DEFAULT_MOCK_DATA,
  MOCK_SCENARIOS,
  setScenario: (sc) => { currentScenario = sc; },
  getScenario: () => currentScenario
};
