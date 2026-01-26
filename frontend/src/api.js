import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
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

export const triggerWebhook = async (jdText, resumes, topK) => {
    const formData = new FormData();
    formData.append("jd_text", jdText);
    formData.append("top_k", topK);

    for (let i = 0; i < resumes.length; i++) {
        formData.append("resumes", resumes[i]);
    }

    const res = await fetch("http://127.0.0.1:5678/webhook-test/hr-intake", {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
    }

    return await res.json();
};

export const resetDatabase = async () => {
    const response = await api.delete('/utils/reset');
    return response.data;
};

export const generateJD = async (role, experience, skills) => {
    const response = await api.post('/utils/generate-jd', { role, experience, skills });
    return response.data;
};

export default api;
