/**
 * QA AI Agent - Reactive Frontend Controller
 */

// Application State
const state = {
    projectId: null,
    projectName: null,
    projectProfile: null,
    apiKey: localStorage.getItem('QA_AGENT_API_KEY') || '',
    modelName: localStorage.getItem('QA_AGENT_MODEL') || 'gemini-2.5-flash',
};

// DOM Element References
const elements = {
    // Nav & Modals
    btnSettings: document.getElementById('btnSettings'),
    modalSettings: document.getElementById('modalSettings'),
    btnCloseModal: document.getElementById('btnCloseModal'),
    btnSaveKey: document.getElementById('btnSaveKey'),
    inputApiKey: document.getElementById('inputApiKey'),
    selectModel: document.getElementById('selectModel'),
    apiKeyStatusText: document.getElementById('apiKeyStatusText'),

    // Steps
    stepIndicator1: document.getElementById('stepIndicator1'),
    stepIndicator2: document.getElementById('stepIndicator2'),
    stepIndicator3: document.getElementById('stepIndicator3'),
    stepIndicator4: document.getElementById('stepIndicator4'),
    stepLine1: document.getElementById('stepLine1'),
    stepLine2: document.getElementById('stepLine2'),
    stepLine3: document.getElementById('stepLine3'),

    // Sections
    sectionIngest: document.getElementById('sectionIngest'),
    sectionProfile: document.getElementById('sectionProfile'),
    sectionGenerated: document.getElementById('sectionGenerated'),
    sectionExecution: document.getElementById('sectionExecution'),

    // Ingest tabs & inputs
    tabZip: document.getElementById('tabZip'),
    tabLocal: document.getElementById('tabLocal'),
    zoneZip: document.getElementById('zoneZip'),
    zoneLocal: document.getElementById('zoneLocal'),
    dropZone: document.getElementById('dropZone'),
    fileInput: document.getElementById('fileInput'),
    inputLocalPath: document.getElementById('inputLocalPath'),
    btnLoadLocal: document.getElementById('btnLoadLocal'),
    btnLoadSample: document.getElementById('btnLoadSample'),

    // Profile Display
    profProjectName: document.getElementById('profProjectName'),
    profPrimaryLang: document.getElementById('profPrimaryLang'),
    profPath: document.getElementById('profPath'),
    profFrameworkBadges: document.getElementById('profFrameworkBadges'),
    profFileCount: document.getElementById('profFileCount'),
    profLineCount: document.getElementById('profLineCount'),
    profEndpointCount: document.getElementById('profEndpointCount'),
    profFunctionCount: document.getElementById('profFunctionCount'),

    // Test Config & Generation
    checkUnit: document.getElementById('checkUnit'),
    checkApi: document.getElementById('checkApi'),
    checkE2e: document.getElementById('checkE2e'),
    btnGenerateTests: document.getElementById('btnGenerateTests'),
    generatedFilesList: document.getElementById('generatedFilesList'),

    // Action Buttons
    btnDownloadZip: document.getElementById('btnDownloadZip'),
    btnExecuteTests: document.getElementById('btnExecuteTests'),

    // Execution & Terminal
    runnerSpinner: document.getElementById('runnerSpinner'),
    terminalOutput: document.getElementById('terminalOutput'),
    resultsSummary: document.getElementById('resultsSummary'),
    resTotal: document.getElementById('resTotal'),
    resPassed: document.getElementById('resPassed'),
    resFailed: document.getElementById('resFailed'),
    resSkipped: document.getElementById('resSkipped'),
    resDuration: document.getElementById('resDuration'),

    // Reports
    reportActions: document.getElementById('reportActions'),
    btnDownloadHtmlReport: document.getElementById('btnDownloadHtmlReport'),
    btnDownloadMdReport: document.getElementById('btnDownloadMdReport'),
};

// Initialize UI
function init() {
    updateApiKeyBadge();
    bindEvents();
}

function updateApiKeyBadge() {
    if (state.apiKey) {
        elements.apiKeyStatusText.textContent = 'API Key Configured';
        elements.apiKeyStatusText.classList.add('text-emerald-400');
    } else {
        elements.apiKeyStatusText.textContent = 'Set API Key (Optional)';
        elements.apiKeyStatusText.classList.remove('text-emerald-400');
    }
    elements.inputApiKey.value = state.apiKey;
    elements.selectModel.value = state.modelName;
}

