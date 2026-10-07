"use strict";
/* Student Guide frontend. One file, one init function per page (picked by <body data-page>).
   The browser only talks to our own /api/* endpoints. No API keys exist here. */

/* ---------- small helpers ---------- */
const $ = (sel, root = document) => root.querySelector(sel);

// Escape anything that came from the server/users before putting it into HTML (stops XSS)
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function safeUrl(url) { return /^https?:\/\//i.test(url || "") ? url : "#"; }
function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? "" : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}
function fmtDay(yyyyMmDd) {            // "2026-10-07" -> local date without timezone shifting
  const [y, m, d] = String(yyyyMmDd).split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}
function toast(message, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = message;
  el.className = "toast show" + (isError ? " error" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (el.className = "toast"), 3200);
}
function setBusy(button, busy, busyText) {
  if (!button) return;
  if (busy) { button.dataset.label = button.textContent; button.textContent = busyText || "Please wait…"; }
  else if (button.dataset.label) { button.textContent = button.dataset.label; }
  button.disabled = busy;
}
function progressBar(percent) {
  const n = Math.max(0, Math.min(100, Number(percent) || 0));
  return `<div class="bar"><div class="bar-fill" style="width:${n}%"></div></div>`;
}
function splitList(text) {
  return String(text || "").split(",").map((s) => s.trim()).filter(Boolean);
}

/* ---------- API client ---------- */
function errorMessage(data, status) {
  if (data && typeof data.detail === "string") return data.detail;
  if (data && Array.isArray(data.detail)) {   // FastAPI validation errors
    return data.detail.map((e) => (e.msg || "Invalid input").replace(/^Value error, /, "")).join(". ");
  }
  return `Something went wrong (${status}).`;
}
async function request(method, url, body) {
  const options = { method, headers: {}, credentials: "same-origin" };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  let data = null;
  if (res.status !== 204) { try { data = await res.json(); } catch (e) { /* no body */ } }
  if (res.status === 401 && !url.startsWith("/api/auth/login")) {
    if (document.body.dataset.private === "true") window.location.href = "/login";
  }
  if (!res.ok) throw new Error(errorMessage(data, res.status));
  return data;
}
const API = {
  get: (url) => request("GET", url),
  post: (url, body) => request("POST", url, body === undefined ? {} : body),
  put: (url, body) => request("PUT", url, body),
  del: (url) => request("DELETE", url),
};

/* ---------- theme ---------- */
function applyTheme() {
  const saved = localStorage.getItem("sg-theme");
  const dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}
function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("sg-theme", next);
  applyTheme();
}

/* ---------- shared UI pieces ---------- */
async function fillRoles(select, selected, emptyLabel) {
  const { roles } = await API.get("/api/roles");
  select.innerHTML = `<option value="">${esc(emptyLabel)}</option>` +
    roles.map((r) => `<option value="${esc(r)}">${esc(r)}</option>`).join("");
  if (selected) select.value = selected;
  return roles;
}
function resourceCard(r) {
  return `<article class="card res-card">
    <a href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener noreferrer">
      <img src="${esc(safeUrl(r.thumbnail))}" alt="" loading="lazy"></a>
    <div class="res-body">
      <h4>${esc(r.title)}</h4>
      <p class="muted small">${esc(r.channel)}${r.published_at ? " · " + esc(fmtDate(r.published_at)) : ""}</p>
      <div class="row">
        <a class="btn btn-sm" href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener noreferrer">Watch</a>
        <button class="btn btn-sm ${r.completed ? "btn-ok" : "btn-outline"}" data-action="complete-resource"
          data-id="${Number(r.id)}" ${r.completed ? "disabled" : ""}>${r.completed ? "✓ Completed" : "Mark completed"}</button>
      </div>
    </div></article>`;
}

