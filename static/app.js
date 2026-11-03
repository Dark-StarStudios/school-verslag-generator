(() => {
  "use strict";
  const clone = value => JSON.parse(JSON.stringify(value));
  const STORAGE_KEY = "school-verslag/1.0/autosave";
  const DECLARATION = `Hierbij verklaar ik dat:
Het door mij gemaakte werk zelf geschreven is en dat ik geen teksten heb overgenomen uit andere stageverslagen, scripties, overige geschriften en literatuur zonder de bron te hebben vermeld.
De inhoud van dit verslag komt, voor wat betreft de feiten en de verrichte werkzaamheden, geheel overeen met de werkelijkheid.
De beschreven door mij uitgevoerde werkzaamheden zijn daadwerkelijk door mij verricht.`;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = value => String(value ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const value = path => path.split(".").reduce((obj, key) => obj?.[key], state.report);
  const setValue = (path, next) => {
    const parts = path.split("."); let obj = state.report;
    parts.slice(0, -1).forEach(key => obj = obj[key]); obj[parts.at(-1)] = next;
  };
  const list = path => Array.isArray(value(path)) ? value(path) : [];
  const mergeDefaults = (defaults, saved) => {
    if (!defaults || typeof defaults !== "object" || Array.isArray(defaults) || !saved || typeof saved !== "object" || Array.isArray(saved)) return clone(saved);
    const merged = clone(defaults);
    Object.entries(saved).forEach(([key, savedValue]) => {
      merged[key] = key in merged ? mergeDefaults(merged[key], savedValue) : clone(savedValue);
    });
    return merged;
  };

  const steps = [
    ["Voorblad", "Voorblad en basisgegevens", "Leg vast wie het verslag maakt en over welk examenproject het gaat."],
    ["Activiteiten", "Examenactiviteiten", "Beschrijf het resultaat, de werkzaamheden en wat je daarvoor nodig had."],
    ["Grenzen", "Grenzen en randvoorwaarden", "Maak duidelijk wat wel en niet bij het examen hoort."],
    ["Planning", "Planning", "Zet de fasen, perioden en concrete taken in een realistische volgorde."],
    ["Werkprocessen", "Verantwoording per werkproces", "Koppel je handelen en bewijs aan elk geselecteerd werkproces."],
    ["Keuzedelen", "Keuzedelen", "Selecteer de D1-werkprocessen van jouw keuzedelen en verantwoord ze afzonderlijk."],
    ["Evaluatie", "Evaluatie", "Evalueer vakinhoudelijk en persoonlijk, inclusief je volgende leerdoel."],
    ["Verklaring", "Verklaring", "Bevestig de verplichte verklaring voor je eigen werk."],
    ["Vormgeving", "Vormgeving van het document", "Kies de kleur en lettertypen die in het voorbeeld en alle exports worden gebruikt."],
    ["Controleren", "Controleren en exporteren", "Los de laatste inhoudelijke waarschuwingen op en download je verslag."]
  ];
  const state = { report: loadAutosave(), step: 0 };

  function loadAutosave() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      return saved ? mergeDefaults(window.DEFAULT_REPORT, saved) : clone(window.DEFAULT_REPORT);
    }
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
    $("#stepContent").innerHTML = [renderCover, renderActivities, renderScope, renderPlanning, renderWorkProcesses, renderKeuzedelen, renderEvaluation, renderDeclaration, renderDesign, renderChecks][state.step]();
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
      ${field("Titel", "project.title", {required:true, placeholder:"Bijvoorbeeld een website"})}
      ${field("Ondertitel", "project.subtitle", {placeholder:"Bijvoorbeeld examenverslag"})}
      ${field("Naam student", "student.name", {required:true, placeholder:"Bijvoorbeeld Nikita Vlasov"})}${field("OV-nummer", "student.student_number")}
      ${field("Klas", "student.class_name", {required:true, placeholder:"Bijvoorbeeld WEB3A"})}${field("Stagebedrijf of opdrachtgever", "student.company", {required:true})}
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
    return `<p class="hint">De criteria komen uit Web development C2024, Crebo 25604ONA1. Selecteer alleen processen waarop je wordt beoordeeld.</p>` + state.report.work_processes.map((wp, i) => `<article class="wp-card"><div class="wp-top"><div><span class="wp-code">${escapeHtml(wp.code)}</span><h3>${escapeHtml(wp.title)}</h3><span class="hint">${escapeHtml((wp.competencies || []).join(", "))}</span></div><label class="switch" aria-label="${escapeHtml(wp.code)} selecteren"><input type="checkbox" data-wp-select="${i}" ${wp.selected ? "checked" : ""}><span></span></label></div>${wp.selected ? `<details><summary>Beoordelingscriteria bekijken</summary><ul>${(wp.indicators || []).map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul></details><div class="field"><label>Mijn verantwoording *</label><textarea data-path="work_processes.${i}.accountability" rows="7" placeholder="Beschrijf situatie, jouw eigen handelingen, gemaakte keuzes, resultaat en wat je daarvan hebt geleerd.">${escapeHtml(wp.accountability || "")}</textarea><small>Schrijf in de ik-vorm en verwijs naar controleerbaar bewijs.</small></div><div style="margin-top:14px">${repeatSection("Bewijs", `work_processes.${i}.evidence`, "Bijvoorbeeld GitHub commit, screenshot, testverslag of feedback")}</div>${evidenceImageSection(wp, i)}` : ""}</article>`).join("");
  }
  function evidenceImageSection(wp, index) {
    const images = wp.evidence_images || [];
    return `<section class="evidence-images"><div class="repeat-head"><div><h3>Screenshots</h3><span class="hint">PNG, JPG of WebP; afbeeldingen komen ook in PDF, DOCX en ODT.</span></div><label class="add-button file-button">+ screenshots<input type="file" accept="image/png,image/jpeg,image/webp" multiple data-evidence-images="${index}"></label></div><div class="evidence-grid">${images.map((image, imageIndex) => `<figure><img src="${escapeHtml(image.data)}" alt="${escapeHtml(image.name || "Bewijs")}"><figcaption>${escapeHtml(image.name || `Screenshot ${imageIndex + 1}`)}</figcaption><button type="button" class="icon-button" data-remove-evidence-image="${index}" data-image-index="${imageIndex}" aria-label="Screenshot verwijderen">×</button></figure>`).join("") || `<span class="hint">Nog geen screenshots toegevoegd.</span>`}</div></section>`;
  }
  function renderKeuzedelen() {
    return `<p class="hint choice-intro">Selecteer per keuzedeel alleen de D1-werkprocessen waarop je wordt beoordeeld. Ze werken hetzelfde als de gewone werkprocessen.</p>` + (state.report.keuzedelen || []).map((choice, choiceIndex) => `<article class="choice-card">
      <div class="choice-top"><div><div class="choice-title"><strong>${escapeHtml(choice.code)} — ${escapeHtml(choice.title)}</strong><span class="choice-badge">keuzedeel</span></div><span class="choice-certificate">${escapeHtml(choice.certificate)}</span></div></div>
      <div class="choice-work-processes">${(choice.work_processes || []).map((process, processIndex) => `<section class="wp-card choice-wp-card"><div class="wp-top"><div><span class="wp-code">${escapeHtml(process.code)}</span><h3>${escapeHtml(process.title)}</h3></div><label class="switch" aria-label="${escapeHtml(process.code)} selecteren"><input type="checkbox" data-choice-wp-select="${choiceIndex}" data-choice-process="${processIndex}" ${process.selected ? "checked" : ""}><span></span></label></div>${process.selected ? `<div class="field"><label>Mijn verantwoording *</label><textarea data-path="keuzedelen.${choiceIndex}.work_processes.${processIndex}.accountability" rows="7" placeholder="Beschrijf situatie, jouw eigen handelingen, gemaakte keuzes, resultaat en wat je daarvan hebt geleerd.">${escapeHtml(process.accountability || "")}</textarea><small>Schrijf in de ik-vorm en verwijs naar controleerbaar bewijs.</small></div><div style="margin-top:14px">${repeatSection("Bewijs", `keuzedelen.${choiceIndex}.work_processes.${processIndex}.evidence`, "Bijvoorbeeld ontwerp, commit, testresultaat of feedback")}</div>${choiceEvidenceImages(process, choiceIndex, processIndex)}` : ""}</section>`).join("")}</div>
    </article>`).join("");
  }
  function choiceEvidenceImages(process, choiceIndex, processIndex) {
    const images = process.evidence_images || [];
    return `<section class="evidence-images"><div class="repeat-head"><div><h3>Screenshots</h3><span class="hint">Deze afbeeldingen komen ook in PDF, DOCX en ODT.</span></div><label class="add-button file-button">+ screenshots<input type="file" accept="image/png,image/jpeg,image/webp" multiple data-choice-images="${choiceIndex}" data-choice-process="${processIndex}"></label></div><div class="evidence-grid">${images.map((image, imageIndex) => `<figure><img src="${escapeHtml(image.data)}" alt="${escapeHtml(image.name || "Bewijs")}"><figcaption>${escapeHtml(image.name || `Screenshot ${imageIndex + 1}`)}</figcaption><button type="button" class="icon-button" data-remove-choice-image="${choiceIndex}" data-choice-process="${processIndex}" data-image-index="${imageIndex}" aria-label="Screenshot verwijderen">×</button></figure>`).join("") || `<span class="hint">Nog geen screenshots toegevoegd.</span>`}</div></section>`;
  }
  function renderEvaluation() {
    return `<div class="field-grid">${field("Vakinhoudelijke evaluatie", "evaluation.professional", {type:"textarea", full:true, required:true, placeholder:"Wat wilde je leren, wat heb je geleerd, wat ging goed en wat kon beter?"})}${field("Persoonlijke evaluatie", "evaluation.personal", {type:"textarea", full:true, required:true, placeholder:"Wat heb je over samenwerken, plannen, communiceren en jezelf geleerd?"})}${field("Volgend project", "evaluation.next_project", {type:"textarea", full:true, required:true, placeholder:"Wat ga je de volgende keer concreet anders doen of verder leren?"})}</div>`;
  }
  function renderDeclaration() {
    const color = /^#[0-9a-f]{6}$/i.test(state.report.design?.declaration_color || "") ? state.report.design.declaration_color : "#FF5F57";
    return `<div class="declaration" style="--declaration-color:${escapeHtml(color)}">${escapeHtml(DECLARATION)}</div><label class="check-card" style="margin-top:18px"><input type="checkbox" id="declarationAccepted" ${state.report.declaration_accepted ? "checked" : ""}><span><strong>Ik neem deze verklaring op in mijn verslag</strong><p>Controleer vóór inleveren of alle beschreven werkzaamheden echt door jou zijn uitgevoerd.</p></span></label>`;
  }
  function renderDesign() {
    const d = state.report.design || {};
    const fontOptions = ["Arial", "Georgia", "Times New Roman", "Verdana"];
    const select = (label, path, selected) => `<div class="field"><label>${label}</label><select data-path="${path}">${fontOptions.map(font => `<option value="${font}" ${font === selected ? "selected" : ""}>${font}</option>`).join("")}</select></div>`;
    const presets = ["#5B9BD5", "#2F5597", "#2E7D6E", "#7A5195", "#C55A11", "#000000", "#D32F2F"];
    const declarationPresets = ["#FF5F57", "#D32F2F", "#000000", "#3858E8"];
    const coverType = d.cover_background_type || "solid";
    return `<div class="design-panel">
      <div class="field color-field"><label>Kleur van titels en tussenkoppen</label><div class="color-control"><input data-path="design.heading_color" type="color" value="${escapeHtml(d.heading_color || "#5B9BD5")}"><input data-path="design.heading_color" type="text" value="${escapeHtml(d.heading_color || "#5B9BD5")}" maxlength="7" pattern="#[0-9A-Fa-f]{6}" aria-label="Hexadecimale kleur"></div><small>De gekozen kleur wordt toegepast op de titel, hoofdstukken en subkoppen.</small></div>
      <div class="color-presets" aria-label="Kleurvoorbeelden">${presets.map(color => `<button type="button" data-color-preset="${color}" style="--swatch:${color}" aria-label="Kies ${color}" title="${color}"></button>`).join("")}</div>
      <div class="field-grid">${select("Lettertype van titels", "design.heading_font", d.heading_font || "Arial")}${select("Lettertype van tekst", "design.body_font", d.body_font || "Arial")}</div>
      <div class="field"><label>Achtergrond van het voorblad</label><select data-path="design.cover_background_type"><option value="solid" ${coverType === "solid" ? "selected" : ""}>Effen kleur</option><option value="gradient" ${coverType === "gradient" ? "selected" : ""}>Kleurverloop (gradient)</option></select><small>Het kleurverloop wordt in het voorbeeld en alle exports toegepast.</small></div>
      <div class="field-grid">
        <div class="field color-field"><label>${coverType === "gradient" ? "Beginkleur van het verloop" : "Achtergrondkleur van het voorblad"}</label><div class="color-control"><input data-path="design.cover_background_color" type="color" value="${escapeHtml(d.cover_background_color || "#FFFFFF")}"><input data-path="design.cover_background_color" type="text" value="${escapeHtml(d.cover_background_color || "#FFFFFF")}" maxlength="7" pattern="#[0-9A-Fa-f]{6}" aria-label="Beginkleur voorblad"></div></div>
        <div class="field color-field"><label>Eindkleur van het verloop</label><div class="color-control"><input data-path="design.cover_gradient_end_color" type="color" value="${escapeHtml(d.cover_gradient_end_color || "#3858E8")}"><input data-path="design.cover_gradient_end_color" type="text" value="${escapeHtml(d.cover_gradient_end_color || "#3858E8")}" maxlength="7" pattern="#[0-9A-Fa-f]{6}" aria-label="Eindkleur kleurverloop"></div><small>Wordt alleen gebruikt wanneer kleurverloop is gekozen.</small></div>
      </div>
      <div class="field-grid">
        <div class="field"><label>Richting van het kleurverloop</label><select data-path="design.cover_gradient_direction"><option value="diagonal" ${(d.cover_gradient_direction || "diagonal") === "diagonal" ? "selected" : ""}>Diagonaal</option><option value="vertical" ${d.cover_gradient_direction === "vertical" ? "selected" : ""}>Verticaal</option><option value="horizontal" ${d.cover_gradient_direction === "horizontal" ? "selected" : ""}>Horizontaal</option></select></div>
        <div class="field color-field"><label>Tekstkleur op het voorblad</label><div class="color-control"><input data-path="design.cover_text_color" type="color" value="${escapeHtml(d.cover_text_color || "#FFFFFF")}"><input data-path="design.cover_text_color" type="text" value="${escapeHtml(d.cover_text_color || "#FFFFFF")}" maxlength="7" pattern="#[0-9A-Fa-f]{6}" aria-label="Tekstkleur voorblad"></div></div>
      </div>
      <div class="field color-field"><label>Kleur van de verklaring</label><div class="color-control"><input data-path="design.declaration_color" type="color" value="${escapeHtml(d.declaration_color || "#FF5F57")}"><input data-path="design.declaration_color" type="text" value="${escapeHtml(d.declaration_color || "#FF5F57")}" maxlength="7" pattern="#[0-9A-Fa-f]{6}" aria-label="Kleur verklaring"></div><small>Deze kleur wordt gebruikt voor de accentlijn en de subtiele achtergrond van de verklaring.</small></div>
      <div class="color-presets" aria-label="Kleurvoorbeelden voor verklaring">${declarationPresets.map(color => `<button type="button" data-declaration-color-preset="${color}" style="--swatch:${color}" aria-label="Kies ${color} voor de verklaring" title="${color}"></button>`).join("")}</div>
      <section class="cover-logo-field"><div class="repeat-head"><div><h3>Logo op het voorblad</h3><span class="hint">PNG, JPG of WebP. Het logo blijft lokaal in het concept opgeslagen.</span></div><label class="add-button file-button">${d.cover_logo?.data ? "Logo vervangen" : "+ logo toevoegen"}<input type="file" accept="image/png,image/jpeg,image/webp" data-cover-logo></label></div>${d.cover_logo?.data ? `<figure><img src="${escapeHtml(d.cover_logo.data)}" alt="${escapeHtml(d.cover_logo.name || "Voorbladlogo")}"><figcaption>${escapeHtml(d.cover_logo.name || "Voorbladlogo")}</figcaption><button type="button" class="icon-button" data-remove-cover-logo aria-label="Logo verwijderen">×</button></figure>` : `<span class="hint">Nog geen logo toegevoegd.</span>`}</section>
      <p class="hint design-note">DOCX en ODT gebruiken het gekozen lettertype rechtstreeks. PDF gebruikt een veilige, gelijkende letterfamilie zodat het bestand overal opent.</p>
    </div>`;
  }
  function renderChecks() {
    const checks = qualityChecks(); const errors = checks.filter(x => !x.ok);
    return `<div>${checks.map(x => `<article class="check-card ${x.ok ? "ok" : "warn"}"><span>${x.ok ? "✓" : "!"}</span><div><strong>${escapeHtml(x.title)}</strong><p>${escapeHtml(x.message)}</p></div></article>`).join("")}</div><div class="export-grid"><button type="button" class="export-button" data-export="pdf">PDF<span>Direct inleverbaar</span></button><button type="button" class="export-button" data-export="docx">DOCX<span>Verder bewerken in Word</span></button><button type="button" class="export-button" data-export="odt">ODT<span>LibreOffice en OpenDocument</span></button></div>${errors.length ? `<p class="hint">Exporteren kan al, maar los de waarschuwingen op voor een sterker verslag.</p>` : `<p class="hint">Alle basiscontroles zijn geslaagd. Lees het verslag nog één keer zelf na.</p>`}`;
  }
  function bindDynamic() {
    $$('[data-path]').forEach(el => {
      const sync = () => {
        setValue(el.dataset.path, el.value);
        $$(`[data-path="${el.dataset.path}"]`).forEach(peer => {
          if (peer !== el && (peer.type !== "color" || /^#[0-9a-f]{6}$/i.test(el.value))) peer.value = el.value;
        });
        scheduleSave(); renderPreview(); updateProgress();
      };
      el.addEventListener("input", sync);
      // Date pickers and some autofill implementations only emit change.
      el.addEventListener("change", sync);
    });
    $$('[data-list-path]').forEach(el => {
      const sync = () => { const arr = list(el.dataset.listPath); arr[Number(el.dataset.index)] = el.value; scheduleSave(); renderPreview(); updateProgress(); };
      el.addEventListener("input", sync);
      el.addEventListener("change", sync);
    });
    $$('[data-add-list]').forEach(el => el.addEventListener("click", () => { list(el.dataset.addList).push(""); scheduleSave(); renderStep(); }));
    $$('[data-remove-list]').forEach(el => el.addEventListener("click", () => { list(el.dataset.removeList).splice(Number(el.dataset.index), 1); scheduleSave(); renderStep(); }));
    $$('[data-step]').forEach(el => el.addEventListener("click", () => { state.step = Number(el.dataset.step); renderStep(); }));
    $$('[data-wp-select]').forEach(el => el.addEventListener("change", () => { state.report.work_processes[Number(el.dataset.wpSelect)].selected = el.checked; scheduleSave(); renderStep(); }));
    $$('[data-choice-wp-select]').forEach(el => el.addEventListener("change", () => {
      state.report.keuzedelen[Number(el.dataset.choiceWpSelect)].work_processes[Number(el.dataset.choiceProcess)].selected = el.checked;
      scheduleSave(); renderStep();
    }));
    $$('[data-color-preset]').forEach(el => el.addEventListener("click", () => { state.report.design.heading_color = el.dataset.colorPreset; scheduleSave(); renderStep(); }));
    $$('[data-declaration-color-preset]').forEach(el => el.addEventListener("click", () => { state.report.design.declaration_color = el.dataset.declarationColorPreset; scheduleSave(); renderStep(); }));
    $('[data-path="design.cover_background_type"]')?.addEventListener("change", () => renderStep());
    $('[data-cover-logo]')?.addEventListener("change", async event => {
      const file = event.target.files?.[0];
      if (!file) return;
      state.report.design ||= {};
      state.report.design.cover_logo = {name:file.name, type:file.type, data:await fileToDataUrl(file)};
      scheduleSave(); renderStep();
    });
    $('[data-remove-cover-logo]')?.addEventListener("click", () => { state.report.design.cover_logo = null; scheduleSave(); renderStep(); });
    $$('[data-remove-phase]').forEach(el => el.addEventListener("click", () => { state.report.planning.splice(Number(el.dataset.removePhase), 1); scheduleSave(); renderStep(); }));
    $("#addPhase")?.addEventListener("click", () => { state.report.planning.push({phase:"", period:"", tasks:[]}); scheduleSave(); renderStep(); });
    $("#declarationAccepted")?.addEventListener("change", e => { state.report.declaration_accepted = e.target.checked; scheduleSave(); renderPreview(); updateProgress(); });
    $$('[data-evidence-images]').forEach(el => el.addEventListener("change", async () => {
      const wp = state.report.work_processes[Number(el.dataset.evidenceImages)];
      wp.evidence_images ||= [];
      for (const file of [...el.files]) {
        if (!/^image\/(png|jpeg|webp)$/.test(file.type)) continue;
        wp.evidence_images.push({name:file.name, type:file.type, data:await fileToDataUrl(file)});
      }
      scheduleSave(); renderStep();
    }));
    $$('[data-remove-evidence-image]').forEach(el => el.addEventListener("click", () => {
      const wp = state.report.work_processes[Number(el.dataset.removeEvidenceImage)];
      (wp.evidence_images ||= []).splice(Number(el.dataset.imageIndex), 1);
      scheduleSave(); renderStep();
    }));
    $$('[data-choice-images]').forEach(el => el.addEventListener("change", async () => {
      const process = state.report.keuzedelen[Number(el.dataset.choiceImages)].work_processes[Number(el.dataset.choiceProcess)];
      process.evidence_images ||= [];
      for (const file of [...el.files]) {
        if (!/^image\/(png|jpeg|webp)$/.test(file.type)) continue;
        process.evidence_images.push({name:file.name, type:file.type, data:await fileToDataUrl(file)});
      }
      scheduleSave(); renderStep();
    }));
    $$('[data-remove-choice-image]').forEach(el => el.addEventListener("click", () => {
      const process = state.report.keuzedelen[Number(el.dataset.removeChoiceImage)].work_processes[Number(el.dataset.choiceProcess)];
      (process.evidence_images ||= []).splice(Number(el.dataset.imageIndex), 1);
      scheduleSave(); renderStep();
    }));
    $$('[data-export]').forEach(el => el.addEventListener("click", () => exportReport(el.dataset.export, el)));
  }
  function stepComplete(i) {
    const r = state.report;
    if (i === 0) return [r.student.name,r.student.class_name,r.student.company,r.project.title,r.project.report_date,r.project.introduction].every(Boolean);
    if (i === 1) return r.activities.length > 0 && Object.values(r.resources).some(x => x.length);
    if (i === 2) return r.scope.included.length && r.scope.excluded.length && r.scope.provided.length;
    if (i === 3) return r.planning.length && r.planning.every(x => x.phase && x.tasks.length);
    if (i === 4) { const selected = r.work_processes.filter(x => x.selected); return selected.length > 0 && selected.every(x => (x.accountability || "").trim().length >= 80 && ((x.evidence || []).length || (x.evidence_images || []).length)); }
    if (i === 5) { const selected = (r.keuzedelen || []).flatMap(choice => (choice.work_processes || []).filter(x => x.selected)); return !selected.length || selected.every(x => (x.accountability || "").trim().length >= 80 && ((x.evidence || []).length || (x.evidence_images || []).length)); }
    if (i === 6) return Object.values(r.evaluation).every(x => (x || "").trim().length >= 80);
    if (i === 7) return r.declaration_accepted;
    if (i === 8) return /^#[0-9a-f]{6}$/i.test(r.design?.heading_color || "") && Boolean(r.design?.heading_font && r.design?.body_font);
    return qualityChecks().every(x => x.ok);
  }
  function updateProgress() {
    const done = steps.map((_, i) => stepComplete(i)).filter(Boolean).length;
    const pct = Math.round(done / steps.length * 100);
    $("#progressLabel").textContent = `${pct}%`; $("#progressBar").style.width = `${pct}%`;
    $("#progressHint").textContent = done === steps.length ? "Klaar voor de laatste eigen controle." : `${done} van ${steps.length} onderdelen compleet.`;
    const selected = state.report.work_processes.filter(item => item.selected).length;
    const selectedChoices = (state.report.keuzedelen || []).flatMap(choice => choice.work_processes || []).filter(item => item.selected).length;
    $("#selectedCount").textContent = selectedChoices ? `${selected} gewone + ${selectedChoices} keuze-werkprocessen geselecteerd` : `${selected} werkprocessen geselecteerd`;
  }
  function qualityChecks() {
    const r = state.report; const selected = r.work_processes.filter(x => x.selected);
    const joined = selected.map(x => x.accountability || "").join(" ").toLowerCase();
    const future = (joined.match(/\b(zal|zullen|ga|gaan)\b/g) || []).length;
    return [
      {title:"Voorblad en inleiding", ok:stepComplete(0), message:stepComplete(0)?"De verplichte basisgegevens zijn ingevuld.":"Vul titel, naam, klas, opdrachtgever, datum en inleiding in."},
      {title:"Afbakening en planning", ok:stepComplete(2)&&stepComplete(3), message:stepComplete(2)&&stepComplete(3)?"Scope en projectfasen zijn beschreven.":"Beschrijf wat wel en niet hoort bij het examen en voeg taken per fase toe."},
      {title:"Alle geselecteerde werkprocessen verantwoord", ok:stepComplete(4), message:stepComplete(4)?"Elk werkproces heeft een toelichting en bewijs.":"Schrijf per geselecteerd werkproces minimaal een concrete toelichting en voeg bewijs toe."},
      {title:"Geselecteerde keuzedelen verantwoord", ok:stepComplete(5), message:stepComplete(5)?"De keuzedelen zijn niet geselecteerd of volledig verantwoord.":"Schrijf per werkproces van ieder geselecteerd keuzedeel een toelichting en voeg bewijs toe."},
      {title:"Feitelijke formulering", ok:future < 3, message:future < 3?"De verantwoording gebruikt hoofdzakelijk gerealiseerde resultaten.":"Er staat veel toekomsttaal in de verantwoording. Beschrijf wat je daadwerkelijk hebt gedaan."},
      {title:"Vakinhoudelijk en persoonlijk geëvalueerd", ok:stepComplete(6), message:stepComplete(6)?"Beide evaluaties en een volgend leerdoel zijn aanwezig.":"Werk beide evaluaties uit en benoem een concreet volgend leerdoel."},
      {title:"Verklaring opgenomen", ok:r.declaration_accepted, message:r.declaration_accepted?"De verplichte verklaring komt in elke export.":"Bevestig de verklaring voordat je inlevert."}
    ];
  }
  function renderPreview() {
    const r = state.report, s = r.student, p = r.project;
    const design = r.design || {};
    const paper = $("#previewPaper");
    paper.style.setProperty("--document-heading", /^#[0-9a-f]{6}$/i.test(design.heading_color || "") ? design.heading_color : "#5B9BD5");
    paper.style.setProperty("--document-heading-font", JSON.stringify(design.heading_font || "Arial"));
    paper.style.setProperty("--document-body-font", JSON.stringify(design.body_font || "Arial"));
    const coverStart = /^#[0-9a-f]{6}$/i.test(design.cover_background_color || "") ? design.cover_background_color : "#FFFFFF";
    const coverEnd = /^#[0-9a-f]{6}$/i.test(design.cover_gradient_end_color || "") ? design.cover_gradient_end_color : "#3858E8";
    const gradientDirection = ({vertical:"to bottom", horizontal:"to right", diagonal:"135deg"})[design.cover_gradient_direction] || "135deg";
    const coverBackground = design.cover_background_type === "gradient" ? `linear-gradient(${gradientDirection}, ${coverStart}, ${coverEnd})` : coverStart;
    paper.style.setProperty("--cover-background", coverBackground);
    paper.style.setProperty("--cover-text", /^#[0-9a-f]{6}$/i.test(design.cover_text_color || "") ? design.cover_text_color : "#FFFFFF");
    paper.style.setProperty("--declaration-color", /^#[0-9a-f]{6}$/i.test(design.declaration_color || "") ? design.declaration_color : "#FF5F57");
    $("#previewTitle").textContent = p.title || "Examenverslag";
    const meta = [
      ["Naam", s.name], ["OV-nummer", s.student_number], ["Klas", s.class_name],
      ["Versie", p.version], ["Verslagdatum", displayDate(p.report_date)],
      ["Examennaam", p.exam_name], ["Examennummer", p.exam_number],
      ["Startdatum examen", displayDate(p.start_date)], ["Einddatum examen", displayDate(p.end_date)],
      ["Stagebedrijf", s.company], ["Praktijkopleider", s.practice_supervisor],
      ["BPV-begeleider", s.bpv_supervisor]
    ].filter(([, content]) => content);
    const selected = r.work_processes.filter(x=>x.selected);
    const selectedChoices = (r.keuzedelen || []).filter(choice => (choice.work_processes || []).some(process => process.selected));
    const planning = (r.planning || []).filter(x => x.phase || x.period || x.tasks?.some(Boolean));
    const customCover = Boolean(design.cover_logo?.data || design.cover_background_type === "gradient" || (design.cover_background_color && design.cover_background_color.toUpperCase() !== "#FFFFFF"));
    const coverHtml = customCover ? `<section class="preview-cover-custom">${design.cover_logo?.data ? `<div class="preview-cover-logo"><img src="${escapeHtml(design.cover_logo.data)}" alt="${escapeHtml(design.cover_logo.name || "Logo")}"></div>` : ""}<div class="preview-cover-panel"><h1>${escapeHtml(p.title || "Titel van het project")}</h1><p class="preview-cover-version">Versie ${escapeHtml(p.version || "1.0")}</p><p class="preview-cover-author">${escapeHtml(s.name || "Naam student")}<br>${escapeHtml(displayDate(p.report_date) || "Verslagdatum")}</p><p class="preview-cover-company">Stagebedrijf: ${escapeHtml(s.company || "-")}<br>Stagebegeleider: ${escapeHtml(s.practice_supervisor || "-")}<br>BPV: ${escapeHtml(s.bpv_supervisor || "-")}</p></div></section>` : `<h1>${escapeHtml(p.title || "Titel van het project")}</h1><p>${escapeHtml(p.subtitle || p.exam_name || "Examenverslag")}</p><div class="cover-meta">${meta.map(([label, content])=>`<div><strong>${escapeHtml(label)}</strong><span>${escapeHtml(content)}</span></div>`).join("") || `<p class="placeholder">Vul de basisgegevens in.</p>`}</div>`;
    paper.innerHTML = `
      ${coverHtml}
      <h2>Inleiding</h2>${previewText(p.introduction || p.description, "De inleiding verschijnt hier.")}
      <h2>Projectgegevens</h2>
      <h3>Op te leveren producten</h3>${previewList(p.products)}
      <h2>Examenactiviteiten</h2>${previewList(r.activities)}
      <h3>Materialen en software</h3>${previewList(r.resources.materials)}
      <h3>Mensen</h3>${previewList(r.resources.people)}
      <h3>Middelen</h3>${previewList(r.resources.means)}
      <h3>Kennis</h3>${previewList(r.resources.knowledge)}
      <h2>Grenzen en randvoorwaarden</h2>
      <h3>Wat hoort wel bij het examen?</h3>${previewList(r.scope.included)}
      <h3>Wat hoort niet bij het examen?</h3>${previewList(r.scope.excluded)}
      <h3>Wat stelt de opdrachtgever beschikbaar?</h3>${previewList(r.scope.provided)}
      <h2>Planning</h2>${planning.length ? planning.map(x=>`<h3>${escapeHtml(x.phase || "Projectfase")}${x.period ? ` — ${escapeHtml(x.period)}` : ""}</h3>${previewList(x.tasks)}`).join("") : `<p class="placeholder">Nog geen projectfasen ingevuld.</p>`}
      <h2>Verantwoording</h2>${selected.length ? selected.map(x=>`<h3>${escapeHtml(x.code)} ${escapeHtml(x.title)}</h3>${x.competencies?.length ? `<p><strong>Competenties:</strong> ${escapeHtml(x.competencies.join(", "))}</p>` : ""}${previewText(x.accountability, "Nog te beschrijven.")}<h3>Bewijs</h3>${previewList(x.evidence)}${previewImages(x.evidence_images)}`).join("") : `<p class="placeholder">Nog geen werkprocessen geselecteerd.</p>`}
      ${selectedChoices.length ? `<h2>Keuzedelen</h2>${selectedChoices.map(choice => `<h3>${escapeHtml(choice.code)} — ${escapeHtml(choice.title)}</h3><p><strong>Code:</strong> ${escapeHtml(choice.certificate)}</p>${(choice.work_processes || []).filter(process => process.selected).map(process => `<h3>${escapeHtml(process.code)} — ${escapeHtml(process.title)}</h3>${previewText(process.accountability, "Nog te beschrijven.")}<h3>Bewijs</h3>${previewList(process.evidence)}${previewImages(process.evidence_images)}`).join("")}`).join("")}` : ""}
      <h2>Evaluatie</h2>
      <h3>Vakinhoudelijke evaluatie</h3>${previewText(r.evaluation.professional, "Nog te schrijven.")}
      <h3>Persoonlijke evaluatie</h3>${previewText(r.evaluation.personal, "Nog te schrijven.")}
      <h3>Volgend project</h3>${previewText(r.evaluation.next_project, "Nog te schrijven.")}
      <h2>Verklaring</h2>${r.declaration_accepted ? `<div class="preview-declaration">${previewText(DECLARATION)}</div>` : `<p class="placeholder">Bevestig de verklaring om deze op te nemen.</p>`}`;
  }
  function displayDate(date) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || "");
    return match ? `${match[3]}-${match[2]}-${match[1]}` : (date || "");
  }
  function previewText(text, fallback="") {
    const content = String(text || fallback || "");
    return `<p${text ? "" : ` class="placeholder"`}>${escapeHtml(content).replace(/\n/g, "<br>")}</p>`;
  }
  function previewList(items) {
    const values = (items || []).filter(item => String(item || "").trim());
    return values.length ? `<ul>${values.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>` : `<p class="placeholder">Nog niets toegevoegd.</p>`;
  }
  function previewImages(images) {
    return (images || []).map(image => `<figure class="preview-evidence"><img src="${escapeHtml(image.data)}" alt="${escapeHtml(image.name || "Bewijs")}"><figcaption>${escapeHtml(image.name || "Screenshot")}</figcaption></figure>`).join("");
  }
  function fileToDataUrl(file) {
    return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(reader.error); reader.readAsDataURL(file); });
  }
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
