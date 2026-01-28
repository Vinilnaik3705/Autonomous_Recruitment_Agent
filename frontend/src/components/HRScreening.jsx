import React, { useState } from 'react';
import { Upload, FileText, X, Check, Search, FileUp, Loader2, Sparkles, Sliders } from 'lucide-react';
import { extractTextFromJD, analyzeResume, matchResumes, triggerWebhook, generateJD, uploadResumesBatch } from '../api';

const HRScreening = () => {
    const [resumes, setResumes] = useState([]);
    const [jdMode, setJdMode] = useState('text'); // 'text', 'file', 'agent'
    const [jdText, setJdText] = useState('');
    const [topK, setTopK] = useState(5);
    const [jdAgentInput, setJdAgentInput] = useState({ role: '', exp: '', skills: '' });
    const [isGeneratingJD, setIsGeneratingJD] = useState(false);
    const [processing, setProcessing] = useState(false);
    const [matchResults, setMatchResults] = useState(null);
    const [uploadStatus, setUploadStatus] = useState({}); // { fileName: 'pending' | 'success' | 'error' }

    const handleResumeUpload = (e) => {
        const files = Array.from(e.target.files);
        setResumes(prev => [...prev, ...files]);
    };

    const removeResume = (index) => {
        setResumes(prev => prev.filter((_, i) => i !== index));
    };

    const handleJDFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        try {
            setProcessing(true);
            const data = await extractTextFromJD(file);
            setJdText(data.text);
            setProcessing(false);
        } catch (error) {
            console.error("JD Extraction failed", error);
            setProcessing(false);
            alert("Failed to extract text from JD file.");
        }
    };

    const handleGenerateJD = async () => {
        setIsGeneratingJD(true);
        try {
            const data = await generateJD(jdAgentInput.role, jdAgentInput.exp, jdAgentInput.skills);
            setJdText(data.jd_text);
            setJdMode('text'); // Switch to text mode so they can edit
        } catch (error) {
            console.error("JD Generation failed", error);
            alert("Failed to generate JD");
        } finally {
            setIsGeneratingJD(false);
        }
    };

    const resultsRef = React.useRef(null);

    const startScreening = async () => {
        if (resumes.length === 0) {
            alert("Please upload resumes first!");
            return;
        }
        if (!jdText.trim()) return alert("Please provide a Job Description.");

        setProcessing(true);
        setMatchResults(null);
        let currentMatches = [];

        // 1. Bulk Upload Resumes
        const BATCH_SIZE = 50;
        const totalBatches = Math.ceil(resumes.length / BATCH_SIZE);

        try {
            const newUploadStatus = {};
            for (let i = 0; i < totalBatches; i++) {
                const start = i * BATCH_SIZE;
                const end = Math.min(start + BATCH_SIZE, resumes.length);
                const batch = resumes.slice(start, end);

                batch.forEach(file => { newUploadStatus[file.name] = 'processing'; });
                setUploadStatus(prev => ({ ...prev, ...newUploadStatus }));

                try {
                    await uploadResumesBatch(batch);
                    batch.forEach(file => { newUploadStatus[file.name] = 'success'; });
                } catch (err) {
                    console.error(`Batch ${i + 1} failed`, err);
                    batch.forEach(file => { newUploadStatus[file.name] = 'error'; });
                }
                setUploadStatus(prev => ({ ...prev, ...newUploadStatus }));
            }
        } catch (error) {
            console.error("Upload process failed", error);
        }

        // 2. Match Resumes
        try {
            console.log("Matching resumes with topK:", topK);
            const results = await matchResumes(jdText, topK);
            console.log("Match Results Recieved:", results.matches);

            if (results.matches && results.matches.length > 0) {
                setMatchResults(results.matches);
                currentMatches = results.matches;

                // Scroll to results
                setTimeout(() => {
                    if (resultsRef.current) {
                        resultsRef.current.scrollIntoView({ behavior: 'smooth' });
                    }
                }, 100);
            } else {
                alert("No matches found. Try relaxing the search criteria or uploading more resumes.");
            }

        } catch (error) {
            console.error("Analysis/Matching failed", error);
            alert("Matching failed. See console for details.");
        } finally {
            setProcessing(false);
        }

        // 3. Trigger Webhook (Fire and Forget - Don't block UI)
        if (currentMatches.length > 0) {
            const runId = new Date().toISOString().split('T')[1].replace('Z', ''); // e.g., 14:30:05.123
            console.log(`[Run ${runId}] Triggering Webhook...`);

            // Add Run ID to payload for debugging
            const payloadMatches = currentMatches.map(m => ({ ...m, RunID: runId }));

            triggerWebhook(jdText, payloadMatches, topK)
                .then(() => console.log(`[Run ${runId}] Webhook triggered successfully`))
                .catch(err => console.error(`[Run ${runId}] Webhook trigger failed:`, err));
        }
    };

    return (
        <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
            <div className="max-w-6xl mx-auto space-y-8">

                <header className="flex items-center space-x-3 mb-8">
                    <div className="p-3 bg-blue-600 rounded-lg shadow-lg shadow-blue-500/20">
                        <Search className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1">
                        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                            HR Screening Portal
                        </h1>
                        <p className="text-slate-400 text-sm">Automated Resume Screening & Matching</p>
                    </div>
                    <button
                        onClick={async () => {
                            if (confirm("Are you sure you want to delete all resume data?")) {
                                import('../api').then(({ resetDatabase }) => {
                                    resetDatabase().then(() => {
                                        alert("Database reset!");
                                        setResumes([]);
                                        setMatchResults(null);
                                        setUploadStatus({});
                                    });
                                });
                            }
                        }}
                        className="px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-sm transition-colors"
                    >
                        Reset Config
                    </button>
                </header>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                    {/* LEFT COLUMN: UPLOADS */}
                    <div className="space-y-6">

                        {/* Resume Upload Card */}
                        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                            <h2 className="text-lg font-semibold mb-4 flex items-center">
                                <FileUp className="w-5 h-5 mr-2 text-blue-400" />
                                Resume Upload
                            </h2>

                            <div className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center transition-colors hover:border-blue-500 hover:bg-slate-700/30 relative">
                                <input
                                    type="file"
                                    multiple
                                    accept=".pdf,.docx,.doc"
                                    onChange={handleResumeUpload}
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                />
                                <div className="pointer-events-none">
                                    <Upload className="w-10 h-10 text-slate-400 mx-auto mb-3" />
                                    <p className="text-slate-300 font-medium">Drop resumes here or click to browse</p>
                                    <p className="text-slate-500 text-sm mt-1">Supports multiple PDF, DOCX</p>
                                </div>
                            </div>

                            {/* Resume List */}
                            {resumes.length > 0 && (
                                <div className="mt-4 space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                                    {resumes.map((file, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg border border-slate-600/50 group">
                                            <div className="flex items-center min-w-0">
                                                <div className={`w-2 h-2 rounded-full mr-3 ${uploadStatus[file.name] === 'success' ? 'bg-green-400' :
                                                    uploadStatus[file.name] === 'error' ? 'bg-red-400' :
                                                        'bg-blue-400'
                                                    }`} />
                                                <span className="text-sm truncate text-slate-200">{file.name}</span>
                                            </div>
                                            <button
                                                onClick={() => removeResume(idx)}
                                                className="p-1 hover:bg-slate-600 rounded-full text-slate-400 hover:text-red-400 transition-colors"
                                            >
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* RIGHT COLUMN: JD & ACTION */}
                    <div className="space-y-6">

                        {/* RIGHT COLUMN: JOB DESCRIPTION */}
                        <div className="flex flex-col bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-6">
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-xl font-semibold text-white flex items-center">
                                    <FileText className="w-5 h-5 mr-2 text-purple-400" />
                                    Job Description
                                </h2>
                                <div className="flex bg-slate-700/50 rounded-lg p-1">
                                    <button
                                        onClick={() => setJdMode('text')}
                                        className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${jdMode === 'text' ? 'bg-purple-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'
                                            }`}
                                    >
                                        Write
                                    </button>
                                    <button
                                        onClick={() => setJdMode('file')}
                                        className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${jdMode === 'file' ? 'bg-purple-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'
                                            }`}
                                    >
                                        Upload
                                    </button>
                                    <button
                                        onClick={() => setJdMode('agent')}
                                        className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${jdMode === 'agent' ? 'bg-purple-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'
                                            }`}
                                    >
                                        <span className="flex items-center"><Sparkles className="w-3 h-3 mr-1" /> Agent</span>
                                    </button>
                                </div>
                            </div>

                            {jdMode === 'text' && (
                                <textarea
                                    className="w-full h-64 bg-slate-900/50 border border-slate-700 rounded-lg p-4 text-slate-300 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none font-mono text-sm leading-relaxed"
                                    placeholder="Paste job description here..."
                                    value={jdText}
                                    onChange={(e) => setJdText(e.target.value)}
                                />
                            )}

                            {jdMode === 'file' && (
                                <div className="h-64 bg-slate-900/50 border border-dashed border-slate-700 rounded-lg flex flex-col items-center justify-center text-slate-400">
                                    <p>File upload not implemented yet in UI demo</p>
                                    <button onClick={() => setJdMode('text')} className="text-purple-400 text-sm mt-2 hover:underline">
                                        Switch to Text
                                    </button>
                                </div>
                            )}

                            {jdMode === 'agent' && (
                                <div className="h-64 bg-slate-900/50 border border-slate-700 rounded-lg p-4 space-y-3">
                                    <input
                                        type="text"
                                        placeholder="Role (e.g. Senior Python Developer)"
                                        className="w-full bg-slate-800 border-slate-600 rounded p-2 text-white text-sm"
                                        value={jdAgentInput.role}
                                        onChange={(e) => setJdAgentInput({ ...jdAgentInput, role: e.target.value })}
                                    />
                                    <input
                                        type="text"
                                        placeholder="Experience (e.g. 5+ years)"
                                        className="w-full bg-slate-800 border-slate-600 rounded p-2 text-white text-sm"
                                        value={jdAgentInput.exp}
                                        onChange={(e) => setJdAgentInput({ ...jdAgentInput, exp: e.target.value })}
                                    />
                                    <textarea
                                        placeholder="Must-Have Skills (e.g. FastAPI, AWS, Docker)"
                                        className="w-full h-20 bg-slate-800 border-slate-600 rounded p-2 text-white text-sm resize-none"
                                        value={jdAgentInput.skills}
                                        onChange={(e) => setJdAgentInput({ ...jdAgentInput, skills: e.target.value })}
                                    />
                                    <button
                                        onClick={handleGenerateJD}
                                        disabled={isGeneratingJD}
                                        className="w-full py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-medium rounded-lg hover:shadow-lg disabled:opacity-50 flex items-center justify-center"
                                    >
                                        {isGeneratingJD ? <Loader2 className="animate-spin w-4 h-4 mr-2" /> : <Sparkles className="w-4 h-4 mr-2" />}
                                        Generate JD
                                    </button>
                                </div>
                            )}

                            {/* Slider Control */}
                            <div className="mt-4 pt-4 border-t border-slate-700">
                                <label className="flex items-center justify-between text-slate-300 text-sm font-medium mb-2">
                                    <span className="flex items-center"><Sliders className="w-4 h-4 mr-2" /> Candidate Shortlist Limit</span>
                                    <span className="bg-slate-700 px-2 py-0.5 rounded text-xs">{topK} candidates</span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="20"
                                    value={topK}
                                    onChange={(e) => setTopK(parseInt(e.target.value))}
                                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                                />
                            </div>
                        </div>

                        {/* Action Area */}
                        <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm">
                            <button
                                onClick={startScreening}
                                disabled={processing || resumes.length === 0 || !jdText}
                                className={`w-full py-3 rounded-xl font-bold text-lg shadow-lg flex items-center justify-center transition-all ${processing
                                    ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                                    : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white hover:shadow-blue-500/25 active:scale-[0.98]'
                                    }`}
                            >
                                {processing ? (
                                    <>
                                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                        Processing...
                                    </>
                                ) : (
                                    "Start Screening"
                                )}
                            </button>

                            {matchResults && (
                                <div className="mt-4 p-3 bg-green-500/10 border border-green-500/20 rounded-lg flex items-center justify-center text-green-400 font-medium animate-in fade-in slide-in-from-top-2 text-sm">
                                    <Check className="w-4 h-4 mr-2" />
                                    Screening Completed! Results sent to Webhook.
                                </div>
                            )}
                        </div>

                    </div>
                </div>

                {/* RESULTS TABLE - Moved outside of columns for full width and no overlap */}
                {matchResults && matchResults.length > 0 && (
                    <div ref={resultsRef} className="mt-16 bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden backdrop-blur-sm relative z-20 animate-in fade-in slide-in-from-bottom-8 shadow-xl">
                        <div className="p-6 border-b border-slate-700">
                            <h2 className="text-xl font-semibold text-white flex items-center">
                                <Sparkles className="w-5 h-5 mr-2 text-purple-400" />
                                Top Candidates
                            </h2>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="bg-slate-700/50 text-slate-300 text-sm uppercase tracking-wider">
                                        <th className="p-4 font-medium">Rank</th>
                                        <th className="p-4 font-medium">Candidate</th>
                                        <th className="p-4 font-medium">Match %</th>
                                        <th className="p-4 font-medium">Contact</th>
                                        <th className="p-4 font-medium">Education</th>
                                        <th className="p-4 font-medium">Skills</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-700 text-sm text-slate-300">
                                    {matchResults.map((candidate, idx) => (
                                        <tr key={idx} className="hover:bg-slate-700/30 transition-colors">
                                            <td className="p-4 font-bold text-slate-500">#{idx + 1}</td>
                                            <td className="p-4">
                                                <div className="font-medium text-white">{candidate.Name}</div>
                                                <div className="text-xs text-slate-500 mt-1">{candidate.File}</div>
                                            </td>
                                            <td className="p-4">
                                                <div className="flex items-center">
                                                    <span className={`text-lg font-bold mr-2 ${candidate.MatchScore > 0.7 ? 'text-green-400' : candidate.MatchScore > 0.4 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                        {(candidate.MatchScore * 100).toFixed(2)}%
                                                    </span>
                                                    <div className="w-16 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                                        <div
                                                            className={`h-full rounded-full ${candidate.MatchScore > 0.7 ? 'bg-green-500' : candidate.MatchScore > 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                                            style={{ width: `${candidate.MatchScore * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="p-4 space-y-1">
                                                <div className="flex items-center text-xs">
                                                    <span className="opacity-70 w-12">Email:</span>
                                                    <a href={`mailto:${candidate.Email}`} className="text-blue-400 hover:underline truncate max-w-[150px]">{candidate.Email || "-"}</a>
                                                </div>
                                                <div className="flex items-center text-xs">
                                                    <span className="opacity-70 w-12">Phone:</span>
                                                    <span>{candidate.Phone || "-"}</span>
                                                </div>
                                            </td>
                                            <td className="p-4 max-w-xs truncate" title={candidate.Education}>
                                                {candidate.Education || "-"}
                                            </td>
                                            <td className="p-4 max-w-xs">
                                                <div className="flex flex-wrap gap-1">
                                                    {candidate.Skills && candidate.Skills.split(',').slice(0, 3).map((skill, si) => (
                                                        <span key={si} className="px-2 py-0.5 bg-slate-700 rounded text-xs border border-slate-600">
                                                            {skill.trim()}
                                                        </span>
                                                    ))}
                                                    {candidate.Skills && candidate.Skills.split(',').length > 3 && (
                                                        <span className="px-2 py-0.5 bg-slate-700/50 rounded text-xs text-slate-500">
                                                            +{candidate.Skills.split(',').length - 3}
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

            </div>
        </div>
    );
};

export default HRScreening;
