const STORAGE_KEY = "sql-quiz-progress";

let allQuestions = [];
let queue = [];
let currentIndex = 0;
let selected = new Set();
let answered = false;

const $ = (sel) => document.querySelector(sel);

function hashText(text) {
  let h = 0;
  const s = text.replace(/\s+/g, " ").trim();
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return String(h);
}

function dedupeQuestions(questions) {
  const seen = new Set();
  return questions.filter((q) => {
    const key = hashText(q.text);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function loadProgress() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || { done: [], correct: [] };
  } catch {
    return { done: [], correct: [] };
  }
}

function saveProgress(progress) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

function updateHomeStats() {
  const progress = loadProgress();
  $("#total-count").textContent = allQuestions.length;
  $("#done-count").textContent = progress.done.length;
  $("#correct-count").textContent = progress.correct.length;
}

function showScreen(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  $(id).classList.add("active");
}

function buildQueue(shuffle) {
  queue = dedupeQuestions([...allQuestions]);
  if (shuffle) {
    for (let i = queue.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [queue[i], queue[j]] = [queue[j], queue[i]];
    }
  }
  currentIndex = 0;
}

function renderQuestion() {
  if (currentIndex >= queue.length) {
    showScreen("#home-screen");
    updateHomeStats();
    alert("練習完成！");
    return;
  }

  const q = queue[currentIndex];
  selected.clear();
  answered = false;

  $("#quiz-index").textContent = `${currentIndex + 1} / ${queue.length}`;
  $("#progress-fill").style.width = `${((currentIndex + 1) / queue.length) * 100}%`;
  $("#question-text").textContent = q.text;

  const imgEl = $("#question-image");
  if (q.hasImage) {
    imgEl.classList.remove("hidden");
  } else {
    imgEl.classList.add("hidden");
  }

  const isMulti = q.multi || (q.answer && q.answer.includes(","));
  const list = $("#options-list");
  list.innerHTML = "";

  q.options.forEach((opt) => {
    const li = document.createElement("li");
    li.className = "option" + (isMulti ? " multi" : "");

    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = isMulti ? "checkbox" : "radio";
    input.name = "answer";
    input.value = opt.id;

    input.addEventListener("change", () => {
      if (answered) return;
      if (isMulti) {
        if (input.checked) selected.add(opt.id);
        else selected.delete(opt.id);
      } else {
        selected = new Set([opt.id]);
      }
      list.querySelectorAll("label").forEach((l) => l.classList.remove("selected"));
      list.querySelectorAll("input:checked").forEach((inp) => {
        inp.closest("label").classList.add("selected");
      });
      $("#btn-submit").disabled = selected.size === 0;
    });

    const letter = document.createElement("span");
    letter.className = "option-letter";
    letter.textContent = opt.id.toUpperCase() + ".";

    const text = document.createElement("span");
    text.className = "option-text";
    text.textContent = opt.text;

    label.append(input, letter, text);
    li.append(label);
    list.append(li);
  });

  $("#btn-submit").disabled = true;
  $("#btn-submit").classList.remove("hidden");
  $("#btn-next").classList.add("hidden");
  $("#feedback").classList.add("hidden");
  $("#answer-panel").classList.add("hidden");
  $("#answer-panel").innerHTML = "";
}

function getExpectedIds(q) {
  if (!q.answer) return new Set();
  return new Set(q.answer.split(",").map((s) => s.trim()));
}

function getOptionById(q, id) {
  return q.options.find((o) => o.id === id);
}

function checkAnswer(q, chosen) {
  if (!q.answer) return null;
  const expected = getExpectedIds(q);
  const chosenSet = new Set(chosen);
  if (expected.size !== chosenSet.size) return false;
  for (const c of expected) {
    if (!chosenSet.has(c)) return false;
  }
  return true;
}

function highlightResults(q, chosen, isCorrect) {
  const expected = getExpectedIds(q);

  document.querySelectorAll(".option input").forEach((input) => {
    input.disabled = true;
    const label = input.closest("label");
    const id = input.value;
    label.classList.remove("correct", "wrong", "missed", "dimmed");

    if (expected.has(id)) {
      label.classList.add("correct");
      if (!isCorrect) {
        addOptionBadge(label, "✓ 正解", "badge-correct");
      }
    } else if (chosen.has(id)) {
      label.classList.add("wrong");
      addOptionBadge(label, "你的選擇", "badge-wrong");
    } else if (q.answer && !isCorrect) {
      label.classList.add("dimmed");
    }
  });
}

function showAnswerPanel(q, isCorrect) {
  const panel = $("#answer-panel");
  if (!q.answer || isCorrect) {
    panel.classList.add("hidden");
    panel.innerHTML = "";
    return;
  }

  panel.innerHTML = '<div class="answer-panel-heading">✓ 正確答案</div>';
  const list = document.createElement("div");
  list.className = "answer-panel-list";

  [...getExpectedIds(q)].forEach((id) => {
    const opt = getOptionById(q, id);
    if (!opt) return;
    const row = document.createElement("div");
    row.className = "answer-panel-item";

    const letter = document.createElement("span");
    letter.className = "answer-panel-letter";
    letter.textContent = id.toUpperCase();

    const text = document.createElement("span");
    text.className = "answer-panel-text";
    text.textContent = opt.text;

    row.append(letter, text);
    list.appendChild(row);
  });

  panel.appendChild(list);
  panel.classList.remove("hidden");
}

function addOptionBadge(label, text, className) {
  if (label.querySelector(".option-badge")) return;
  const badge = document.createElement("span");
  badge.className = `option-badge ${className}`;
  badge.textContent = text;
  label.appendChild(badge);
}

function renderFeedback(q, result) {
  const feedback = $("#feedback");
  feedback.classList.remove("hidden", "correct", "wrong", "neutral");
  feedback.innerHTML = "";

  if (result === null) {
    feedback.classList.add("neutral");
    feedback.innerHTML =
      '<p class="feedback-title">此題暫無標準答案</p>' +
      '<p class="feedback-detail">請對照講義或筆記自行確認。</p>';
    return;
  }

  if (result) {
    feedback.classList.add("correct");
    feedback.innerHTML = '<p class="feedback-title">✓ 答對了！</p>';
  } else {
    feedback.classList.add("wrong");
    feedback.innerHTML =
      '<p class="feedback-title">✗ 答錯了</p>' +
      '<p class="feedback-detail">請看選項下方灰藍色區塊的完整正解。</p>';
  }
}

function recordProgress(qid, isCorrect) {
  const progress = loadProgress();
  if (!progress.done.includes(qid)) progress.done.push(qid);
  if (isCorrect && !progress.correct.includes(qid)) progress.correct.push(qid);
  saveProgress(progress);
}

function submitAnswer() {
  if (answered || selected.size === 0) return;
  answered = true;

  const q = queue[currentIndex];
  const result = checkAnswer(q, [...selected]);
  const isCorrect = result === true;

  highlightResults(q, selected, isCorrect);
  showAnswerPanel(q, isCorrect);
  renderFeedback(q, result);

  if (q.answer && !isCorrect) {
    setTimeout(() => {
      $("#answer-panel").scrollIntoView({ behavior: "smooth", block: "center" });
    }, 150);
  }
  recordProgress(q.id, isCorrect);

  $("#btn-submit").classList.add("hidden");
  $("#btn-next").classList.remove("hidden");
  updateHomeStats();
}

function nextQuestion() {
  currentIndex++;
  renderQuestion();
}

async function loadQuizData() {
  if (window.QUIZ_DATA?.questions?.length) {
    return window.QUIZ_DATA;
  }
  const res = await fetch("questions.json");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function init() {
  try {
    const data = await loadQuizData();
    allQuestions = dedupeQuestions(data.questions);
    updateHomeStats();
  } catch (e) {
    $("#total-count").textContent = "載入失敗";
    document.querySelector(".hint").textContent =
      "無法載入題庫。請用本地伺服器開啟，或部署至 GitHub Pages。";
    console.error(e);
  }
}

$("#btn-random").addEventListener("click", () => {
  if (allQuestions.length === 0) return;
  buildQueue(true);
  showScreen("#quiz-screen");
  renderQuestion();
});

$("#btn-seq").addEventListener("click", () => {
  if (allQuestions.length === 0) return;
  buildQueue(false);
  showScreen("#quiz-screen");
  renderQuestion();
});

$("#btn-reset").addEventListener("click", () => {
  if (confirm("確定要重置所有練習進度？")) {
    localStorage.removeItem(STORAGE_KEY);
    updateHomeStats();
  }
});

$("#btn-back").addEventListener("click", () => {
  showScreen("#home-screen");
  updateHomeStats();
});

$("#btn-skip").addEventListener("click", nextQuestion);
$("#btn-submit").addEventListener("click", submitAnswer);
$("#btn-next").addEventListener("click", nextQuestion);

init();