/* ---------- click actions (event delegation: no inline onclick, so CSP stays strict) ---------- */
const actions = {
  "toggle-theme": () => toggleTheme(),
  "logout": async () => {
    try { await API.post("/api/auth/logout"); } finally { window.location.href = "/login"; }
  },
  "complete-resource": async (btn) => {
    btn.disabled = true;
    try {
      await API.post(`/api/resources/${btn.dataset.id}/complete`);
      btn.textContent = "✓ Completed";
      btn.classList.replace("btn-outline", "btn-ok");
    } catch (e) { btn.disabled = false; toast(e.message, true); }
  },
  "load-resources": async (btn) => {
    const target = $(`#res-${btn.dataset.id}`);
    setBusy(btn, true, "Searching YouTube…");
    try {
      const list = await API.get(`/api/roadmap/steps/${btn.dataset.id}/resources`);
      target.innerHTML = list.length ? list.map(resourceCard).join("") : `<p class="muted">No videos found.</p>`;
      btn.hidden = true;
    } catch (e) { setBusy(btn, false); toast(e.message, true); }
  },
  "complete-step": async (btn) => {
    setBusy(btn, true, "Saving…");
    try {
      const roadmap = await API.post(`/api/roadmap/steps/${btn.dataset.id}/complete`);
      toast("Step completed. Great work!");
      page.roadmapRender && page.roadmapRender(roadmap);
    } catch (e) { setBusy(btn, false); toast(e.message, true); }
  },
  "complete-task": async (btn) => {
    setBusy(btn, true, "Saving…");
    try {
      await API.post(`/api/tasks/${btn.dataset.id}/complete`);
      toast("Task completed!");
      if (page.reload) page.reload();
    } catch (e) { setBusy(btn, false); toast(e.message, true); }
  },
  "tab": (btn) => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === btn));
    $("#tab-people").hidden = btn.dataset.tab !== "people";
    $("#tab-posts").hidden = btn.dataset.tab !== "posts";
  },
  "delete-post": async (btn) => {
    if (!confirm("Delete this post?")) return;
    try { await API.del(`/api/community/posts/${btn.dataset.id}`); toast("Post deleted."); page.reloadPosts(); }
    catch (e) { toast(e.message, true); }
  },
  "show-generator": () => { $("#generator").hidden = false; $("#generator").scrollIntoView({ behavior: "smooth" }); },
  "topic-search": (btn) => {
    const input = $("#search-form input[name=query]");
    input.value = btn.dataset.query;
    $("#search-form").requestSubmit();
  },
};
document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-action]");
  if (!el) return;
  const handler = actions[el.dataset.action];
  if (handler) { event.preventDefault(); handler(el); }
});

/* ---------- pages ---------- */
const page = {};   // shared hooks between actions and the current page

async function initLogin() {
  const form = $("#login-form"), err = $("#form-error");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.hidden = true;
    const btn = form.querySelector("button");
    setBusy(btn, true, "Logging in…");
    try {
      await API.post("/api/auth/login", { email: form.email.value.trim(), password: form.password.value });
      window.location.href = "/dashboard";
    } catch (ex) { err.textContent = ex.message; err.hidden = false; setBusy(btn, false); }
  });
}

async function initRegister() {
  const form = $("#register-form"), err = $("#form-error");
  fillRoles($("#role-select"), "", "Choose later").catch(() => {});
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.hidden = true;
    const btn = form.querySelector("button");
    setBusy(btn, true, "Creating account…");
    try {
      await API.post("/api/auth/register", {
        name: form.name.value.trim(), email: form.email.value.trim(), password: form.password.value,
        college: form.college.value.trim(), career_role: form.career_role.value || null,
      });
      window.location.href = "/dashboard";
    } catch (ex) { err.textContent = ex.message; err.hidden = false; setBusy(btn, false); }
  });
}

