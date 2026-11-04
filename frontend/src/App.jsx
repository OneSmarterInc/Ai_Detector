import {useEffect,useRef,useState} from 'react';

function Icon({name,...props}) {
  const paths={file:<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/></>,plus:<path d="M12 5v14M5 12h14"/>,upload:<><path d="M12 16V3m-5 5 5-5 5 5M4 16v4h16v-4"/></>,close:<path d="m6 6 12 12M6 18 18 6"/>,check:<path d="m5 12 4 4L19 6"/>,info:<><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></>};
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]||paths.file}</svg>;
}
const formatSize=n=>n>=1048576?`${(n/1048576).toFixed(1)} MB`:`${Math.max(1,Math.ceil(n/1024))} KB`;
const active=job=>job&&['queued','running'].includes(job.status);

async function request(url,options={}) {
  const response=await fetch(url,options);
  let body;try {body=await response.json();} catch {throw new Error(`The request could not finish (${response.status}). Check the file limits and try again.`);}
  if(!response.ok)throw new Error(body.error||`Request failed (${response.status}).`);
  return body;
}

function FileResult({result,jobId}) {
  const detection=result.text?.ai_detection;
  const share=result.breakdown;
  const estimated=detection?.status==='estimated';
  const label=estimated?(detection.label==='Leans AI-generated'?'Looks AI-written':detection.label==='Leans human-written'?'Looks human-written':'Not sure'):'AI writing not checked';
  const explanation=estimated?(label==='Not sure'?'The model cannot give a clear answer. Some writing patterns are ambiguous or different sections disagree.':label==='Looks AI-written'?'The writing resembles AI examples. This does not prove that AI wrote it.':'The writing resembles human examples. The detector can still miss AI use.'):(detection?.reason||(result.images?.length?'Pictures receive file and pattern checks. This tool does not judge whether an image was AI-generated.':result.error||'No readable prose was available.'));
  const issues=result.issues||[];
  return <article className="result" aria-label={`Result for ${result.file}`}>
    <header className="result-heading"><div className="file-title"><Icon name="file"/><h2>{result.file}</h2></div><span className={`status ${result.status==='complete'?'good':'attention'}`}>{result.status==='failed'?'Could not read file':result.status==='partial'?'Partly checked':'Checks finished'}</span></header>
    <div className="verdict"><h3>{label}</h3><p>{explanation}</p></div>
    {share&&<section className="share" aria-label="Percentage of checked text">
      <div className="share-title"><span><strong className="percentage">{share.ai_like}%</strong> <span>of checked text flagged <strong>AI-like</strong></span></span><span className="estimate-tag">Estimate</span></div>
      <div className="share-bar" role="img" aria-label={`${share.ai_like}% AI-like, ${share.human_like}% human-like, ${share.uncertain}% uncertain`}>
        <span className="ai" style={{width:`${share.ai_like}%`}}/><span className="human" style={{width:`${share.human_like}%`}}/><span className="unknown" style={{width:`${share.uncertain}%`}}/>
      </div>
      <ul className="legend"><li><i className="ai"/>{share.ai_like}% AI-like</li><li><i className="human"/>{share.human_like}% human-like</li><li><i className="unknown"/>{share.uncertain}% uncertain</li></ul>
      <p className="small">Based on the length of checked sections. This is not the true percentage of words written by AI. A whole section is grouped by its model signal.</p>
    </section>}
    {estimated&&<div className={`coverage ${share?.sampled?'attention':''}`}><Icon name="info"/><div><strong>{share?.sampled?'Only part of this document was scored.':'All text prepared for this check was scored.'}</strong><p>Checked {detection.passages_checked} of {detection.total_passages} sections · {detection.words_in_checked_text?.toLocaleString()} words in the considered text.</p>{detection.notes?.slice(1).map((note,i)=><p key={i}>{note}</p>)}</div></div>}
    {issues.length>0&&<div className="issues"><strong>What could not be fully checked</strong><ul>{issues.map((issue,i)=><li key={i}>{issue}</li>)}</ul></div>}
    {result.text&&<section className="file-checks"><h3>Other file checks</h3><dl><div><dt>Unusual characters</dt><dd>{result.text.unusual_character_count??0}</dd></div><div><dt>Mixed-alphabet words</dt><dd>{result.text.mixed_alphabet_word_count??0}</dd></div></dl><p className="small">These clues can have ordinary explanations. They do not prove AI use.</p></section>}
    {estimated&&<details><summary>See section scores and model details</summary><p className="small">{detection.model}. Model signal: {detection.ai_pattern_score} / 100. This signal is not a probability of authorship.</p><div className="table-scroll"><table><thead><tr><th>Section</th><th>AI-pattern score</th><th>Beginning of text</th></tr></thead><tbody>{detection.passages.map(p=><tr key={p.passage_number}><td>{p.passage_number}</td><td>{p.ai_pattern_score} / 100</td><td>{p.text_excerpt}</td></tr>)}</tbody></table></div></details>}
    {result.images?.length>0&&<details className="image-details"><summary>See image checks · {result.images.length} image{result.images.length===1?'':'s'}</summary><p className="small">These are exploratory pattern views, not evidence of an AI watermark.</p>{result.images.map((picture,i)=><section key={i} className="image-group"><h4>{picture.source}</h4>{picture.analysis_note&&<p>{picture.analysis_note}</p>}{picture.frame_note&&<p>{picture.frame_note}</p>}<div className="pictures">{picture.visuals.map((v,k)=><figure key={k}><img loading="lazy" alt={v.caption} src={`/api/jobs/${jobId}/assets/${encodeURIComponent(v.file.split('/').pop())}`}/><figcaption>{v.caption}</figcaption></figure>)}</div></section>)}</details>}
    <details><summary>See file metadata and technical details</summary><pre>{JSON.stringify(result,null,2)}</pre></details>
  </article>;
}