// Event Bindings
function bindEvents() {
    // Settings Modal
    elements.btnSettings.addEventListener('click', () => {
        elements.modalSettings.classList.remove('hidden');
    });
    elements.btnCloseModal.addEventListener('click', () => {
        elements.modalSettings.classList.add('hidden');
    });
    elements.btnSaveKey.addEventListener('click', () => {
        state.apiKey = elements.inputApiKey.value.trim();
        state.modelName = elements.selectModel.value;
        localStorage.setItem('QA_AGENT_API_KEY', state.apiKey);
        localStorage.setItem('QA_AGENT_MODEL', state.modelName);
        updateApiKeyBadge();
        elements.modalSettings.classList.add('hidden');
    });

    // Ingest Mode Tabs
    elements.tabZip.addEventListener('click', () => {
        elements.tabZip.classList.add('bg-zinc-800/90', 'text-white');
        elements.tabZip.classList.remove('text-zinc-400');
        elements.tabLocal.classList.remove('bg-zinc-800/90', 'text-white');
        elements.tabLocal.classList.add('text-zinc-400');
        elements.zoneZip.classList.remove('hidden');
        elements.zoneLocal.classList.add('hidden');
    });

    elements.tabLocal.addEventListener('click', () => {
        elements.tabLocal.classList.add('bg-zinc-800/90', 'text-white');
        elements.tabLocal.classList.remove('text-zinc-400');
        elements.tabZip.classList.remove('bg-zinc-800/90', 'text-white');
        elements.tabZip.classList.add('text-zinc-400');
        elements.zoneLocal.classList.remove('hidden');
        elements.zoneZip.classList.add('hidden');
    });

    // File Upload Handlers
    elements.dropZone.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileUpload);
    elements.dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.dropZone.classList.add('border-emerald-500');
    });
    elements.dropZone.addEventListener('dragleave', () => {
        elements.dropZone.classList.remove('border-emerald-500');
    });
    elements.dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.dropZone.classList.remove('border-emerald-500');
        if (e.dataTransfer.files.length) {
            uploadZipFile(e.dataTransfer.files[0]);
        }
    });

    // Local Path Loader
    elements.btnLoadLocal.addEventListener('click', () => {
        const path = elements.inputLocalPath.value.trim();
        if (path) loadLocalProject(path);
    });

    // Quick Sample Loader
    elements.btnLoadSample.addEventListener('click', () => {
        loadLocalProject('sample_projects/fastapi_calculator');
    });

    // Generate Tests Button
    elements.btnGenerateTests.addEventListener('click', triggerTestGeneration);

    // Download Project with Tests
    elements.btnDownloadZip.addEventListener('click', downloadProjectZip);

    // Run Tests Automatically
    elements.btnExecuteTests.addEventListener('click', triggerTestExecution);

    // Download Reports
    elements.btnDownloadHtmlReport.addEventListener('click', () => {
        window.open(`/api/projects/${state.projectId}/report?format=html`, '_blank');
    });
    elements.btnDownloadMdReport.addEventListener('click', () => {
        window.location.href = `/api/projects/${state.projectId}/report?format=md`;
    });
}

// Ingestion Handlers
function handleFileUpload(e) {
    if (e.target.files.length > 0) {
        uploadZipFile(e.target.files[0]);
    }
}

async function uploadZipFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    elements.dropZone.innerHTML = `
        <div class="py-4">
            <div class="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
            <p class="text-xs text-zinc-400">Uploading and extracting project archive...</p>
        </div>
    `;

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload failed');

        state.projectId = data.project_id;
        state.projectName = data.name;
        await runProjectAnalysis();
    } catch (err) {
        alert('Upload failed: ' + err.message);
        location.reload();
    }
}