async function initDashboard() {
  async function load() {
    const p = await API.get("/api/progress");
    const rm = p.roadmap;
    $("#dash-stats").innerHTML = [
      ["Roadmap progress", rm ? rm.percent + "%" : "–"],
      ["Topics completed", rm ? `${rm.completed_steps} / ${rm.total_steps}` : "–"],
      ["Tasks completed", p.tasks.completed],
      ["Resources completed", p.resources_completed],
      ["Day streak", p.streak],
    ].map(([label, num]) => `<div class="card stat"><div class="num">${esc(num)}</div><div class="label">${esc(label)}</div></div>`).join("");

    $("#dash-roadmap").innerHTML = rm
      ? `<h3>Learning progress</h3><p class="muted">${esc(rm.role)} roadmap</p>${progressBar(rm.percent)}
         <p>${rm.current_step ? `<strong>Current topic:</strong> ${esc(rm.current_step.topic)}` : "🎉 You finished every topic!"}</p>
         <a class="btn btn-sm" href="/roadmap">Open roadmap</a>`
      : `<h3>Learning progress</h3><p class="muted">You have no roadmap yet.</p><a class="btn btn-sm" href="/roadmap">Generate my roadmap</a>`;

    $("#dash-profile").innerHTML = `<h3>Profile</h3>
      <p><strong>${esc(p.profile.name)}</strong></p>
      <p class="muted">${esc(p.profile.college)}</p>
      <p><span class="badge">${esc(p.profile.career_role || "No role selected")}</span>
         <span class="badge">${esc(p.profile.skill_level || "Beginner")}</span></p>
      <a class="btn btn-sm btn-outline" href="/profile">Edit profile</a>`;

    $("#dash-remaining").innerHTML = `<h3>Remaining topics</h3>` + (rm && rm.remaining_topics.length
      ? `<ol>${rm.remaining_topics.map((t) => `<li>${esc(t)}</li>`).join("")}</ol>`
      : `<p class="muted">Nothing left, or no roadmap yet.</p>`);
  }
  async function loadTask() {
    const box = $("#dash-task");
    try {
      const t = await API.get("/api/tasks/today");
      box.innerHTML = `<h3>Today's task</h3><h4>${esc(t.title)}</h4><p>${esc(t.description)}</p>` +
        (t.completed ? `<span class="badge completed">✓ Completed</span>`
          : `<button class="btn btn-sm" data-action="complete-task" data-id="${Number(t.id)}">Mark as done</button>`);
    } catch (e) { box.innerHTML = `<h3>Today's task</h3><p class="muted">${esc(e.message)}</p>`; }
  }
  page.reload = () => { load(); loadTask(); };
  load().catch((e) => toast(e.message, true));
  loadTask();
}

