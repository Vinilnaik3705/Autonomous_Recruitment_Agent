import React,{useState,useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {transitions} from './stages.mjs';
import './style.css';

const base=(import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/,'');
function Run({run,role,act}){
  const options=transitions(run.stage,role);
  const [target,setTarget]=useState(options[0]);
  const [note,setNote]=useState('');
  const [start,setStart]=useState('');
  const pending=run.actions?.some(a=>['book','offer','reschedule'].includes(a.kind)&&['pending','sending','uncertain'].includes(a.state));
  return <article><h3>{run.filename || 'Application'} <small>#{run.id}</small></h3>
    <p>{run.email} · {run.stage.replaceAll('_',' ')} {run.screening_state && ' / '+run.screening_state}</p>
    {run.interview_at && <p>Interview · {new Date(run.interview_at).toLocaleString()}</p>}
    {run.checklist?.length>0 && <ul>{run.checklist.map((s,i)=><li key={i}>{s}</li>)}</ul>}
    {run.result && <details><summary>Screening result</summary><pre>{JSON.stringify(run.result,null,2)}</pre></details>}
    {run.actions?.length>0 && <p>{run.actions.map(a=>a.kind+' · '+a.state).join(' | ')}</p>}
    {run.screening_state==='failed' && <button onClick={()=>act('/runs/'+run.id+'/retry',{})}>Retry screening</button>}
    {role!=='student' && options.length>0 && !pending && <form onSubmit={e=>{e.preventDefault();act('/runs/'+run.id+'/stage',{target,note,start:target==='interview_scheduled'?new Date(start).toISOString():null,checklist:target==='onboarding'?note.split('\n').filter(Boolean):[]});}}>
      <label>Next stage<select value={target} onChange={e=>setTarget(e.target.value)}>{options.map(t=><option key={t} value={t}>{t.replaceAll('_',' ')}</option>)}</select></label>
      {target==='interview_scheduled' && <label>Interview start (local time)<input type="datetime-local" required value={start} onChange={e=>setStart(e.target.value)}/></label>}
      {['feedback_received','offer_sent','onboarding','complete'].includes(target) && <label>{{feedback_received:'Interview feedback',offer_sent:'Offer terms sent to candidate',onboarding:'Checklist (one item per line)',complete:'Completion record'}[target]}<textarea required value={note} onChange={e=>setNote(e.target.value)}/></label>}
      <button>Confirm {target?.replaceAll('_',' ')}</button></form>}
    </article>;
}
function App(){
  const [token,setToken]=useState(sessionStorage.getItem('token')||'');
  const [user,setUser]=useState(null),[runs,setRuns]=useState([]),[error,setError]=useState(''),[signup,setSignup]=useState(false);
  const [revision,setRevision]=useState(0),[busy,setBusy]=useState(false);
  async function request(path,options={}){
    const res=await fetch(base+path,{...options,headers:{...(token&&{Authorization:'Bearer '+token}),...options.headers}});
    const data=await res.json();
    if(!res.ok) throw Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));
    return data;
  }
  useEffect(()=>{
    let active=true;
    if(!token) return;
    async function load(){
      try{const profile=await request('/auth/me');const rows=await request(profile.role==='student'?'/applications':'/runs');
        if(active){setUser(profile);setRuns(rows);}
      }catch(e){if(active)setError(e.message);}
    }
    load();const id=setInterval(load,15000);return ()=>{active=false;clearInterval(id);};
  },[token,revision]);
  async function execute(fn){
    if(busy)return;
    setBusy(true);setError('');try{await fn();setRevision(n=>n+1);}catch(e){setError(e.message);}finally{setBusy(false);}
  }
  function post(path,data){return request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
  function logout(){sessionStorage.removeItem('token');setToken('');setUser(null);setRuns([]);setError('');}
  return <><header><h1>Recruitment workspace</h1>{token && <button onClick={logout}>Sign out</button>}</header>
    {error && <p role="alert">{error}</p>}<fieldset disabled={busy}>
    {!token ? <form onSubmit={e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.currentTarget));execute(async()=>{
      const auth=await post(signup?'/auth/register':'/auth/login',data);sessionStorage.setItem('token',auth.access_token);setToken(auth.access_token);
    });}}><h2>{signup?'Candidate registration':'Sign in'}</h2>{signup && <label>Name<input name="username" required/></label>}
    <label>Email<input type="email" name="email" required/></label><label>Password<input name="password" type="password" required minLength={signup?12:1}/></label><button>{signup?'Register':'Sign in'}</button>
    <button type="button" onClick={()=>setSignup(!signup)}>{signup?'Use existing account':'Create candidate account'}</button></form>
    : user && <><h2>{user.username} · {user.role}</h2>{user.role==='student'?
      <form onSubmit={e=>{e.preventDefault();const body=new FormData(e.currentTarget);execute(()=>request('/applications/claim',{method:'POST',body}));}}>
        <label>Invitation code<input name="code" required/></label><button>Link application</button></form>
      : <form onSubmit={e=>{e.preventDefault();const form=e.currentTarget;const body=new FormData(form);
        form.dataset.key ||= crypto.randomUUID();execute(async()=>{await request('/runs',{method:'POST',body,headers:{'Idempotency-Key':form.dataset.key}});form.reset();delete form.dataset.key;});}} onChange={e=>{delete e.currentTarget.dataset.key;}}>
      <h2>Submit for screening</h2><label>Candidate email (receives an invitation)<input type="email" required name="email"/></label>
      <label>Job description<textarea required name="job_description"/></label><label>Required skills (comma separated)<input name="required_skills"/></label>
      <label>Resume<input required type="file" accept=".pdf,.docx" name="file"/></label><button>Queue screening</button></form>}
      <h2>Applications</h2>{runs.length===0 && <p>No applications yet.</p>}{runs.map(run=><Run key={run.id+'-'+run.stage} run={run} role={user.role} act={(path,data)=>execute(()=>post(path,data))}/>)}</>}
    </fieldset></>;
}
createRoot(document.getElementById('root')).render(<App/>);
