import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { transitions } from "./stages.mjs";
import "./style.css";

const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

function Onboarding({ item, staff, request, post, onError }) {
  const [tasks, setTasks] = useState([]);
  const path = `/applications/${item.id}/onboarding`;
  async function refresh() {
    setTasks(await request(path));
  }
  return <section>
    <button onClick={() => refresh().catch(err => onError(err.message))}>Load onboarding tasks</button>
    <ul>{tasks.map(task => <li key={task.id}>{task.task_type} · {task.status}
      {(staff ? task.status === "submitted" : task.status === "pending") &&
        <button onClick={async () => {
          try {
            await post(`${path}/${task.id}`, {});
            await refresh();
          } catch (err) {
            onError(err.message);
          }
        }}>{staff ? "Verify" : "Mark submitted"}</button>}
    </li>)}</ul>
  </section>;
}

function Workspace() {
  const [token, setToken] = useState(sessionStorage.getItem("token") || "");
  const [profile, setProfile] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [interviewers, setInterviewers] = useState([]);
  const [assigned, setAssigned] = useState([]);
  const [applications, setApplications] = useState([]);
  const [register, setRegister] = useState(false);
  const [error, setError] = useState("");
  const staff = ["admin", "hr"].includes(profile?.role);

  async function request(path, options = {}) {
    const response = await fetch(base + path, {
      ...options,
      headers: {
        ...(token && { Authorization: "Bearer " + token }),
        ...options.headers,
      },
    });
    const body = await response.json();
    if (!response.ok) {
      throw Error(typeof body.detail === "string" ? body.detail : "Check the submitted fields.");
    }
    return body;
  }

  useEffect(() => {
    let active = true;
    if (!token) return;
    async function refresh() {
      try {
        const user = await request("/auth/me");
        const openJobs = await request("/jobs");
        const rows = user.role === "interviewer" ? [] : await request("/applications");
        const panel = ["admin", "hr"].includes(user.role) ? await request("/interviewers") : [];
        const panelAssignments = user.role === "interviewer" ? await request("/interviews/assigned") : [];
        if (active) {
          setInterviewers(panel);
          setAssigned(panelAssignments);
          setProfile(user);
          setJobs(openJobs);
          setApplications(rows);
        }
      } catch (err) {
        if (active) setError(err.message);
      }
    }
    refresh();
    const timer = setInterval(refresh, 4000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [token]);

  const post = (path, data) => request(path, {
    method: "POST", body: JSON.stringify(data), headers: {"Content-Type": "application/json"},
  });
  async function submit(event, action) {
    event.preventDefault();
    setError("");
    try {
      await action(new FormData(event.currentTarget));
    } catch (err) {
      setError(err.message);
    }
  }
  function logout() {
    setToken("");
    setProfile(null);
    setError("");
    sessionStorage.removeItem("token");
  }

  return <div className="workspace">
    <header><h1>Recruitment workspace</h1>{token && <button onClick={logout}>Sign out</button>}</header>
    {error && <p role="alert">{error}</p>}
    {!token ? <form onSubmit={event => submit(event, async data => {
      const session = await post(register ? "/auth/register" : "/auth/login", Object.fromEntries(data));
      sessionStorage.setItem("token", session.access_token);
      setToken(session.access_token);
    })}>
      <h2>{register ? "Candidate registration" : "Sign in"}</h2>
      {register && <label>Full name<input name="full_name" required /></label>}
      <label>Email<input type="email" name="email" required /></label>
      <label>Password<input type="password" name="password" minLength={8} required /></label>
      <button>{register ? "Register" : "Sign in"}</button>
      <button type="button" onClick={() => setRegister(!register)}>
        {register ? "Use existing account" : "Create candidate account"}
      </button>
    </form> : profile && <>
      {staff && <form onSubmit={event => submit(event, async data => {
        const job = await post("/jobs", {
          title: data.get("title"), description: data.get("description"),
          required_skills: data.get("skills").split(",").map(skill => skill.trim()).filter(Boolean),
        });
        setJobs(previous => [job, ...previous]);
      })}>
        <h2>Create job</h2>
        <label>Job title<input name="title" required /></label>
        <label>Job description<textarea name="description" required /></label>
        <label>Required skills<input name="skills" placeholder="Python, PostgreSQL" /></label>
        <button>Create job</button>
      </form>}
      {profile.role !== "interviewer" && <form onSubmit={event => submit(event, async data => {
        await request("/applications", {method: "POST", body: data});
        setApplications(await request("/applications"));
      })}>
        <h2>Upload resume</h2>
        <label>Job<select name="job_id" required>{jobs.map(job => <option key={job.id} value={job.id}>{job.title}</option>)}</select></label>
        <label>Candidate name<input name="full_name" defaultValue={staff ? "" : profile.full_name} required /></label>
        {staff && <label>Candidate email<input name="email" type="email" required /></label>}
        <label>Resume<input type="file" name="file" accept=".pdf,.docx" required /></label>
        <button disabled={!jobs.length}>Queue screening</button>
      </form>}
      {profile.role === "candidate" && <form onSubmit={event => submit(event, async data => {
        const id = data.get("application_id");
        data.delete("application_id");
        await request("/applications/" + id + "/claim", {method:"POST", body:data});
        setApplications(await request("/applications"));
      })}>
        <h2>Claim invitation</h2>
        <label>Application ID<input type="number" min={1} name="application_id" required /></label>
        <label>Invitation code<input name="code" required /></label>
        <button>Claim application</button>
      </form>}
      {profile.role === "interviewer" && <section>
        <h2>Assigned interviews</h2>
        {assigned.map(interview => <article key={interview.id}>
          <h3>{interview.full_name} · {interview.title}</h3>
          <p>{new Date(interview.scheduled_start).toLocaleString()}</p>
          {!interview.feedback_submitted_at && <form onSubmit={event => submit(event, async data => {
            await post(`/interviews/${interview.application_id}/feedback`, Object.fromEntries(data));
            setAssigned(await request("/interviews/assigned"));
          })}>
            <label>Feedback<textarea name="comments" required /></label>
            <label>Recommendation<select name="recommendation"><option value="select">Select</option><option value="reject">Reject</option><option value="hold">Hold</option></select></label>
            <button>Submit feedback</button>
          </form>}
        </article>)}
      </section>}
      {profile.role !== "interviewer" && <h2>Applications</h2>}
      {profile.role !== "interviewer" && !applications.length && <p>No applications yet.</p>}
      {applications.map(item => <article key={item.id}>
        <h3>{item.full_name} · {item.title}</h3>
        <p>{item.status.replaceAll("_", " ")} · {item.match_score == null ? "Waiting for score" : `Score ${Math.round(item.match_score * 100)}%`}</p>
        {item.status === "onboarding" && <Onboarding item={item} staff={staff} request={request} post={post} onError={setError} />}
        {staff && item.status === "applied" && <button onClick={() => post(`/applications/${item.id}/retry`, {}).catch(err => setError(err.message))}>Retry screening</button>}
        {staff && transitions(item.status, profile.role).length > 0 && <form onSubmit={event => submit(event, async data => {
          const value = Object.fromEntries(data);
          await post(`/applications/${item.id}/stage`, {
            target: value.target, scheduled_start: value.start ? new Date(value.start).toISOString() : null,
            interviewer_id: value.interviewer_id ? Number(value.interviewer_id) : null,
            feedback_comments: value.notes, offer_text: value.notes,
            checklist: value.notes.split("\n").filter(Boolean),
          });
          setApplications(await request("/applications"));
        })}>
          <label>Advance stage<select name="target">{transitions(item.status, profile.role).map(stage => <option key={stage}>{stage}</option>)}</select></label>
          <label>Interview time<input name="start" type="datetime-local" /></label>
          <label>Interviewer<select name="interviewer_id"><option value="">Choose an interviewer</option>{interviewers.map(person => <option key={person.id} value={person.id}>{person.full_name}</option>)}</select></label>
          <label>Feedback, offer text or checklist<textarea name="notes" /></label>
          <button>Save stage</button>
        </form>}
      </article>)}
    </>}
  </div>;
}

createRoot(document.getElementById("root")).render(<Workspace />);