async function initRoadmap() {
  const root = $("#roadmap-root");
  const [profile, current, rolesData] = await Promise.all(
    [API.get("/api/profile"), API.get("/api/roadmap"), API.get("/api/roles")]);

  function generatorHtml(hasRoadmap) {
    return `<form id="generator" class="card form" ${hasRoadmap ? "hidden" : ""}>
      <h3>${hasRoadmap ? "Generate a new roadmap" : "Create your personalised roadmap"}</h3>
      ${hasRoadmap ? `<p class="muted small">Your current roadmap will be archived.</p>` : ""}
      <label>Career role<select name="role" required>
        <option value="">Choose a role</option>
        ${rolesData.roles.map((r) => `<option ${r === profile.career_role ? "selected" : ""}>${esc(r)}</option>`).join("")}
      </select></label>
      <label>Current skill level<select name="skill_level">
        ${rolesData.skill_levels.map((s) => `<option ${s === (profile.skill_level || "Beginner") ? "selected" : ""}>${esc(s)}</option>`).join("")}
      </select></label>
      <label>Skills you already have (comma separated)
        <input name="skills" value="${esc((profile.skills || []).join(", "))}" placeholder="Python, HTML"></label>
      <label>Learning goals
        <textarea name="goals" rows="2" maxlength="1000" placeholder="e.g. Get a backend internship">${esc(profile.learning_goals || "")}</textarea></label>
      <p id="gen-error" class="error" hidden></p>
      <button class="btn" type="submit">Generate roadmap</button>
    </form>`;
  }

  function stepHtml(s, openId) {
    const status = { completed: "Completed", in_progress: "In progress", not_started: "Not started" }[s.status];
    return `<details class="step ${esc(s.status)}" ${s.id === openId ? "open" : ""}>
      <summary><span class="step-num">${s.status === "completed" ? "✓" : Number(s.order_index)}</span>
        <span class="step-title">${esc(s.topic)}</span><span class="badge ${esc(s.status)}">${esc(status)}</span></summary>
      <div class="step-body">
        <p><strong>Why you need it:</strong> ${esc(s.why)}</p>
        <div class="phase"><h4>1 · Learn</h4>
          <div class="chips">${s.concepts.map((c) => `<span class="chip static">${esc(c)}</span>`).join("")}</div>
          <button class="btn btn-sm btn-outline" data-action="load-resources" data-id="${Number(s.id)}">▶ Find YouTube videos</button>
          <div id="res-${Number(s.id)}" class="grid res-grid"></div></div>
        <div class="phase"><h4>2 · Practice</h4><p>${esc(s.practice_task)}</p></div>
        <div class="phase"><h4>3 · Build</h4>
          <p><strong>After learning:</strong> ${esc(s.after_learning)}</p>
          <p><strong>Project idea:</strong> ${esc(s.project_idea)}</p>
          <p><strong>Expected outcome:</strong> ${esc(s.expected_outcome)}</p></div>
        <div class="phase"><h4>4 · Complete</h4>${s.status === "completed"
          ? `<span class="badge completed">✓ Done ${s.completed_at ? esc(fmtDate(s.completed_at)) : ""}</span>`
          : `<button class="btn btn-sm btn-ok" data-action="complete-step" data-id="${Number(s.id)}">Mark step complete</button>`}</div>
      </div></details>`;
  }

  function render(rm) {
    if (!rm) { root.innerHTML = generatorHtml(false); bindGenerator(); return; }
    const openId = (rm.steps.find((s) => s.status !== "completed") || {}).id;
    root.innerHTML = `<div class="card">
        <div class="row" style="justify-content:space-between">
          <div><h3>${esc(rm.role)}</h3><span class="muted small">${esc(rm.skill_level || "")}</span></div>
          <button class="btn btn-sm btn-outline" data-action="show-generator">New roadmap</button></div>
        ${progressBar(rm.percent)}
        <p class="muted">${rm.completed_steps} of ${rm.total_steps} topics completed (${rm.percent}%)</p></div>
      ${generatorHtml(true)}
      <div class="stack">${rm.steps.map((s) => stepHtml(s, openId)).join("")}</div>`;
    bindGenerator();
  }
  page.roadmapRender = render;

  function bindGenerator() {
    const form = $("#generator");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = $("#gen-error"); err.hidden = true;
      const btn = form.querySelector("button[type=submit]");
      setBusy(btn, true, "AI mentor is building your roadmap… (10-20 s)");
      try {
        const rm = await API.post("/api/roadmap/generate", {
          role: form.role.value, skill_level: form.skill_level.value,
          existing_skills: splitList(form.skills.value), goals: form.goals.value.trim(),
        });
        toast("Your roadmap is ready!");
        render(rm);
      } catch (ex) { err.textContent = ex.message; err.hidden = false; setBusy(btn, false); }
    });
  }
  render(current);
}

async function initResources() {
  const form = $("#search-form"), results = $("#results");
  try {   // quick-search chips from the user's current roadmap topics
    const rm = await API.get("/api/roadmap");
    if (rm) {
      const topics = rm.steps.filter((s) => s.status !== "completed").slice(0, 6);
      $("#topic-chips").innerHTML = topics.map((s) =>
        `<button class="chip" data-action="topic-search" data-query="${esc(s.search_query || s.topic)}">${esc(s.topic)}</button>`).join("");
    }
  } catch (e) { /* chips are optional */ }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = form.querySelector("button");
    setBusy(btn, true, "Searching…");
    results.innerHTML = "";
    try {
      const list = await API.get(`/api/resources/search?query=${encodeURIComponent(form.query.value.trim())}`);
      results.innerHTML = list.length ? list.map(resourceCard).join("") : `<p class="muted">No videos found.</p>`;
    } catch (ex) { toast(ex.message, true); }
    setBusy(btn, false);
  });
}

