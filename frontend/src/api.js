import axios from 'axios';

const API_BASE_URL = (typeof window !== "undefined"
  ? (import.meta.env.VITE_API_BASE_URL || '/api')
  : (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000')
).replace(/\/$/, '');

// Simple client-side cache for GET requests
const requestCache = {
    data: {},
    inFlight: {},
};

const getCacheKey = (url, params = {}) => {
    const paramStr = Object.keys(params)
        .sort()
        .map(k => `${k}=${JSON.stringify(params[k])}`)
        .join('&');
    return `${url}${paramStr ? '?' + paramStr : ''}`;
};

const getCachedResponse = (cacheKey) => {
    const cached = requestCache.data[cacheKey];
    if (!cached) return null;
    
    const age = (Date.now() - cached.timestamp) / 1000;
    // Cache TTL: 20 seconds for interview status, 60 seconds for notifications
    const ttl = cacheKey.includes('interviewstatus') ? 20 : 60;
    
    if (age < ttl) {
        return cached.response;
    }
    
    // Expired, remove from cache
    delete requestCache.data[cacheKey];
    return null;
};

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 300000, // 5 minutes
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Add response caching and request deduplication for GET requests
api.interceptors.response.use(
    (response) => {
        if (response.config.method === 'get') {
            const cacheKey = getCacheKey(response.config.url, response.config.params);
            requestCache.data[cacheKey] = {
                response: response.data,
                timestamp: Date.now(),
            };
            delete requestCache.inFlight[cacheKey];
        }
        return response;
    },
    (error) => {
        const cacheKey = getCacheKey(error.config.url, error.config.params);
        delete requestCache.inFlight[cacheKey];
        return Promise.reject(error);
    }
);

export const extractTextFromJD = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/utils/extract-text', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const analyzeResume = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/resume/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const uploadResumesBatch = async (files) => {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    const response = await api.post('/resume/upload-batch', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
};

export const matchResumes = async (jdText, topK = 5) => {
    const response = await api.post('/resume/match', { jd_text: jdText, top_k: topK });
    return response.data;
};

export const triggerWebhook = async (jdText, matchResults, topK) => {
    const payload = {
        jd_text: jdText,
        top_k: topK,
        matches: matchResults.map(m => ({
            ...m,
            // Ensure skills is a proper array or clean string to avoid N8N regex issues
            // Sending as array makes it easier for N8N to handle without string replacement hacks
            Skills: m.Skills ? m.Skills.split(',').map(s => s.trim()) : []
        }))
    };

    const res = await fetch("http://localhost:5678/webhook/start-screening", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload),
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
    }

    return await res.json();
};

export const generateJD = async (role, experience, skills) => {
    const response = await api.post('/utils/generate-jd', { role, experience, skills });
    return response.data;
};

export const createJobDescription = async (jobData) => {
    const response = await api.post('/jobs/create', jobData);
    return response.data;
};

export const getInterviewStatus = async (forceFresh = false) => {
    const cacheKey = getCacheKey('/jobs/interviewstatus');

    if (forceFresh) {
        delete requestCache.data[cacheKey];
        delete requestCache.inFlight[cacheKey];
    }
    
    // Check if we have a cached response within TTL
    const cached = getCachedResponse(cacheKey);
    if (cached) {
        return cached;
    }
    
    // Check if a request is already in flight to avoid duplicate network calls
    if (requestCache.inFlight[cacheKey]) {
        return requestCache.inFlight[cacheKey];
    }
    
    // Make the request and track it
    const promise = api.get('/jobs/interviewstatus').then(res => res.data);
    requestCache.inFlight[cacheKey] = promise;
    
    return promise;
};

export const getNotifications = async (params = {}) => {
    const limit = params.limit ?? 50;
    const offset = params.offset ?? 0;
    const unreadOnly = params.unread_only ?? false;
    const cacheKey = getCacheKey(`/notifications?limit=${limit}&offset=${offset}&unread=${unreadOnly}`);
    
    const cached = getCachedResponse(cacheKey);
    if (cached) {
        return cached;
    }
    
    if (requestCache.inFlight[cacheKey]) {
        return requestCache.inFlight[cacheKey];
    }
    
    const promise = api.get('/notifications', { params: { limit, offset, unread_only: unreadOnly } }).then((res) => {
        const data = res.data;
        if (Array.isArray(data)) {
            return { items: data, total: data.length, unread: data.filter((n) => !n.read).length, limit, offset };
        }
        return data;
    });
    requestCache.inFlight[cacheKey] = promise;
    
    return promise;
};

export const markAllNotificationsRead = async () => {
    const response = await api.patch('/notifications/read-all');
    return response.data;
};

export const clearAllInterviews = async () => {
    const response = await api.delete('/jobs/clear-interviews');
    return response.data;
};

export const submitOAResultFromUrl = async ({ candidateEmail, candidateName, reportUrl }) => {
    const payload = {
        candidate_email: candidateEmail,
        candidate_name: candidateName,
        report_url: reportUrl,
    };

    const response = await api.post('/oa/submit-from-url', payload);
    return response.data;
};

export const markNotificationRead = async (id) => {
    const response = await api.patch(`/notifications/${id}/read`);
    return response.data;
};

export default api;