async function loadLocalProject(path) {
    elements.btnLoadLocal.disabled = true;
    elements.btnLoadLocal.innerHTML = `<div class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>`;

    try {
        const res = await fetch('/api/load-local', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to load local path');

        state.projectId = data.project_id;
        state.projectName = data.name;
        await runProjectAnalysis();
    } catch (err) {
        alert('Failed to load project: ' + err.message);
    } finally {
        elements.btnLoadLocal.disabled = false;
        elements.btnLoadLocal.innerHTML = `<i data-lucide="folder-search" class="w-4 h-4"></i> Load`;
        lucide.createIcons();
    }
}

// Analysis & Profiling
async function runProjectAnalysis() {
    setStep(2);

    try {
        const res = await fetch(`/api/projects/${state.projectId}/analyze`, { method: 'POST' });
        const profile = await res.json();
        if (!res.ok) throw new Error(profile.detail || 'Analysis failed');

        state.projectProfile = profile;
        renderProfile(profile);

        elements.sectionProfile.classList.remove('hidden');
        elements.sectionProfile.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert('Analysis error: ' + err.message);
    }
}

function renderProfile(profile) {
    elements.profProjectName.textContent = profile.project_name;
    elements.profPrimaryLang.textContent = profile.primary_language;
    elements.profPath.textContent = profile.root_path;

    elements.profFileCount.textContent = profile.file_count;
    elements.profLineCount.textContent = profile.total_lines;
    elements.profEndpointCount.textContent = profile.endpoints ? profile.endpoints.length : 0;
    elements.profFunctionCount.textContent = profile.functions ? profile.functions.length : 0;

    // Framework badges
    elements.profFrameworkBadges.innerHTML = '';
    if (profile.frameworks && profile.frameworks.length) {
        profile.frameworks.forEach((fw) => {
            const badge = document.createElement('span');
            badge.className = 'px-2.5 py-1 text-xs font-medium rounded-lg bg-zinc-800 text-zinc-200 border border-zinc-700';
            badge.textContent = fw;
            elements.profFrameworkBadges.appendChild(badge);
        });
    }

    lucide.createIcons();
}

async function fetchJsonSafely(url, options = {}) {
    const res = await fetch(url, options);
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || data.message || `Server error (${res.status})`);
        }
        return data;
    } else {
        const text = await res.text();
        if (res.status === 504 || res.status === 502) {
            throw new Error(`Server request timed out (${res.status}). The project is very large.`);
        }
        throw new Error(`Server error (${res.status}): ${text.substring(0, 100)}`);
    }
}

// Test Generation
async function triggerTestGeneration() {
    setStep(3);

    const testTypes = [];
    if (elements.checkUnit.checked) testTypes.push('unit');
    if (elements.checkApi.checked) testTypes.push('api');
    if (elements.checkE2e.checked) testTypes.push('e2e');

    if (testTypes.length === 0) {
        alert('Please select at least one test type (Unit, API, or E2E).');
        return;
    }

    elements.btnGenerateTests.disabled = true;
    elements.btnGenerateTests.innerHTML = `
        <div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
        <span>Generating Test Suites...</span>
    `;

    try {
        // 1. Plan tests
        await fetchJsonSafely(`/api/projects/${state.projectId}/plan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_types: testTypes }),
        });

        // 2. Generate tests
        const genData = await fetchJsonSafely(`/api/projects/${state.projectId}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: state.apiKey || undefined,
                model_name: state.modelName,
            }),
        });

        renderGeneratedFiles(genData.files);

        elements.sectionGenerated.classList.remove('hidden');
        elements.sectionGenerated.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert('Generation failed: ' + err.message);
    } finally {
        elements.btnGenerateTests.disabled = false;
        elements.btnGenerateTests.innerHTML = `
            <i data-lucide="sparkles" class="w-4 h-4"></i>
            <span>Generate Test Suites</span>
        `;
        lucide.createIcons();
    }
}

function renderGeneratedFiles(files) {
    elements.generatedFilesList.innerHTML = '';
    files.forEach((f) => {
        const item = document.createElement('div');
        item.className = 'p-3 rounded-xl border border-zinc-800/80 bg-zinc-950/40 flex items-center justify-between';
        
        let typeBadgeColor = 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20';
        if (f.test_type === 'api') typeBadgeColor = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
        if (f.test_type === 'e2e') typeBadgeColor = 'bg-amber-500/10 text-amber-400 border-amber-500/20';

        item.innerHTML = `
            <div class="flex items-center gap-3">
                <i data-lucide="file-code" class="w-4 h-4 text-zinc-400"></i>
                <span class="font-mono text-xs text-zinc-200">${f.relative_path}</span>
            </div>
            <span class="px-2 py-0.5 text-[10px] font-semibold rounded-md border ${typeBadgeColor} uppercase">
                ${f.test_type}
            </span>
        `;
        elements.generatedFilesList.appendChild(item);
    });
    lucide.createIcons();
}

