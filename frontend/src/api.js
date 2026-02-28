import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 300000, // 5 minutes
});

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

export const getInterviewStatus = async () => {
    const response = await api.get('/jobs/interviewstatus');
    return response.data;
};

export const clearAllInterviews = async () => {
    const response = await api.delete('/jobs/clear-interviews');
    return response.data;
};

export const getNotifications = async () => {
    const response = await api.get('/notifications');
    return response.data;
};

export const markNotificationRead = async (id) => {
    const response = await api.patch(`/notifications/${id}/read`);
    return response.data;
};

export default api;