export default function App() {
  const [info,setInfo]=useState(null),[error,setError]=useState(''),[files,setFiles]=useState([]),[text,setText]=useState(''),[mode,setMode]=useState('files');
  const [job,setJob]=useState(null),[history,setHistory]=useState([]),[page,setPage]=useState('scan'),[sending,setSending]=useState(false),[dragging,setDragging]=useState(false),[notice,setNotice]=useState('');
  const filePicker=useRef(null),folderPicker=useRef(null),pollFailures=useRef(0);
  const busy=sending||active(job);
  const refresh=()=>request('/api/jobs/').then(data=>setHistory(data.jobs));
  useEffect(()=>{let live=true;request('/api/info/').then(data=>{if(live)setInfo(data);}).catch(e=>{if(live)setError(e.message);});refresh().catch(e=>setError(e.message));return()=>{live=false;};},[]);
  useEffect(()=>{
    if(!active(job))return;
    let cancelled=false,timer;
    const poll=async()=>{try {const next=await request(`/api/jobs/${job.id}/`);if(cancelled)return;pollFailures.current=0;setJob(next);if(!active(next))await refresh();}catch(e){if(!cancelled){pollFailures.current++;setError('Could not refresh the scan. Check that the local server is still running.');}}finally {if(!cancelled)timer=setTimeout(poll,1500);}};
    timer=setTimeout(poll,1000);return()=>{cancelled=true;clearTimeout(timer);};
  },[job?.id,job?.status]);
  function addFiles(incoming,folder=false){
    if(busy||!info)return;
    setError('');setNotice('');
    const all=Array.from(incoming);const supported=all.filter(f=>info.extensions.includes('.'+f.name.split('.').pop().toLowerCase()));
    if(supported.length!==all.length){if(!folder){setError('Unsupported file type. Open File limits to see the supported formats.');return;}setNotice(`${all.length-supported.length} unsupported file(s) skipped.`);}
    const merged=[...files];for(const f of supported)if(!merged.some(x=>x.name===f.name&&x.size===f.size&&x.lastModified===f.lastModified))merged.push(f);
    if(merged.length>info.max_files){setError('Choose up to 10 files per batch. For a folder, select a smaller group of files.');return;}
    if(merged.some(f=>f.size>info.max_file_bytes)||merged.reduce((n,f)=>n+f.size,0)>info.max_batch_bytes){setError('Use files up to 100 MB each and 500 MB per batch.');return;}
    setFiles(merged);
  }
  async function scan(event){event.preventDefault();if(!info||busy)return;setError('');setSending(true);const body=new FormData();if(mode==='files')files.forEach(f=>body.append('files',f));else body.append('text',text);try {const next=await request('/api/jobs/',{method:'POST',headers:{'X-CSRFToken':info.csrf_token},body});setJob(next);setPage('scan');await refresh();}catch(e){setError(e.message);}finally{setSending(false);}}
  async function openJob(id){setError('');try{setJob(await request(`/api/jobs/${id}/`));setPage('scan');}catch(e){setError(e.message);}}
  async function removeReport(){if(!job||active(job))return;setError('');try{await request(`/api/jobs/${job.id}/`,{method:'DELETE',headers:{'X-CSRFToken':info.csrf_token}});setJob(null);await refresh();setNotice('Report and uploaded copies deleted. Your original files were not changed.');}catch(e){setError(e.message);}}
  function newScan(){setPage('scan');if(!active(job)){setJob(null);setFiles([]);setText('');setNotice('');setError('');}}
  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className="sidebar"><a className="brand" href="/" aria-label="AI File Inspector home"><span className="brand-mark"><Icon name="file"/></span><span>AI File<br/><strong>Inspector</strong></span></a>
      <nav aria-label="Main navigation"><button className={page==='scan'?'nav-button selected':'nav-button'} onClick={newScan}><Icon name="plus"/>New scan</button><button className={page==='limits'?'nav-button selected':'nav-button'} onClick={()=>setPage('limits')}><Icon name="info"/>File limits</button></nav>
      <section className="history"><h2>Recent scans</h2>{history.length===0?<p className="small">Your reports will appear here.</p>:<ul>{history.map(h=><li key={h.id}><button className={job?.id===h.id?'history-button current':'history-button'} onClick={()=>openJob(h.id)}><span>{h.files[0]?.name||'New scan'}{h.files.length>1?` +${h.files.length-1}`:''}</span><small>{h.status==='complete'?'Ready':h.status==='failed'?'Stopped':h.status==='queued'?'Waiting':'Checking'}</small></button></li>)}</ul>}</section>
      <div className="local-note"><span className="local-dot"/>Runs on this computer<p>Files stay in your local portal. No external AI API.</p></div>
    </aside>
    <main id="main"><header className="topline"><span>Writing & file analysis</span><span className="model-status">{info?(info.model_ready?'Gradient model ready':'Model setup needed'):'Connecting to local server…'}</span></header>
      {history.length>0&&<div className="mobile-history"><label htmlFor="recent-scan">Recent scans</label><select id="recent-scan" value={job?.id||''} onChange={e=>{if(e.target.value)openJob(e.target.value);}}><option value="">Open a saved report…</option>{history.map(h=><option key={h.id} value={h.id}>{h.files[0]?.name||'New scan'} · {h.status}</option>)}</select></div>}
      {error&&<div role="alert" className="error"><strong>Something needs attention</strong><p>{error}</p><button className="text-button" onClick={()=>setError('')}>Dismiss</button></div>}
      {notice&&<p role="status" className="notice">{notice}</p>}
      {page==='limits'?<section className="limits"><h1>File types & limits</h1><p>Opening a file does not mean all its contents can be scored.</p><div className="web-limits"><strong>Web portal upload limits</strong><p>Up to 10 files per batch · 100 MB per file · 500 MB combined. Pasted text: up to 200,000 characters.</p></div><pre>{info?.limits_text||'Loading the guide…'}</pre><section className="method"><h2>Can we improve the model weights?</h2><p>Yes, through fine-tuning on correctly labelled human and AI examples. Random weight changes do not improve accuracy. Training must be followed by testing on separate examples that were not used to train or choose the model.</p><p>This portal uses the verified Gradient model. No new weights have been trained for this interface.</p></section></section>:<>
      <header className="page-heading"><h1>{job?'Your file report':'Understand your writing.'}</h1><p>{job?'Clear results, with the details you need to interpret them.':'Check a document or paste text. Get a writing estimate you can understand.'}</p></header>
      {!job&&<div className="workspace"><form onSubmit={scan} className="upload-panel">
        <div className="mode-switch" role="group" aria-label="Input method"><button type="button" aria-pressed={mode==='files'} onClick={()=>setMode('files')} disabled={busy}>Upload files</button><button type="button" aria-pressed={mode==='text'} onClick={()=>setMode('text')} disabled={busy}>Paste text</button></div>
        {mode==='files'?<><div className={`dropzone ${dragging?'dragging':''}`} onDragOver={e=>{e.preventDefault();setDragging(true);}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);addFiles(e.dataTransfer.files);}}><Icon name="upload" width="32" height="32"/><h2>Bring your files here</h2><p>Drop files here, or choose them from your computer.</p><div className="picker-actions"><button className="secondary" type="button" disabled={!info||busy} onClick={()=>filePicker.current.click()}>Choose files</button><button className="text-button" type="button" disabled={!info||busy} onClick={()=>folderPicker.current.click()}>Choose folder</button></div><span className="small">PDF, DOCX, text and pictures · up to 100 MB each</span></div><input ref={filePicker} type="file" multiple accept={info?.extensions.join(',')} hidden onChange={e=>{addFiles(e.target.files);e.target.value='';}}/><input ref={folderPicker} type="file" multiple webkitdirectory="" hidden onChange={e=>{addFiles(e.target.files,true);e.target.value='';}}/>
        {files.length>0&&<ul className="selected-files">{files.map((file,i)=><li key={`${file.name}-${i}`}><Icon name="file"/><span>{file.name}<small>{formatSize(file.size)}</small></span><button type="button" className="icon-button" aria-label={`Remove ${file.name}`} disabled={busy} onClick={()=>setFiles(files.filter((_,index)=>index!==i))}><Icon name="close"/></button></li>)}</ul>}</>:<><label className="textarea-label" htmlFor="writing">Your English writing</label><textarea id="writing" value={text} onChange={e=>setText(e.target.value)} maxLength={200000} placeholder="Paste at least 100 words of English prose…" disabled={busy}/><p className="input-count">{text.trim()?text.trim().split(/\s+/).length:0} words (approx.) · {text.length.toLocaleString()} / 200,000 characters</p></>}
        <div className="submit-row"><button type="submit" className="primary" disabled={!info||busy||(mode==='files'?files.length===0:!text.trim())}>{sending?'Uploading…':'Check writing'}<Icon name="check"/></button><span className="small">At least 100 English words for a writing estimate.</span></div>
      </form><aside className="explain"><h2>A percentage with context.</h2><p>The report shows the share of checked text in sections flagged as AI-like, human-like or uncertain.</p><p>It is an estimate of writing patterns—not a measurement of who wrote each word.</p><div className="explain-rule"/><h3>Know what was checked</h3><p>Long documents may be sampled. You will see the coverage next to your result.</p><h3>Pictures work differently</h3><p>Image uploads get file and pattern checks, not an AI-image verdict.</p><button className="text-button" onClick={()=>setPage('limits')}>Read the file limits</button></aside></div>}
      {job&&<section aria-label="Scan report"><div className={`scan-progress ${active(job)?'working':''}`} role="status"><div><strong>{job.status==='complete'?'Scan finished':job.status==='failed'?'Scan stopped':job.status==='queued'?'Your scan is queued':'Checking your files'}</strong><p>{job.error||job.progress}</p>{active(job)&&<p className="small">The first file may take longer while the model loads. You can leave this page open.</p>}</div>{active(job)&&<progress aria-label="Scanning"/>}</div>
        {job.results?.map((r,i)=><FileResult key={`${job.id}-${i}`} result={r} jobId={job.id}/>)}
        {!active(job)&&<div className="report-actions"><button className="primary" onClick={newScan}><Icon name="plus"/>Check another file</button><a className="secondary" href={`/api/jobs/${job.id}/report/`} download>Download report JSON</a><button className="text-button danger" onClick={removeReport}>Delete this scan</button></div>}
      </section>}
      <footer>AI estimates can be wrong. Review the original writing before making a decision.</footer>
      </>}
    </main>
  </div>;
}