// Download Project with Tests (ZIP)
function downloadProjectZip() {
    if (!state.projectId) return;
    window.location.href = `/api/projects/${state.projectId}/download`;
}

// Run Tests Automatically (WebSocket stream)
function triggerTestExecution() {
    setStep(4);

    elements.sectionExecution.classList.remove('hidden');
    elements.sectionExecution.scrollIntoView({ behavior: 'smooth' });

    elements.btnExecuteTests.disabled = true;
    elements.runnerSpinner.classList.remove('hidden');
    elements.terminalOutput.textContent = '[QA Agent] Initializing test runner sandbox...\n';
    elements.resultsSummary.classList.add('hidden');
    elements.reportActions.classList.add('hidden');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/execute/${state.projectId}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'log') {
            elements.terminalOutput.textContent += msg.data + '\n';
            elements.terminalOutput.scrollTop = elements.terminalOutput.scrollHeight;
        } else if (msg.type === 'completed') {
            elements.runnerSpinner.classList.add('hidden');
            elements.btnExecuteTests.disabled = false;
            displayExecutionResults(msg.result);
        }
    };

    ws.onerror = (err) => {
        elements.terminalOutput.textContent += '\n[WebSocket Error] Falling back to standard runner...\n';
        runFallbackExecution();
    };
}

async function runFallbackExecution() {
    try {
        const res = await fetch(`/api/projects/${state.projectId}/execute`, { method: 'POST' });
        const result = await res.json();
        elements.runnerSpinner.classList.add('hidden');
        elements.btnExecuteTests.disabled = false;
        elements.terminalOutput.textContent += result.stdout + '\n' + (result.stderr || '');
        displayExecutionResults(result);
    } catch (err) {
        elements.terminalOutput.textContent += `\n[Fatal Error] Execution failed: ${err.message}`;
        elements.runnerSpinner.classList.add('hidden');
        elements.btnExecuteTests.disabled = false;
    }
}

function displayExecutionResults(result) {
    elements.resultsSummary.classList.remove('hidden');
    elements.reportActions.classList.remove('hidden');

    elements.resTotal.textContent = result.total_tests;
    elements.resPassed.textContent = result.passed;
    elements.resFailed.textContent = result.failed;
    elements.resSkipped.textContent = result.skipped;
    elements.resDuration.textContent = `${result.duration_seconds}s`;

    lucide.createIcons();
}

// Step tracker visuals
function setStep(step) {
    const steps = [
        { indicator: elements.stepIndicator1, line: elements.stepLine1 },
        { indicator: elements.stepIndicator2, line: elements.stepLine2 },
        { indicator: elements.stepIndicator3, line: elements.stepLine3 },
        { indicator: elements.stepIndicator4, line: null },
    ];

    steps.forEach((s, idx) => {
        const currentStepNum = idx + 1;
        const circle = s.indicator.querySelector('span:first-child');
        const label = s.indicator.querySelector('span:last-child');

        if (currentStepNum <= step) {
            circle.className = 'w-7 h-7 rounded-full bg-emerald-500 text-zinc-950 font-bold text-xs flex items-center justify-center';
            label.className = 'text-sm font-medium text-emerald-400';
            if (s.line) s.line.className = 'h-0.5 w-16 sm:w-24 bg-emerald-500';
        } else {
            circle.className = 'w-7 h-7 rounded-full bg-zinc-800 text-zinc-400 font-bold text-xs flex items-center justify-center';
            label.className = 'text-sm font-medium text-zinc-400';
            if (s.line) s.line.className = 'h-0.5 w-16 sm:w-24 bg-zinc-800';
        }
    });
}

// Start
window.addEventListener('DOMContentLoaded', init);