async function initTechUpdates() {
  const list = $("#news-list"), filter = $("#news-filter");
  const me = await API.get("/api/auth/me");
  async function load() {
    list.innerHTML = `<div class="card skeleton">Loading news…</div>`;
    try {
      const role = filter.value === "mine" && me.career_role ? `?role=${encodeURIComponent(me.career_role)}` : "";
      const items = await API.get("/api/tech-updates" + role);
      list.innerHTML = items.length ? items.map((u) => `<article class="card">
          <h3><a href="${esc(safeUrl(u.url))}" target="_blank" rel="noopener noreferrer">${esc(u.title)}</a></h3>
          <p class="muted small">${esc(u.source)} · ${esc(fmtDate(u.published_at))}
            ${u.category ? `· <span class="badge">${esc(u.category)}</span>` : ""}</p>
          <p><strong>What happened:</strong> ${esc(u.description)}</p>
          <div class="quote-why"><strong>Why it matters:</strong> ${esc(u.why_it_matters)}</div>
          <p class="small"><strong>Who should care:</strong>
            ${(u.relevant_roles || []).map((r) => `<span class="badge">${esc(r)}</span>`).join("")}</p>
        </article>`).join("")
        : `<div class="card muted">No updates found${role ? " for your role" : ""}.</div>`;
    } catch (e) { list.innerHTML = `<div class="card error">${esc(e.message)}</div>`; }
  }
  filter.addEventListener("change", load);
  load();
}

async function initTasks() {
  const todayBox = $("#today-task"), history = $("#task-history");
  async function load() {
    try {
      const t = await API.get("/api/tasks/today");
      todayBox.innerHTML = `<span class="badge">${esc(t.difficulty)}</span>${t.step_topic ? `<span class="badge">${esc(t.step_topic)}</span>` : ""}
        <h3>${esc(t.title)}</h3><p>${esc(t.description)}</p>` +
        (t.completed ? `<span class="badge completed">✓ Completed</span>`
          : `<button class="btn" data-action="complete-task" data-id="${Number(t.id)}">Mark as done</button>`);
    } catch (e) { todayBox.innerHTML = `<p class="muted">${esc(e.message)}</p>`; }
    try {
      const all = await API.get("/api/tasks");
      history.innerHTML = all.length ? all.map((t) => `<div class="card">
          <div class="row" style="justify-content:space-between"><strong>${esc(t.title)}</strong>
            <span class="badge ${t.completed ? "completed" : ""}">${t.completed ? "✓ Done" : "Pending"}</span></div>
          <p class="muted small">${esc(fmtDay(t.task_date))}</p><p>${esc(t.description)}</p></div>`).join("")
        : `<p class="muted">No tasks yet.</p>`;
    } catch (e) { history.innerHTML = ""; }
  }
  page.reload = load;
  load();
}

