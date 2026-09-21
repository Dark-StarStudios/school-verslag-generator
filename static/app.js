(() => {
  "use strict";
  const clone = value => JSON.parse(JSON.stringify(value));
  const STORAGE_KEY = "school-verslag/1.0/autosave";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = value => String(value ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const value = path => path.split(".").reduce((obj, key) => obj?.[key], state.report);
  const setValue = (path, next) => {
    const parts = path.split("."); let obj = state.report;
    parts.slice(0, -1).forEach(key => obj = obj[key]); obj[parts.at(-1)] = next;
  };
  const list = path => Array.isArray(value(path)) ? value(path) : [];

  const steps = [
    ["Voorblad", "Voorblad en basisgegevens", "Leg vast wie het verslag maakt en over welk examenproject het gaat."],
    ["Activiteiten", "Examenactiviteiten", "Beschrijf het resultaat, de werkzaamheden en wat je daarvoor nodig had."],
    ["Grenzen", "Grenzen en randvoorwaarden", "Maak duidelijk wat wel en niet bij het examen hoort."],
    ["Planning", "Planning", "Zet de fasen, perioden en concrete taken in een realistische volgorde."],
    ["Werkprocessen", "Verantwoording per werkproces", "Koppel je handelen en bewijs aan elk geselecteerd werkproces."],
    ["Evaluatie", "Evaluatie", "Evalueer vakinhoudelijk en persoonlijk, inclusief je volgende leerdoel."],
    ["Verklaring", "Verklaring", "Bevestig de verplichte verklaring voor je eigen werk."],
    ["Controleren", "Controleren en exporteren", "Los de laatste inhoudelijke waarschuwingen op en download je verslag."]
  ];
  const state = { report: loadAutosave(), step: 0 };

  function loadAutosave() {
    try { return {...clone(window.DEFAULT_REPORT), ...JSON.parse(localStorage.getItem(STORAGE_KEY))}; }
    catch { return clone(window.DEFAULT_REPORT); }
  }
  function saveAutosave() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.report));
    $("#saveState").textContent = "Lokaal opgeslagen";
  }
  let saveTimer;
  function scheduleSave() {
    $("#saveState").textContent = "Bezig met opslaan…";
    clearTimeout(saveTimer); saveTimer = setTimeout(saveAutosave, 250);
  }
  function field(label, path, opts = {}) {
    const {type="text", full=false, help="", placeholder="", required=false, rows=5} = opts;
    const current = value(path) ?? "";
    const control = type === "textarea"
      ? `<textarea data-path="${path}" rows="${rows}" placeholder="${escapeHtml(placeholder)}">${escapeHtml(current)}</textarea>`
      : `<input data-path="${path}" type="${type}" value="${escapeHtml(current)}" placeholder="${escapeHtml(placeholder)}">`;
    return `<div class="field ${full ? "full" : ""}"><label>${escapeHtml(label)}${required ? " *" : ""}</label>${control}${help ? `<small>${escapeHtml(help)}</small>` : ""}</div>`;
  }
  function repeatSection(title, path, placeholder, help="") {
    const rows = list(path).map((item, i) => `<div class="repeat-row"><input data-list-path="${path}" data-index="${i}" value="${escapeHtml(item)}" placeholder="${escapeHtml(placeholder)}"><button class="icon-button" data-remove-list="${path}" data-index="${i}" type="button" aria-label="Verwijderen">×</button></div>`).join("");
    return `<section class="repeat-section"><div class="repeat-head"><div><h3>${escapeHtml(title)}</h3>${help ? `<span class="hint">${escapeHtml(help)}</span>` : ""}</div><button class="add-button" data-add-list="${path}" type="button">+ toevoegen</button></div><div class="repeat-list">${rows || `<span class="hint">Nog niets toegevoegd.</span>`}</div></section>`;
  }
  function renderStep() {
    const [short, title, intro] = steps[state.step];
    $("#stepEyebrow").textContent = `STAP ${state.step + 1} VAN ${steps.length}`;
    $("#stepTitle").textContent = title; $("#stepIntro").textContent = intro;
    $("#stepContent").innerHTML = [renderCover, renderActivities, renderScope, renderPlanning, renderWorkProcesses, renderEvaluation, renderDeclaration, renderChecks][state.step]();
    $("#previousStep").disabled = state.step === 0;
    $("#nextStep").textContent = state.step === steps.length - 1 ? "Naar het begin" : "Volgende stap";
    renderNav(); bindDynamic(); renderPreview(); updateProgress();
    window.scrollTo({top: 0, behavior: "smooth"});
  }
  function renderNav() {
    $("#stepNav").innerHTML = steps.map((step, i) => `<button type="button" class="step-link ${i === state.step ? "active" : ""} ${stepComplete(i) ? "done" : ""}" data-step="${i}"><span class="index">${i + 1}</span><span>${step[0]}</span><span class="state">${stepComplete(i) ? "✓" : ""}</span></button>`).join("");
  }
  function renderCover() {
    return `<div class="field-grid">
      ${field("Titel", "project.title", {required:true, placeholder:"Bijvoorbeeld Antonis Verhuur website"})}
      ${field("Ondertitel", "project.subtitle", {placeholder:"Bijvoorbeeld Technisch examenverslag"})}
      ${field("Naam student", "student.name", {required:true})}${field("OV-nummer", "student.student_number")}
      ${field("Klas", "student.class_name", {required:true})}${field("Stagebedrijf of opdrachtgever", "student.company", {required:true})}
      ${field("Praktijkopleider", "student.practice_supervisor")}${field("BPV-begeleider", "student.bpv_supervisor")}
      ${field("Versie", "project.version", {required:true})}${field("Verslagdatum", "project.report_date", {type:"date", required:true})}
      ${field("Examennaam", "project.exam_name")}${field("Examennummer", "project.exam_number", {placeholder:"EP1"})}
      ${field("Startdatum examen", "project.start_date", {type:"date"})}${field("Einddatum examen", "project.end_date", {type:"date"})}
      ${field("Inleiding", "project.introduction", {type:"textarea", full:true, required:true, placeholder:"Wat is de aanleiding, het probleem, jouw opdracht en het doel?"})}
    </div>${repeatSection("Op te leveren producten", "project.products", "Bijvoorbeeld werkende website")}`;
  }
  function renderActivities() {
    return `${repeatSection("Wat moest ik doen?", "activities", "Concrete activiteit of resultaat", "Gebruik werkwoorden en noem alleen wat echt bij het examen hoort.")}
      ${repeatSection("Materialen en software", "resources.materials", "Bijvoorbeeld WordPress, GitHub of Figma")}
      ${repeatSection("Mensen", "resources.people", "Wie gaf feedback, testte of hielp?")}
      ${repeatSection("Middelen", "resources.means", "Computer, testdevice, hosting of toegang")}
      ${repeatSection("Kennis", "resources.knowledge", "Techniek, methode of vakkennis")}`;
  }
  function renderScope() {
    return `${repeatSection("Wat hoort wel bij het examen?", "scope.included", "Onderdeel binnen de opdracht")}
      ${repeatSection("Wat hoort niet bij het examen?", "scope.excluded", "Bewuste afbakening")}
      ${repeatSection("Wat stelt de opdrachtgever beschikbaar?", "scope.provided", "Mensen, uren, materiaal, accounts of informatie")}`;
  }
  function renderPlanning() {
    return `<div class="repeat-head"><div><h3>Projectfasen</h3><span class="hint">Perioden mogen datums of weken zijn.</span></div><button class="add-button" id="addPhase" type="button">+ fase toevoegen</button></div>` + state.report.planning.map((phase, i) => `<article class="phase-card"><div class="phase-grid">${field(`Fase ${i+1}`, `planning.${i}.phase`, {required:true})}${field("Periode", `planning.${i}.period`, {placeholder:"dd-mm-jjjj t/m dd-mm-jjjj"})}</div><div style="margin-top:14px">${repeatSection("Taken", `planning.${i}.tasks`, "Concrete taak of mijlpaal")}</div><button class="add-button" data-remove-phase="${i}" type="button">Fase verwijderen</button></article>`).join("");
  }
  function renderWorkProcesses() {
    return `<p class="hint">De criteria komen uit Web development C2024, Crebo 25604ONA1. Selecteer alleen processen waarop je wordt beoordeeld.</p>` + state.report.work_processes.map((wp, i) => `<article class="wp-card"><div class="wp-top"><div><span class="wp-code">${escapeHtml(wp.code)}</span><h3>${escapeHtml(wp.title)}</h3><span class="hint">${escapeHtml((wp.competencies || []).join(", "))}</span></div><label class="switch" aria-label="${escapeHtml(wp.code)} selecteren"><input type="checkbox" data-wp-select="${i}" ${wp.selected ? "checked" : ""}><span></span></label></div>${wp.selected ? `<details><summary>Beoordelingscriteria bekijken</summary><ul>${(wp.indicators || []).map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul></details><div class="field"><label>Mijn verantwoording *</label><textarea data-path="work_processes.${i}.accountability" rows="7" placeholder="Beschrijf situatie, jouw eigen handelingen, gemaakte keuzes, resultaat en wat je daarvan hebt geleerd.">${escapeHtml(wp.accountability || "")}</textarea><small>Schrijf in de ik-vorm en verwijs naar controleerbaar bewijs.</small></div><div style="margin-top:14px">${repeatSection("Bewijs", `work_processes.${i}.evidence`, "Bijvoorbeeld GitHub commit, screenshot, testverslag of feedback")}</div>` : ""}</article>`).join("");
  }
  function renderEvaluation() {
    return `<div class="field-grid">${field("Vakinhoudelijke evaluatie", "evaluation.professional", {type:"textarea", full:true, required:true, placeholder:"Wat wilde je leren, wat heb je geleerd, wat ging goed en wat kon beter?"})}${field("Persoonlijke evaluatie", "evaluation.personal", {type:"textarea", full:true, required:true, placeholder:"Wat heb je over samenwerken, plannen, communiceren en jezelf geleerd?"})}${field("Volgend project", "evaluation.next_project", {type:"textarea", full:true, required:true, placeholder:"Wat ga je de volgende keer concreet anders doen of verder leren?"})}</div>`;
  }
  function renderDeclaration() {
    const declaration = `Hierbij verklaar ik dat:\nHet door mij gemaakte werk zelf geschreven is en dat ik geen teksten heb overgenomen uit andere stageverslagen, scripties, overige geschriften en literatuur zonder de bron te hebben vermeld.\nDe inhoud van dit verslag komt, voor wat betreft de feiten en de verrichte werkzaamheden, geheel overeen met de werkelijkheid.\nDe beschreven door mij uitgevoerde werkzaamheden zijn daadwerkelijk door mij verricht.`;
    return `<div class="declaration">${escapeHtml(declaration)}</div><label class="check-card" style="margin-top:18px"><input type="checkbox" id="declarationAccepted" ${state.report.declaration_accepted ? "checked" : ""}><span><strong>Ik neem deze verklaring op in mijn verslag</strong><p>Controleer vóór inleveren of alle beschreven werkzaamheden echt door jou zijn uitgevoerd.</p></span></label>`;
  }
  function renderChecks() {
    const checks = qualityChecks(); const errors = checks.filter(x => !x.ok);
    return `<div>${checks.map(x => `<article class="check-card ${x.ok ? "ok" : "warn"}"><span>${x.ok ? "✓" : "!"}</span><div><strong>${escapeHtml(x.title)}</strong><p>${escapeHtml(x.message)}</p></div></article>`).join("")}</div><div class="export-grid"><button type="button" class="export-button" data-export="pdf">PDF<span>Direct inleverbaar</span></button><button type="button" class="export-button" data-export="docx">DOCX<span>Verder bewerken in Word</span></button><button type="button" class="export-button" data-export="odt">ODT<span>LibreOffice en OpenDocument</span></button></div>${errors.length ? `<p class="hint">Exporteren kan al, maar los de waarschuwingen op voor een sterker verslag.</p>` : `<p class="hint">Alle basiscontroles zijn geslaagd. Lees het verslag nog één keer zelf na.</p>`}`;
  }
  function bindDynamic() {
    $$('[data-path]').forEach(el => el.addEventListener("input", () => { setValue(el.dataset.path, el.value); scheduleSave(); renderPreview(); updateProgress(); }));
    $$('[data-list-path]').forEach(el => el.addEventListener("input", () => { const arr = list(el.dataset.listPath); arr[Number(el.dataset.index)] = el.value; scheduleSave(); renderPreview(); }));
    $$('[data-add-list]').forEach(el => el.addEventListener("click", () => { list(el.dataset.addList).push(""); scheduleSave(); renderStep(); }));
    $$('[data-remove-list]').forEach(el => el.addEventListener("click", () => { list(el.dataset.removeList).splice(Number(el.dataset.index), 1); scheduleSave(); renderStep(); }));
    $$('[data-step]').forEach(el => el.addEventListener("click", () => { state.step = Number(el.dataset.step); renderStep(); }));
    $$('[data-wp-select]').forEach(el => el.addEventListener("change", () => { state.report.work_processes[Number(el.dataset.wpSelect)].selected = el.checked; scheduleSave(); renderStep(); }));
    $$('[data-remove-phase]').forEach(el => el.addEventListener("click", () => { state.report.planning.splice(Number(el.dataset.removePhase), 1); scheduleSave(); renderStep(); }));
    $("#addPhase")?.addEventListener("click", () => { state.report.planning.push({phase:"", period:"", tasks:[]}); scheduleSave(); renderStep(); });
    $("#declarationAccepted")?.addEventListener("change", e => { state.report.declaration_accepted = e.target.checked; scheduleSave(); updateProgress(); });
    $$('[data-export]').forEach(el => el.addEventListener("click", () => exportReport(el.dataset.export, el)));
  }
  function stepComplete(i) {
    const r = state.report;
    if (i === 0) return [r.student.name,r.student.class_name,r.student.company,r.project.title,r.project.report_date,r.project.introduction].every(Boolean);
    if (i === 1) return r.activities.length > 0 && Object.values(r.resources).some(x => x.length);
    if (i === 2) return r.scope.included.length && r.scope.excluded.length && r.scope.provided.length;
    if (i === 3) return r.planning.length && r.planning.every(x => x.phase && x.tasks.length);
    if (i === 4) { const selected = r.work_processes.filter(x => x.selected); return selected.length > 0 && selected.every(x => (x.accountability || "").trim().length >= 80 && x.evidence.length); }
    if (i === 5) return Object.values(r.evaluation).every(x => (x || "").trim().length >= 80);
    if (i === 6) return r.declaration_accepted;
    return qualityChecks().every(x => x.ok);
  }
  function updateProgress() {
    const done = steps.map((_, i) => stepComplete(i)).filter(Boolean).length;
    const pct = Math.round(done / steps.length * 100);
    $("#progressLabel").textContent = `${pct}%`; $("#progressBar").style.width = `${pct}%`;
    $("#progressHint").textContent = done === steps.length ? "Klaar voor de laatste eigen controle." : `${done} van ${steps.length} onderdelen compleet.`;
    const selected = state.report.work_processes.filter(item => item.selected).length;
    $("#selectedCount").textContent = `${selected} werkprocessen geselecteerd`;
  }
  function qualityChecks() {
    const r = state.report; const selected = r.work_processes.filter(x => x.selected);
    const joined = selected.map(x => x.accountability || "").join(" ").toLowerCase();
    const future = (joined.match(/\b(zal|zullen|ga|gaan)\b/g) || []).length;
    return [
      {title:"Voorblad en inleiding", ok:stepComplete(0), message:stepComplete(0)?"De verplichte basisgegevens zijn ingevuld.":"Vul titel, naam, klas, opdrachtgever, datum en inleiding in."},
      {title:"Afbakening en planning", ok:stepComplete(2)&&stepComplete(3), message:stepComplete(2)&&stepComplete(3)?"Scope en projectfasen zijn beschreven.":"Beschrijf wat wel en niet hoort bij het examen en voeg taken per fase toe."},
      {title:"Alle geselecteerde werkprocessen verantwoord", ok:stepComplete(4), message:stepComplete(4)?"Elk werkproces heeft een toelichting en bewijs.":"Schrijf per geselecteerd werkproces minimaal een concrete toelichting en voeg bewijs toe."},
      {title:"Feitelijke formulering", ok:future < 3, message:future < 3?"De verantwoording gebruikt hoofdzakelijk gerealiseerde resultaten.":"Er staat veel toekomsttaal in de verantwoording. Beschrijf wat je daadwerkelijk hebt gedaan."},
      {title:"Vakinhoudelijk en persoonlijk geëvalueerd", ok:stepComplete(5), message:stepComplete(5)?"Beide evaluaties en een volgend leerdoel zijn aanwezig.":"Werk beide evaluaties uit en benoem een concreet volgend leerdoel."},
      {title:"Verklaring opgenomen", ok:r.declaration_accepted, message:r.declaration_accepted?"De verplichte verklaring komt in elke export.":"Bevestig de verklaring voordat je inlevert."}
    ];
  }
  function renderPreview() {
    const r = state.report, s = r.student, p = r.project;
    $("#previewTitle").textContent = p.title || "Examenverslag";
    const meta = [["Naam",s.name],["Klas",s.class_name],["Versie",p.version],["Datum",p.report_date],["Stagebedrijf",s.company]].filter(x=>x[1]);
    const selected = r.work_processes.filter(x=>x.selected);
    $("#previewPaper").innerHTML = `<h1>${escapeHtml(p.title || "Titel van het project")}</h1><p>${escapeHtml(p.subtitle || p.exam_name || "Examenverslag")}</p><div class="cover-meta">${meta.map(([a,b])=>`<div><strong>${escapeHtml(a)}</strong><span>${escapeHtml(b)}</span></div>`).join("") || `<p class="placeholder">Vul de basisgegevens in.</p>`}</div><h2>Inleiding</h2><p>${escapeHtml(p.introduction || "De inleiding verschijnt hier.")}</p><h2>Examenactiviteiten</h2>${previewList(r.activities)}<h2>Planning</h2>${r.planning.filter(x=>x.phase).map(x=>`<h3>${escapeHtml(x.phase)}</h3>${previewList(x.tasks)}`).join("")}<h2>Verantwoording</h2>${selected.slice(0,3).map(x=>`<h3>${escapeHtml(x.code)} ${escapeHtml(x.title)}</h3><p>${escapeHtml(x.accountability || "Nog te beschrijven.")}</p>`).join("")}<h2>Evaluatie</h2><p>${escapeHtml(r.evaluation.professional || "Nog te schrijven.")}</p>`;
  }
  function previewList(items) { return items?.length ? `<ul>${items.filter(Boolean).map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>` : `<p class="placeholder">Nog niets toegevoegd.</p>`; }
  function showNotice(text, error=false) { const el=$("#notice"); el.hidden=false; el.textContent=text; el.style.background=error?"#fff0f0":"#eefaf5"; el.style.color=error?"#8b2424":"#0d6849"; clearTimeout(el._timer); el._timer=setTimeout(()=>el.hidden=true,5000); }
  function saveJson() {
    const blob = new Blob([JSON.stringify(state.report, null, 2)], {type:"application/json"});
    const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=`verslag-concept-${slug(state.report.student.name || "student")}.json`; a.click(); URL.revokeObjectURL(a.href); showNotice("Concept als JSON gedownload.");
  }
  async function loadJson(file) {
    try { const raw=JSON.parse(await file.text()); const response=await fetch("/api/normalize",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(raw)}); const data=await response.json(); if(!response.ok) throw new Error(data.error || "Importeren mislukt"); state.report=data; saveAutosave(); renderStep(); showNotice("Concept geladen. Controleer vooral de extra verslagonderdelen."); }
    catch(err){ showNotice(err.message || "Kon dit JSON-bestand niet lezen.", true); }
  }
  async function exportReport(kind, button) {
    const old=button.innerHTML; button.disabled=true; button.textContent="Bezig…";
    try { const response=await fetch(`/api/export/${kind}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(state.report)}); if(!response.ok){const data=await response.json();throw new Error(data.error||"Export mislukt");} const blob=await response.blob(); const disposition=response.headers.get("Content-Disposition")||""; const match=/filename\*?=(?:UTF-8''|\")?([^\";]+)/i.exec(disposition); const filename=match?decodeURIComponent(match[1].replace(/\"/g,"")):`examenverslag.${kind}`; const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=filename; a.click(); URL.revokeObjectURL(a.href); showNotice(`${kind.toUpperCase()} gedownload.`); }
    catch(err){showNotice(err.message, true);} finally {button.disabled=false;button.innerHTML=old;}
  }
  const slug = text => text.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"") || "student";

  $("#previousStep").addEventListener("click",()=>{state.step=Math.max(0,state.step-1);renderStep();});
  $("#nextStep").addEventListener("click",()=>{state.step=state.step===steps.length-1?0:state.step+1;renderStep();});
  $("#saveJson").addEventListener("click",saveJson);
  $("#loadJson").addEventListener("click",()=>$("#fileInput").click());
  $("#fileInput").addEventListener("change",e=>{if(e.target.files[0])loadJson(e.target.files[0]);e.target.value="";});
  $("#previewToggle").addEventListener("click",()=>$("#previewPanel").classList.toggle("open"));
  renderStep();
})();