async function initCommunity() {
  const me = await API.get("/api/profile");
  const roleSelects = [$("#f-role"), $("#post-role"), $("#pf-role")];
  await Promise.all(roleSelects.map((s, i) => fillRoles(s, i === 1 ? me.career_role : "", i === 1 ? "Any role" : "All roles")));

  async function loadPeople() {
    const params = new URLSearchParams({ same_college: $("#f-college").checked });
    if ($("#f-role").value) params.set("role", $("#f-role").value);
    if ($("#f-relation").value) params.set("relation", $("#f-relation").value);
    const box = $("#people-list");
    try {
      const people = await API.get("/api/community/users?" + params);
      box.innerHTML = people.length ? people.map((u) => `<article class="card">
          <h3>${esc(u.name)}</h3>
          <p class="muted small">${esc(u.college)}${u.study_year ? " · Year " + Number(u.study_year) : ""}</p>
          <p>${u.relation ? `<span class="badge">${esc(u.relation)}</span>` : ""}
             ${u.career_role ? `<span class="badge">${esc(u.career_role)}</span>` : ""}
             ${u.skill_level ? `<span class="badge">${esc(u.skill_level)}</span>` : ""}</p>
          ${u.bio ? `<p>${esc(u.bio)}</p>` : ""}
          <div class="chips">${(u.interests || []).map((i) => `<span class="chip static">${esc(i)}</span>`).join("")}</div>
        </article>`).join("") : `<p class="muted">No students found with these filters yet.</p>`;
    } catch (e) { box.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
  }
  async function loadPosts() {
    const params = new URLSearchParams({ same_college: $("#pf-college").checked });
    if ($("#pf-role").value) params.set("role", $("#pf-role").value);
    if ($("#pf-type").value) params.set("type", $("#pf-type").value);
    const box = $("#post-list");
    try {
      const posts = await API.get("/api/community/posts?" + params);
      box.innerHTML = posts.length ? posts.map((p) => `<article class="card">
          <div class="row" style="justify-content:space-between">
            <div><span class="badge">${esc(p.type.replace("_", " "))}</span>
              ${p.role_tag ? `<span class="badge">${esc(p.role_tag)}</span>` : ""}</div>
            ${p.is_mine ? `<button class="btn btn-sm btn-danger" data-action="delete-post" data-id="${Number(p.id)}">Delete</button>` : ""}</div>
          <h3>${esc(p.title)}</h3><p style="white-space:pre-wrap">${esc(p.body)}</p>
          <p class="muted small">${esc(p.author_name)}${p.author_role ? " · " + esc(p.author_role) : ""} · ${esc(fmtDate(p.created_at))}</p>
        </article>`).join("") : `<p class="muted">No posts yet. Be the first to share something!</p>`;
    } catch (e) { box.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
  }
  page.reloadPosts = loadPosts;

  ["#f-role", "#f-relation", "#f-college"].forEach((s) => $(s).addEventListener("change", loadPeople));
  ["#pf-role", "#pf-type", "#pf-college"].forEach((s) => $(s).addEventListener("change", loadPosts));

  const form = $("#post-form"), err = $("#post-error");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.hidden = true;
    const btn = form.querySelector("button");
    setBusy(btn, true, "Posting…");
    try {
      await API.post("/api/community/posts", {
        type: form.type.value, title: form.title.value.trim(), body: form.body.value.trim(),
        role_tag: form.role_tag.value || null,
      });
      form.title.value = ""; form.body.value = "";
      toast("Posted!");
      loadPosts();
    } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    setBusy(btn, false);
  });
  loadPeople();
  loadPosts();
}

async function initProfile() {
  const form = $("#profile-form"), err = $("#form-error");
  const [p] = await Promise.all([API.get("/api/profile"), fillRoles($("#role-select"), "", "Not selected")]);
  form.name.value = p.name; form.email.value = p.email; form.college.value = p.college;
  form.career_role.value = p.career_role || ""; form.skill_level.value = p.skill_level || "Beginner";
  form.available_time.value = p.available_time || ""; form.study_year.value = p.study_year || "";
  form.skills.value = (p.skills || []).join(", "); form.interests.value = (p.interests || []).join(", ");
  form.learning_goals.value = p.learning_goals || ""; form.bio.value = p.bio || "";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    err.hidden = true;
    const btn = form.querySelector("button[type=submit]");
    setBusy(btn, true, "Saving…");
    try {
      await API.put("/api/profile", {
        name: form.name.value.trim(), college: form.college.value.trim(),
        career_role: form.career_role.value || null, skill_level: form.skill_level.value,
        available_time: form.available_time.value || null,
        study_year: form.study_year.value ? Number(form.study_year.value) : null,
        skills: splitList(form.skills.value), interests: splitList(form.interests.value),
        learning_goals: form.learning_goals.value.trim() || null, bio: form.bio.value.trim() || null,
      });
      toast("Profile saved.");
    } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    setBusy(btn, false);
  });
}

/* ---------- start ---------- */
const initializers = {
  login: initLogin, register: initRegister, dashboard: initDashboard, roadmap: initRoadmap,
  resources: initResources, tech_updates: initTechUpdates, tasks: initTasks,
  community: initCommunity, profile: initProfile,
};

document.addEventListener("DOMContentLoaded", async () => {
  applyTheme();
  try {
    if (document.body.dataset.private === "true") {
      const me = await API.get("/api/auth/me");
      const box = $("#nav-user");
      if (box) box.textContent = me.name;
    }
    const init = initializers[document.body.dataset.page];
    if (init) await init();
  } catch (e) {
    if (e.message) toast(e.message, true);
  }
});
